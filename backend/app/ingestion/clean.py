"""
Cleaning, normalization, and deduplication for the HackBase data pipeline.

Raw scraper/curated-source output (RawProblem-shaped dicts) goes in;
validated, tagged ProcessedProblem records come out. This module is pure
Python (no network, no LLM) so it runs fast and deterministically — the
domain/technology tagging here is a cheap heuristic first pass (see
app.core.taxonomy), not the Phase 2 Gemini enrichment.
"""

from __future__ import annotations

import hashlib
import logging
import re
from difflib import SequenceMatcher

from pydantic import ValidationError

from app.core.taxonomy import extract_technologies, map_domains
from app.schemas.problem import ProcessedProblem, RawProblem

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

SUMMARY_MAX_CHARS = 320
NEAR_DUPLICATE_THRESHOLD = 0.90  # title similarity ratio, within the same source

# Known mojibake artifacts observed in real scraped source data (e.g. a
# curly apostrophe that got mis-decoded through multiple encoding passes
# before we ever saw it). Targeted replacement rather than a generic
# re-decode attempt, which risks corrupting otherwise-valid text.
_MOJIBAKE_FIXES = {
    "├ö├ç├û": "'",
    "├ö├ç├¬": '"',
    "├ö├ç├¦": '"',
}


def _fix_mojibake(text: str) -> str:
    for bad, good in _MOJIBAKE_FIXES.items():
        if bad in text:
            text = text.replace(bad, good)
    return text


def _normalize_whitespace(text: str) -> str:
    text = _fix_mojibake(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def _make_summary(title: str, description: str) -> str:
    description = description.strip()
    if not description:
        return title
    sentences = _SENTENCE_SPLIT_RE.split(description)
    summary = ""
    for sentence in sentences:
        candidate = (summary + " " + sentence).strip() if summary else sentence
        if len(candidate) > SUMMARY_MAX_CHARS:
            break
        summary = candidate
    if not summary:
        summary = description[:SUMMARY_MAX_CHARS].rsplit(" ", 1)[0]
    if len(summary) < len(description):
        summary = summary.rstrip(".") + "."
    return summary


def stable_id(source: str, external_id: str | None, title: str) -> str:
    """
    Deterministic id: prefer `source:external_id` (e.g. "sih:SIH25001") when
    the source gives us one, otherwise hash source+normalized-title so the
    same problem always resolves to the same id across pipeline runs.
    """
    if external_id:
        return f"{source}:{external_id}".lower().replace(" ", "-")
    normalized_title = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    digest = hashlib.sha1(f"{source}:{normalized_title}".encode("utf-8")).hexdigest()[:10]
    return f"{source}:{digest}"


def normalize(raw: RawProblem) -> ProcessedProblem:
    title = _normalize_whitespace(raw.title)
    description = _normalize_whitespace(raw.description)
    summary = _make_summary(title, description)

    domain = map_domains(raw.theme or "", title, description[:600])
    technologies = extract_technologies(title, description)

    return ProcessedProblem(
        id=stable_id(raw.source, raw.external_id, title),
        title=title,
        summary=summary,
        problem_statement=description or summary,
        organization=raw.organization,
        source=raw.source,
        hackathon_name=raw.hackathon_name,
        external_id=raw.external_id,
        category=raw.category,
        domain=domain,
        technologies=technologies,
        skills=[],  # heuristic skill inference is out of scope for Phase 1
        difficulty=None,  # left for the Phase 2 enrichment pass — not guessed here
        url=raw.url,
    )


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


NEAR_DUPLICATE_DESC_THRESHOLD = 0.60


def _is_near_duplicate(a: ProcessedProblem, b: ProcessedProblem) -> bool:
    """
    A record only counts as a near-duplicate if BOTH its title and its
    description are similar. Title-only matching is not enough: real
    datasets (SIH's included) reuse identical generic titles like "Student
    Innovation" across dozens of genuinely distinct problem statements from
    different ministries — those must NOT be collapsed. Requiring
    description similarity too keeps that distinction while still catching
    actual republished/duplicate listings.
    """
    if _similarity(a.title, b.title) < NEAR_DUPLICATE_THRESHOLD:
        return False
    return _similarity(a.problem_statement[:600], b.problem_statement[:600]) >= NEAR_DUPLICATE_DESC_THRESHOLD


def dedupe(records: list[ProcessedProblem]) -> list[ProcessedProblem]:
    """
    Two passes: exact-id dedup (different sources publishing the exact same
    external_id/title collapse to one record), then near-duplicate
    detection *within the same source AND hackathon edition*
    (source, hackathon_name) on title+description together (catches
    republished/rephrased listings without merging distinct problems that
    merely share a generic title). Cross-source similar titles are left
    alone — a "smart attendance system" from SIH and one from a campus
    hackathon are genuinely different problems. Grouping by hackathon_name
    too (not just source) matters once a source spans multiple editions —
    e.g. SIH 2025 and SIH 2026 both have source="sih", but a 2026 problem
    that happens to reuse similar wording to a 2025 one is a genuinely
    different, real problem statement, not a duplicate to drop.
    """
    seen_ids: dict[str, ProcessedProblem] = {}
    dropped_exact = 0
    for record in records:
        if record.id in seen_ids:
            dropped_exact += 1
            continue
        seen_ids[record.id] = record

    deduped = list(seen_ids.values())
    by_source_and_edition: dict[tuple[str, str | None], list[ProcessedProblem]] = {}
    for record in deduped:
        by_source_and_edition.setdefault((record.source, record.hackathon_name), []).append(record)

    to_drop: set[str] = set()
    dropped_near = 0
    for (source, hackathon_name), group in by_source_and_edition.items():
        kept: list[ProcessedProblem] = []
        for record in group:
            is_dup = any(_is_near_duplicate(record, other) for other in kept)
            if is_dup:
                to_drop.add(record.id)
                dropped_near += 1
            else:
                kept.append(record)

    result = [r for r in deduped if r.id not in to_drop]

    if dropped_exact or dropped_near:
        logger.info(
            "dedupe: dropped %d exact-id duplicate(s) and %d near-duplicate title(s), %d records remain",
            dropped_exact,
            dropped_near,
            len(result),
        )
    return result


def clean_pipeline(raw_records: list[dict]) -> list[ProcessedProblem]:
    """Validate -> normalize -> dedupe. Invalid raw records are skipped and
    logged, never silently dropped without a trace."""
    valid: list[RawProblem] = []
    for i, rec in enumerate(raw_records):
        try:
            valid.append(RawProblem(**rec))
        except ValidationError as exc:
            logger.warning("skipping invalid raw record at index %d: %s", i, exc)

    normalized = [normalize(r) for r in valid]
    return dedupe(normalized)
