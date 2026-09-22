"""
Ingests hackathon/project problem statements from prose (non-structured)
sources — ordinary web pages and a GitHub repo — as opposed to the
structured, predictable HTML the other scrapers (sih_scraper.py etc.)
parse by fixed shape.

Two ingestion paths feed one merged, idempotent output file
(data/raw/article_ingest.json):

1. GITHUB_REPO: already clean, structured markdown (the repo's own
   INDEX.md is a complete, accurate catalog — title/file-path/tags per
   problem — and each individual file has a real "## The Problem"
   section). Parsed directly with plain text processing, no LLM call,
   since the content is already exactly what we need — cheaper and more
   reliable than routing well-structured text through an LLM.

2. ARTICLE_URLS: ordinary web pages with unstructured prose. Fetched as
   plain HTML, text-extracted, then sent to Gemini (app.rag.gemini_client)
   with a strict extraction-only prompt: Gemini is told to return only
   problem statements literally present in the given text, and an empty
   list if it finds none. This is extraction, not generation — the prompt
   explicitly forbids inventing anything not in the source text.

Idempotent by source URL: a URL already successfully checked is skipped on
a normal re-run (skips a real Gemini call for the article path too — see
the standing "be frugal with Gemini calls" rule). This applies even when a
page genuinely had zero real problem statements on it — that's still a
real, complete answer, tracked in article_ingest_state.json, not something
to keep re-asking Gemini about; only an actual fetch/Gemini failure gets
retried on the next run. Pass --force to drop and re-fetch every URL
below, not just new ones.

This module only ever WRITES data/raw/article_ingest.json — it never
touches data/processed/problems.json directly. Merging these new raw
records into the processed corpus without disturbing already-enriched
problems (resume_value_score etc.) is scripts/build_corpus.py's job; see
its module docstring for the merge-by-id behavior that makes that safe.

Run as: python -m app.scrapers.article_ingest [--force]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.core.tracking import ARTICLE_INGEST_EXPERIMENT, track_run
from app.rag.gemini_client import GeminiNotConfiguredError, GeminiUnavailableError, generate_json, get_gemini_model

logger = logging.getLogger(__name__)

# article_ingest.py lives at <project_root>/backend/app/scrapers/ ->
# parents[0]=scrapers, [1]=app, [2]=backend, [3]=<project_root>.
ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = ROOT / "data" / "raw" / "article_ingest.json"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 30
_MAX_TEXT_CHARS = 40000  # generous — real pages checked ran 15-40k chars; don't truncate away real content

SOURCE = "article"

# --- Path 1: ordinary web pages, extracted via Gemini ---
#
# robots.txt was checked manually on every URL below before adding it (see
# the task this module was built from) — none restrict AI crawlers.
# Deliberately NOT included, and don't try alternate ways to reach them:
#   - unstop.com: a specific attachment URL there is robots.txt-disallowed,
#     confirmed blocked by an actual fetch attempt (not just in theory).
#   - studocu.com: robots.txt explicitly disallows anthropic-ai/ClaudeBot/
#     Claude-web by name.
#   - slideshare.net: not robots.txt-blocked, but the content is gated
#     behind a login wall, so scraping it would only get a partial/broken
#     result.
ARTICLE_URLS = [
    "https://eventornado.com/blog/hackathon-problem-statements",
    "https://newhorizonindia.edu/smarthorizon/problem-statements.php",
    "https://hackathon.bput.ac.in/problem-statements",
    "https://www.hackerearth.com/blog/crafting-hackathon-problem-statements",
    "https://www.jiscollege.ac.in/JISTech2k20/Hackathon.html",
    "https://bgihackathon.in/problem-statements",
    "https://www.ghrhack.tech/problem-statements",
]

_EXTRACTION_PROMPT_TEMPLATE = """\
You are extracting hackathon/project problem statements that are \
LITERALLY PRESENT in the web page text below. This is extraction, not \
generation.

Rules — read carefully:
- Only return a problem statement if it is explicitly described in the \
text below. Do not invent, generalize, or rephrase the page's own advice \
into a new problem that isn't actually stated.
- If the page contains no real, specific problem statements (e.g. it's \
just general advice about how to WRITE problem statements, with no \
concrete example problems), return an empty JSON array: []. An empty \
list is the correct, expected answer for many pages — never invent \
something plausible-sounding just to return a non-empty list.
- Do not count the page's own meta-commentary (e.g. "a good problem \
statement should include...") as a problem statement.

Web page text:
\"\"\"
{page_text}
\"\"\"

Respond with ONLY a JSON array (no markdown, no commentary). One object \
per distinct real problem statement found:
[
  {{"title": "<short title, drawn from the text>", \
"statement": "<the problem description, drawn from the text — do not \
pad or embellish beyond what's actually written>", \
"domain_guess": "<a short domain/category guess based on the text, or \
null if genuinely unclear>"}}
]
"""


def _fetch_page_text(url: str) -> str:
    response = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:_MAX_TEXT_CHARS]


def _site_label(url: str) -> str:
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def _parse_extraction_response(text: str, url: str) -> list[dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini extraction for %s did not return valid JSON: %s", url, exc)
        return []

    if not isinstance(data, list):
        logger.warning("Gemini extraction for %s: expected a JSON array, got %s", url, type(data).__name__)
        return []

    fetched_at = datetime.now(timezone.utc).isoformat()
    site = _site_label(url)
    records = []
    for item in data:
        if not isinstance(item, dict) or not item.get("title") or not item.get("statement"):
            logger.warning("skipping malformed extracted item from %s: %r", url, item)
            continue
        records.append(
            {
                "title": str(item["title"]).strip(),
                "description": str(item["statement"]).strip(),
                "organization": None,
                "source": SOURCE,
                "hackathon_name": site,
                "external_id": None,
                "category": None,
                "theme": (str(item["domain_guess"]).strip() if item.get("domain_guess") else None),
                "url": url,
                "fetched_at": fetched_at,
            }
        )
    return records


def _try_extract_from_article_url(url: str) -> tuple[list[dict], bool]:
    """Returns (records, succeeded). A page that was genuinely checked and
    had zero real problem statements on it (succeeded=True, records=[]) is
    NOT the same thing as a page that failed to fetch or hit a Gemini
    error (succeeded=False, records=[]) — both look identical as an empty
    list, so run()'s idempotency tracking needs this flag to tell them
    apart: a genuine empty result should never be retried (that's real
    quota spent for a real, correct answer), but a transient failure
    should be retried next run rather than silently treated as "checked,
    nothing there"."""
    try:
        page_text = _fetch_page_text(url)
    except requests.RequestException as exc:
        logger.warning("could not fetch %s: %s", url, exc)
        return [], False

    if not page_text.strip():
        logger.warning("no extractable text on %s", url)
        return [], False

    try:
        model = get_gemini_model()
        prompt = _EXTRACTION_PROMPT_TEMPLATE.format(page_text=page_text)
        raw_text = generate_json(model, prompt, timeout=45, retry_timeout=40)
    except (GeminiNotConfiguredError, GeminiUnavailableError) as exc:
        logger.warning("Gemini extraction failed for %s: %s", url, exc)
        return [], False

    return _parse_extraction_response(raw_text, url), True


def extract_from_article_url(url: str) -> list[dict]:
    """One real Gemini call per URL — fetches the page, extracts visible
    text, and asks Gemini to pull out only problem statements actually
    present in it. Returns [] (never raises past logging) if the page
    can't be fetched, has no text, or Gemini is unavailable, so one broken
    source never stops the rest. See _try_extract_from_article_url for the
    success/failure distinction run() needs for idempotency — this wrapper
    is for callers that just want the records."""
    records, _succeeded = _try_extract_from_article_url(url)
    return records


# --- Path 2: GitHub repo, already clean structured markdown — no Gemini ---

GITHUB_REPO = "AshayK003/hackathon-problem-statements"
GITHUB_BRANCH = "master"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}"
GITHUB_BLOB_BASE = f"https://github.com/{GITHUB_REPO}/blob/{GITHUB_BRANCH}"
GITHUB_HACKATHON_NAME = f"Problem Statements Worth Building (GitHub: {GITHUB_REPO})"

# INDEX.md tracks are headed "### <emoji> <Track Name> (N problems)";
# table rows underneath are "| # | Title | [label](path.md) | time | tags |".
_TRACK_HEADING_RE = re.compile(r"^###\s+\S*\s*(?P<name>.+?)\s*\(\d+\s+problems?\)\s*$")
_INDEX_ROW_RE = re.compile(
    r"^\|\s*\d+\s*\|\s*(?P<title>[^|]+?)\s*\|\s*\[[^\]]*\]\((?P<path>[^)]+\.md)\)\s*\|\s*[^|]*\|\s*(?P<tags>[^|]*)\|\s*$"
)
_PROBLEM_SECTION_RE = re.compile(r"^##\s+The Problem\s*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_github_index(index_text: str) -> list[dict]:
    """Every {title, path, track, tags} entry listed in INDEX.md."""
    entries: list[dict] = []
    current_track: str | None = None
    for line in index_text.splitlines():
        line = line.strip()
        track_match = _TRACK_HEADING_RE.match(line)
        if track_match:
            current_track = track_match.group("name").strip()
            continue
        row_match = _INDEX_ROW_RE.match(line)
        if row_match and current_track:
            entries.append(
                {
                    "title": row_match.group("title").strip(),
                    "path": row_match.group("path").strip(),
                    "track": current_track,
                    "tags": row_match.group("tags").strip(),
                }
            )
    return entries


def _parse_github_problem_file(file_text: str, fallback_title: str) -> tuple[str, str]:
    """Returns (title, problem_statement) for one repo markdown file. Falls
    back to the INDEX.md-listed title / the whole file text if the
    expected structure (H1 / "## The Problem") isn't found, rather than
    dropping the record — the repo's own content is still real either
    way, just less precisely sectioned."""
    title_match = _TITLE_RE.search(file_text)
    title = title_match.group(1).strip() if title_match else fallback_title

    section_match = _PROBLEM_SECTION_RE.search(file_text)
    statement = section_match.group(1).strip() if section_match else file_text.strip()
    return title, statement


def fetch_github_index_entries() -> list[dict]:
    """Fetches and parses INDEX.md — the full real catalog of what's in the
    repo right now. Cheap (one small file), so this is always fetched in
    full; only the (much larger) per-problem file fetches below are
    filtered down to what's actually new, for idempotency."""
    try:
        index_resp = requests.get(f"{GITHUB_RAW_BASE}/INDEX.md", headers=_HEADERS, timeout=_TIMEOUT)
        index_resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("could not fetch GitHub repo INDEX.md: %s", exc)
        return []

    entries = _parse_github_index(index_resp.text)
    if not entries:
        logger.warning("GitHub repo INDEX.md structure changed — parsed 0 entries")
    return entries


def fetch_github_problems(entries: list[dict], paths: set[str] | None = None) -> list[dict]:
    """No Gemini call — the repo is already clean, structured markdown, so
    this is a direct fetch-and-parse of each listed file. `paths`
    restricts which of `entries` are actually fetched (idempotent partial
    runs skip files already in the output); None fetches all of them."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    records = []
    for entry in entries:
        if paths is not None and entry["path"] not in paths:
            continue
        blob_url = f"{GITHUB_BLOB_BASE}/{entry['path']}"
        try:
            file_resp = requests.get(f"{GITHUB_RAW_BASE}/{entry['path']}", headers=_HEADERS, timeout=_TIMEOUT)
            file_resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("could not fetch %s: %s", entry["path"], exc)
            continue

        title, statement = _parse_github_problem_file(file_resp.text, entry["title"])
        records.append(
            {
                "title": title,
                "description": statement,
                "organization": None,
                "source": SOURCE,
                "hackathon_name": GITHUB_HACKATHON_NAME,
                "external_id": entry["path"].removesuffix(".md"),
                "category": entry["track"],
                "theme": entry["tags"] or None,
                "url": blob_url,
                "fetched_at": fetched_at,
            }
        )

    logger.info("GitHub repo: fetched %d problem file(s)", len(records))
    return records


# --- Merge + idempotent write ---

# Tracks which ARTICLE_URLS have been successfully checked (Gemini
# actually answered, whether with items or a genuine empty list) —
# separate from OUTPUT_PATH because a legitimate "found nothing on this
# page" result produces zero records, which would otherwise be
# indistinguishable from "never tried yet" and get re-fetched (and
# re-billed to Gemini) on every single run forever. The GitHub path
# doesn't need this: every successfully-fetched file always produces
# exactly one real record, so presence-in-OUTPUT_PATH is already accurate
# for it.
STATE_PATH = ROOT / "data" / "raw" / "article_ingest_state.json"


def _load_existing() -> list[dict]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read existing %s: %s", OUTPUT_PATH, exc)
        return []


def _load_processed_article_urls() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return set(data.get("processed_article_urls", []))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("could not read %s: %s", STATE_PATH, exc)
        return set()


def _save_processed_article_urls(urls: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"processed_article_urls": sorted(urls)}, indent=2), encoding="utf-8")


def run(force: bool = False) -> list[dict]:
    existing = _load_existing()
    existing_urls = {r.get("url") for r in existing if r.get("url")}
    processed_article_urls = _load_processed_article_urls()

    github_entries = fetch_github_index_entries()
    github_url_by_path = {e["path"]: f"{GITHUB_BLOB_BASE}/{e['path']}" for e in github_entries}
    all_target_urls = set(ARTICLE_URLS) | set(github_url_by_path.values())

    if force:
        kept = [r for r in existing if r.get("url") not in all_target_urls]
        urls_to_process = set(ARTICLE_URLS)
        github_paths_to_process = set(github_url_by_path)
        processed_article_urls = processed_article_urls - set(ARTICLE_URLS)
    else:
        kept = existing
        urls_to_process = {u for u in ARTICLE_URLS if u not in processed_article_urls}
        github_paths_to_process = {path for path, url in github_url_by_path.items() if url not in existing_urls}

    new_records: list[dict] = []
    newly_processed: set[str] = set()

    with track_run(
        ARTICLE_INGEST_EXPERIMENT,
        params={
            "force": force,
            "article_urls_to_process": len(urls_to_process),
            "github_files_to_process": len(github_paths_to_process),
        },
    ) as run_tracker:
        for url in sorted(urls_to_process):
            records, succeeded = _try_extract_from_article_url(url)
            status = "" if succeeded else " (failed — will retry next run)"
            logger.info("extracted %d problem statement(s) from %s%s", len(records), url, status)
            new_records.extend(records)
            if succeeded:
                newly_processed.add(url)

        if github_paths_to_process:
            new_records.extend(fetch_github_problems(github_entries, paths=github_paths_to_process))

        run_tracker.log_metric("new_records", len(new_records))
        run_tracker.log_metric("skipped_already_present_urls", len(existing_urls & all_target_urls))

    _save_processed_article_urls(processed_article_urls | newly_processed)

    merged = kept + new_records
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "wrote %d record(s) (%d new, %d carried over) -> %s",
        len(merged),
        len(new_records),
        len(kept),
        OUTPUT_PATH,
    )
    return merged


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="re-fetch every URL, even ones already in the output file"
    )
    args = parser.parse_args()
    run(force=args.force)
