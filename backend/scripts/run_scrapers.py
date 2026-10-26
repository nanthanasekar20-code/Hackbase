"""
Runs all registered scrapers and writes raw output to data/raw/.
Each scraper degrades gracefully — one failing source won't stop the rest.

Run as: python scripts/run_scrapers.py

DevpostScraper is deliberately NOT registered here, even though the file
still exists (app/scrapers/devpost_scraper.py) and is fully implemented.
Devpost hackathons don't have distinct per-problem statements the way SIH
does — that scraper turns each hackathon's generic "About" blurb into a
single fake "problem statement," which showed up mixed into real
search/browse results next to genuine problem statements. Devpost
hackathons are already surfaced properly, as what they actually are, on
the separate Live Hackathons feed (app/scrapers/live_devpost_scraper.py +
scripts/run_live_hackathons.py — a different, correct scraper, untouched
by this). Keeping the file around (unregistered) rather than deleting it:
it'd be worth revisiting if it's ever extended to find real per-sponsor
challenge tracks instead of the whole-hackathon blurb.
"""

import json
from pathlib import Path

from app.scrapers.sih_scraper import SIHScraper
from app.scrapers.unstop_scraper import UnstopScraper
from app.scrapers.hackerearth_scraper import HackerEarthScraper

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

SCRAPERS = [SIHScraper(), UnstopScraper(), HackerEarthScraper()]


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for scraper in SCRAPERS:
        records = scraper.run_safe()
        out_path = RAW_DIR / f"{scraper.source_name}.json"
        out_path.write_text(json.dumps(records, indent=2))
        print(f"[{scraper.source_name}] wrote {len(records)} records -> {out_path}")


if __name__ == "__main__":
    main()
