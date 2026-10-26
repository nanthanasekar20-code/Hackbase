"""
Runs every "Live Hackathons" scraper (see app/scrapers/live_*.py) and
writes the merged result to data/processed/live_hackathons.json.

This is a separate, much simpler feed from the problem-statement corpus
(data/processed/problems.json) and its scrape -> build -> index pipeline
(scripts/run_scrapers.py, scripts/build_corpus.py,
app/rag/index_builder.py) — nothing here touches that file or those
scripts. Just hackathon name + source + official link, refreshed
periodically, no database table.

Each scraper runs via run_safe() (see app/scrapers/base_scraper.py), so
one failing/blocked source (see live_unstop_scraper.py,
live_dorahacks_scraper.py, live_kaggle_scraper.py for the three that are
genuinely blocked by anti-bot protection) never stops the others —
same graceful-degradation philosophy as the existing scrapers.

Run as: python scripts/run_live_hackathons.py
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.scrapers.live_angelhack_scraper import LiveAngelHackScraper
from app.scrapers.live_devfolio_scraper import LiveDevfolioScraper
from app.scrapers.live_devpost_scraper import LiveDevpostScraper
from app.scrapers.live_dorahacks_scraper import LiveDoraHacksScraper
from app.scrapers.live_hack2skill_scraper import LiveHack2SkillScraper
from app.scrapers.live_hackerearth_scraper import LiveHackerEarthScraper
from app.scrapers.live_kaggle_scraper import LiveKaggleScraper
from app.scrapers.live_mlh_scraper import LiveMLHScraper
from app.scrapers.live_taikai_scraper import LiveTaikaiScraper
from app.scrapers.live_unstop_scraper import LiveUnstopScraper

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "live_hackathons.json"

SCRAPERS = [
    LiveDevpostScraper(),
    LiveMLHScraper(),
    LiveAngelHackScraper(),
    LiveDevfolioScraper(),
    LiveTaikaiScraper(),
    LiveHackerEarthScraper(),
    LiveHack2SkillScraper(),
    # Genuinely blocked by active anti-bot protection — always return []
    # (see each scraper's own docstring). Still run via run_safe() like
    # the rest, so this stays a no-op list entry rather than special-cased.
    LiveUnstopScraper(),
    LiveDoraHacksScraper(),
    LiveKaggleScraper(),
]


def run() -> dict:
    """Runs every scraper and returns the merged payload (also written to
    OUTPUT_PATH). Split out from main() so it can be called directly —
    e.g. from the scheduled job in app/services/live_hackathons_job.py —
    without going through a subprocess."""
    hackathons: list[dict] = []
    per_source_counts: dict[str, int] = {}

    for scraper in SCRAPERS:
        records = scraper.run_safe()
        per_source_counts[scraper.source_name] = len(records)
        hackathons.extend(records)
        logger.info("[%s] contributed %d hackathon(s)", scraper.source_name, len(records))

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(hackathons),
        "per_source_counts": per_source_counts,
        "hackathons": hackathons,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %d live hackathon(s) -> %s", len(hackathons), OUTPUT_PATH)
    return payload


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    payload = run()
    print(f"Wrote {payload['count']} live hackathon(s) -> {OUTPUT_PATH}")
    for source, count in payload["per_source_counts"].items():
        print(f"  [{source}] {count}")


if __name__ == "__main__":
    main()
