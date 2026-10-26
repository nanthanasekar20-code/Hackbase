"""
Unstop blocks automated access — part of the main problem corpus
(data/processed/problems.json via scripts/run_scrapers.py ->
build_corpus.py). Separate from app/scrapers/live_unstop_scraper.py
(the Live Hackathons feed's scraper), which already documented this same
finding — re-verified fresh here rather than assumed:

- A plain `requests.get()` to unstop.com/sitemap (listed in its own
  robots.txt) got the connection reset — `curl` exit 7, no response at
  all.
- Minutes later, the *opposite* paths failed: the homepage itself
  returned connection-refused (curl exit 000) while /hackathons and
  /directory/... both returned a real 200. The failure isn't tied to a
  specific path at all — it moves around between checks, consistent with
  rate-limiting/fingerprint-based blocking rather than a fixed rule this
  scraper could route around.
- Separately, even when a request *does* succeed, unstop.com/hackathons
  is an Angular SPA (confirmed live: the raw HTML is a ~24KB app shell —
  polyfills.js/main.js bundles, no listing markup) — real data would need
  a headless browser regardless of the connection issue above.

Both problems together (intermittent active blocking + client-side
rendering) mean there's no reliable way to get real data here without
retrying aggressively or adding stealth/evasion techniques to get past
the blocking — which would cross from "scrape like a normal visitor"
into deliberately evading anti-bot protection. This stays unimplemented
rather than attempting that; see live_unstop_scraper.py for the same
conclusion reached independently for the Live Hackathons feed.
"""

from __future__ import annotations

from app.scrapers.base_scraper import BaseScraper


class UnstopScraper(BaseScraper):
    source_name = "unstop"

    def fetch(self) -> list[dict]:
        return []
