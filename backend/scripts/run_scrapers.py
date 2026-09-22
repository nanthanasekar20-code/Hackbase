"""
Runs all registered scrapers and writes raw output to data/raw/.
Each scraper degrades gracefully — one failing source won't stop the rest.

Run as: python scripts/run_scrapers.py
"""

import json
from pathlib import Path

from app.scrapers.sih_scraper import SIHScraper
from app.scrapers.devpost_scraper import DevpostScraper
from app.scrapers.unstop_scraper import UnstopScraper
from app.scrapers.hackerearth_scraper import HackerEarthScraper

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

SCRAPERS = [SIHScraper(), DevpostScraper(), UnstopScraper(), HackerEarthScraper()]


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for scraper in SCRAPERS:
        records = scraper.run_safe()
        out_path = RAW_DIR / f"{scraper.source_name}.json"
        out_path.write_text(json.dumps(records, indent=2))
        print(f"[{scraper.source_name}] wrote {len(records)} records -> {out_path}")


if __name__ == "__main__":
    main()
