"""
Real scraper for Kaggle competition problem statements, via Kaggle's
official public API (the `kaggle` package) — part of the main problem
corpus (data/processed/problems.json via scripts/run_scrapers.py ->
build_corpus.py). Separate from app/scrapers/live_kaggle_scraper.py (the
Live Hackathons feed's scraper, which only needs title/url/deadline) —
this one pulls each competition's own `description` field, a real,
distinct problem statement Kaggle itself writes per competition, not a
generic site-wide blurb (the reason Devpost stays unregistered here —
see scripts/run_scrapers.py).

Same credential requirement and honest degradation as
live_kaggle_scraper.py: Kaggle's public API needs a real user's own
KAGGLE_USERNAME / KAGGLE_KEY (see .env.example), which this scraper
can't supply on its own — with no credentials configured, fetch() logs
why and returns [] rather than guessing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app.core.config import settings
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class KaggleScraper(BaseScraper):
    """Active Kaggle competitions' own problem descriptions."""

    source_name = "kaggle"

    def fetch(self) -> list[dict]:
        if not settings.kaggle_username or not settings.kaggle_key:
            logger.info(
                "Kaggle problem-statement scraper skipped: KAGGLE_USERNAME/"
                "KAGGLE_KEY aren't configured (see .env.example) — leaving "
                "this source empty rather than guessing at credentials."
            )
            return []

        # Same env-var authentication approach as live_kaggle_scraper.py —
        # see its comment for why this happens here rather than at import
        # time or via a separate kaggle.json file.
        os.environ["KAGGLE_USERNAME"] = settings.kaggle_username
        os.environ["KAGGLE_KEY"] = settings.kaggle_key

        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        response = api.competitions_list(group="general", sort_by="earliestDeadline", page_size=50)
        return self.parse(response.competitions if response else [])

    def parse(self, competitions: list) -> list[dict]:
        """Mapping logic split out from fetch() so it can be unit-tested
        against fixture competition objects without hitting the network."""
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []

        for comp in competitions:
            title = (getattr(comp, "title", "") or "").strip()
            description = (getattr(comp, "description", "") or "").strip()
            if not title or not description:
                # No real description text wouldn't be a meaningful problem
                # statement — same judgment call as HackerEarth's
                # titles-only case (see hackerearth_scraper.py): skip
                # rather than pad the corpus with a near-empty record.
                continue
            ref = (getattr(comp, "ref", "") or "").strip()
            records.append(
                {
                    "title": title,
                    "description": description,
                    "organization": getattr(comp, "organization_name", "") or None,
                    "source": self.source_name,
                    "hackathon_name": title,
                    "external_id": f"kaggle:{ref}" if ref else None,
                    "category": getattr(comp, "category", "") or None,
                    "theme": None,
                    "url": (getattr(comp, "url", "") or "").strip() or None,
                    "fetched_at": fetched_at,
                }
            )

        logger.info("Kaggle problem-statement scraper parsed %d competition(s)", len(records))
        return records
