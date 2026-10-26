"""
Builds the processed problem-statement corpus:

    data/raw/*.json (live scraper output, if any)
        + data/seed/*_snapshot.json (fallback pre-fetched real data)
        + data/seed/curated_supplementary.json (hand-curated real data)
    --clean/normalize/dedupe/tag-->
    data/processed/problems.json

Run scrapers first if you want live data: `python scripts/run_scrapers.py`.
This script works fine without that step too — it falls back to the
checked-in SIH snapshot when data/raw/sih.json is missing or empty, so the
pipeline always has real (if possibly dated) data to build from, e.g. if
sih.gov.in is unreachable or has changed its markup.

Preserves Gemini enrichment (all nine *_score fields scored by
scripts/enrich_resume_value.py — see its SCORE_FIELDS/RESUME_VALUE_FIELDS
below, kept in sync by hand) across a rebuild: a real incident already
happened where a rebuild silently wiped every already-computed score back
to null, since this script always regenerates problems.json from raw
sources and those fields don't exist anywhere in raw/seed data. Before
writing the new file, any EXISTING problems.json on disk is read and its
scores are copied onto the freshly-processed problem with the same id —
see _restore_resume_value_scores(). This is an id match, not a full
rebuild skip, so it survives adding new raw sources (new problems just
have no prior score to restore, same as before this fix existed) — the
one edge case it can't cover is a problem's stable id itself changing
(e.g. dedup happening to pick a different near-duplicate "winner" once
new raw records are added to its (source, hackathon_name) group — see
app.ingestion.clean.dedupe), which is a pre-existing property of how ids
are derived, not something introduced here.

Also preserves and stamps first_seen_at (see
app.schemas.problem.ProcessedProblem.first_seen_at) the same way: any
problem whose id already appears in the existing problems.json keeps its
original first_seen_at, and only a genuinely new id gets stamped with
today's date. This is what makes the frontend's "New" badge (see
app.schemas.query.RankedResult) mean "actually new to the corpus" instead
of "happened to be in the most recent rebuild" — see
_restore_first_seen_dates(). The very first run of this script after
first_seen_at was introduced has no prior dates to restore at all, which
would otherwise stamp all 612 existing problems as "new" in one go — see
scripts/backfill_first_seen.py, meant to run once before that happens.

Run as: python scripts/build_corpus.py
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.clean import clean_pipeline
from app.schemas.problem import ProcessedProblem

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
SEED_DIR = ROOT / "data" / "seed"
PROCESSED_DIR = ROOT / "data" / "processed"

# Must match scripts/enrich_resume_value.py's SCORE_FIELDS exactly — every
# field Gemini enrichment can write needs to be preserved across a rebuild
# (see _restore_resume_value_scores() below), or adding a new enrichment
# field here-but-not-there would silently wipe it on the next
# `python scripts/build_corpus.py` run, same class of bug this whole
# preserve-on-rebuild mechanism exists to prevent.
RESUME_VALUE_FIELDS = (
    "resume_value_score",
    "industry_relevance_score",
    "technical_depth_score",
    "novelty_score",
    "dataset_availability_score",
    "hardware_requirement_score",
    "competition_potential_score",
    "social_impact_score",
    "feasibility_score",
)


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read %s: %s", path, exc)
        return []


def gather_raw_records() -> list[dict]:
    records: list[dict] = []

    # Prefer a fresh live SIH scrape (data/raw/sih.json, written by
    # scripts/run_scrapers.py) over the checked-in snapshot; fall back to
    # the snapshot if the live scrape hasn't been run or came back empty.
    live_sih = _load_json(RAW_DIR / "sih.json")
    if live_sih:
        logger.info("using live SIH scrape: %d records from %s", len(live_sih), RAW_DIR / "sih.json")
        records.extend(live_sih)
    else:
        snapshot = _load_json(SEED_DIR / "sih_2025_snapshot.json")
        logger.info("live SIH scrape not found/empty — using seed snapshot: %d records", len(snapshot))
        records.extend(snapshot)

    # Any other live-scraped sources (unstop/hackerearth/...), if the
    # scrapers for them are ever implemented and produce output.
    #
    # devpost.json is deliberately skipped even if it exists on disk (e.g.
    # a stale file from before scripts/run_scrapers.py stopped registering
    # DevpostScraper — see that script's docstring for why): this glob
    # reads whatever *.json files happen to be sitting in data/raw/
    # regardless of which scraper wrote them or whether that scraper is
    # still registered, so simply unregistering the scraper would NOT have
    # stopped an already-written devpost.json from being silently
    # re-ingested on every future rebuild.
    for path in sorted(RAW_DIR.glob("*.json")):
        if path.name in ("sih.json", "devpost.json"):
            continue
        other = _load_json(path)
        if other:
            logger.info("using live scrape: %d records from %s", len(other), path)
            records.extend(other)

    curated = _load_json(SEED_DIR / "curated_supplementary.json")
    logger.info("curated supplementary records: %d", len(curated))
    records.extend(curated)

    # Belt-and-suspenders on top of the devpost.json skip above: also
    # drops any devpost-source record regardless of *where* it came from
    # (curated_supplementary.json has 12 hand-picked devpost entries of
    # its own, predating the scraper) — the corpus has no reliable way to
    # tell a real per-problem statement apart from a whole-hackathon
    # blurb for this source at all right now, so none of it belongs here
    # (see scripts/run_scrapers.py's docstring). Revisit if/when
    # devpost_scraper.py is extended to find real per-sponsor challenges.
    before = len(records)
    records = [r for r in records if r.get("source") != "devpost"]
    dropped = before - len(records)
    if dropped:
        logger.info("dropped %d devpost-source record(s) — not fed into the main corpus (see docstring)", dropped)

    return records


def _load_existing_resume_value_scores(path: Path) -> dict[str, dict]:
    """id -> {<whichever of RESUME_VALUE_FIELDS are set>} for every
    already-enriched problem currently on disk (only fields that are
    actually non-null — a problem with no enrichment yet contributes
    nothing, and a partially-enriched one only contributes what it has)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read existing %s for score preservation: %s", path, exc)
        return {}

    scores: dict[str, dict] = {}
    for problem in data:
        problem_id = problem.get("id")
        if not problem_id:
            continue
        entry = {field: problem[field] for field in RESUME_VALUE_FIELDS if problem.get(field) is not None}
        if entry:
            scores[problem_id] = entry
    return scores


def _restore_resume_value_scores(processed: list[ProcessedProblem], existing_scores: dict[str, dict]) -> int:
    """Mutates `processed` in place, copying over any previously-computed
    enrichment scores for problems whose id is unchanged. Returns how many
    problems had scores restored."""
    restored = 0
    for problem in processed:
        prior = existing_scores.get(problem.id)
        if not prior:
            continue
        for field, value in prior.items():
            setattr(problem, field, value)
        restored += 1
    return restored


def _load_existing_first_seen_dates(path: Path) -> dict[str, str]:
    """id -> first_seen_at for every problem currently on disk that
    already has one. Mirrors _load_existing_resume_value_scores() above —
    same reasoning, different field."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read existing %s for first_seen_at preservation: %s", path, exc)
        return {}

    dates: dict[str, str] = {}
    for problem in data:
        problem_id = problem.get("id")
        first_seen_at = problem.get("first_seen_at")
        if problem_id and first_seen_at:
            dates[problem_id] = first_seen_at
    return dates


def _restore_first_seen_dates(processed: list[ProcessedProblem], existing_dates: dict[str, str]) -> tuple[int, int]:
    """Mutates `processed` in place: restores first_seen_at for any problem
    whose id was already on disk, and stamps today's date on every problem
    that still has none afterwards (a genuinely new id). Returns
    (restored_count, newly_stamped_count)."""
    today = datetime.now(timezone.utc).date().isoformat()
    restored = 0
    stamped = 0
    for problem in processed:
        prior = existing_dates.get(problem.id)
        if prior:
            problem.first_seen_at = prior
            restored += 1
        elif not problem.first_seen_at:
            problem.first_seen_at = today
            stamped += 1
    return restored, stamped


def main():
    raw_records = gather_raw_records()
    if not raw_records:
        logger.error("no raw records found in data/raw or data/seed — nothing to process")
        return

    processed = clean_pipeline(raw_records)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "problems.json"

    existing_scores = _load_existing_resume_value_scores(out_path)
    restored = _restore_resume_value_scores(processed, existing_scores)
    if existing_scores:
        logger.info(
            "restored resume-value enrichment scores for %d/%d previously-scored problem(s)",
            restored,
            len(existing_scores),
        )
        if restored < len(existing_scores):
            logger.warning(
                "%d previously-scored problem(s) had no matching id in this rebuild's output — "
                "their enrichment scores could not be restored (see this script's module docstring)",
                len(existing_scores) - restored,
            )

    existing_dates = _load_existing_first_seen_dates(out_path)
    dates_restored, newly_stamped = _restore_first_seen_dates(processed, existing_dates)
    logger.info(
        "first_seen_at: restored %d, newly stamped %d (today) — run scripts/backfill_first_seen.py "
        "once before the first rebuild after upgrading, or every pre-existing problem stamps as new",
        dates_restored,
        newly_stamped,
    )

    out_path.write_text(
        json.dumps([p.model_dump() for p in processed], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    by_source = Counter(p.source for p in processed)
    by_domain = Counter(d for p in processed for d in p.domain)
    untagged = sum(1 for p in processed if not p.domain)

    logger.info("wrote %d processed problems -> %s", len(processed), out_path)
    logger.info("by source: %s", dict(by_source))
    logger.info("by domain: %s", dict(by_domain.most_common()))
    if untagged:
        logger.info("%d problem(s) matched no domain keyword (left untagged, not guessed)", untagged)


if __name__ == "__main__":
    main()
