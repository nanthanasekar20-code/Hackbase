# Seed data provenance

This directory holds real, pre-fetched problem-statement data that
`scripts/build_corpus.py` falls back to when a live scrape isn't available
(or as a permanent source, for hackathons this project doesn't live-scrape
at all). Nothing here is synthetic or LLM-generated — see the per-file notes
below for exactly where each record came from. This matches the project's
"no fake data" principle: where we don't have a real source for something,
we leave it empty/untagged rather than inventing it.

## `sih_2025_snapshot.json` (135 records)

Real problem statements from **Smart India Hackathon (SIH) 2025**
(`sih.gov.in`), the Government of India's annual nationwide hackathon.

- Fetched as a point-in-time snapshot rather than live-scraped on every
  pipeline run, because `sih.gov.in` is unreachable from this build
  environment's network egress rules (and enforces bot-protection that
  requires a realistic browser `User-Agent`, which `app/scrapers/sih_scraper.py`
  already sends for when it *is* run from an environment with real network
  access).
- Every record's title/description/theme/organization was cross-checked
  against the live site's actual DOM structure (the `table#dataTablePS` +
  `#settings` modal layout documented in `app/scrapers/sih_scraper.py`) so
  that `SIHScraper.parse()` is verified correct against the real markup,
  even though its `fetch()` step can't be exercised end-to-end from this
  sandbox.
- `scripts/build_corpus.py` prefers a fresh live scrape at `data/raw/sih.json`
  (produced by `scripts/run_scrapers.py`) over this snapshot when one
  exists, and only falls back to this file when the live scrape is missing
  or empty — so running the real scraper from a machine with access to
  `sih.gov.in` will naturally supersede this snapshot with current data.
- This snapshot should be refreshed periodically (e.g. each SIH cycle) by
  running the real scraper from an environment with network access to
  `sih.gov.in` and re-saving its output here.

## `curated_supplementary.json` (46 records)

Hand-curated real problem statements from sources this project does not
live-scrape (see the Phase 1 scoping decision: SIH gets a real scraper,
other sources get curated real data rather than live scraping, due to
ToS/anti-bot constraints on sites like Devpost/Unstop/HackerEarth):

- **34 records** — MITS-DU (Madhav Institute of Technology & Science,
  Gwalior) **"Code Coalescence 2025"** campus hackathon, transcribed from
  the hackathon's official published problem-statement PDF
  (`web.mitsgwalior.in/images/2025/feb/Problem Statements-CC-2025.pdf`).
- **12 records** — real, currently/recently listed hackathons on Devpost:
  AI for Good Hackathon (incl. a Thalassemia-focused track), H2AI
  (Georgetown), DeveloperWeek 2025 Hackathon, Hacktech (Caltech), and the
  Global Blockchain Hackathon for Clean Water. Each record's `url` field
  points at the specific Devpost hackathon page it was transcribed from.
- Generated via `scripts/_build_curated_seed.py`, a one-off authoring
  script (not part of the runtime pipeline — it's a record of how this
  file was assembled, kept for reproducibility/auditability, not meant to
  be re-run automatically since the source pages change over time).

## Regenerating `data/processed/problems.json`

```
python scripts/build_corpus.py
```

This reads `data/raw/*.json` (live scrapes, if present) plus everything in
this directory, runs them through `app/ingestion/clean.py` (validation,
text normalization, heuristic domain/technology tagging, deduplication),
and writes the combined, deduplicated, tagged corpus to
`data/processed/problems.json`. See that module's docstring for details on
the cleaning/dedup rules, and `app/core/taxonomy.py` for the domain/tech
keyword lists driving the (Phase 1, heuristic-only) tagging.
