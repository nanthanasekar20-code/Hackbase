"""
Shared helper for live-hackathon scrapers that need a real rendered DOM —
Devfolio, Taikai, HackerEarth and Hack2Skill all build their listing pages
client-side (no listing data in the raw HTTP response, confirmed by
diffing a plain `requests.get()` against what actually renders), so a
plain requests + BeautifulSoup pull would see an empty app shell. This
spins up a real (headless) Chromium tab via Playwright, lets the page's
own JS populate the DOM, and hands back the fully-rendered HTML —
`BeautifulSoup` then parses that exactly like any server-rendered page,
keeping every scraper's own parse() logic consistent regardless of which
fetch method it used.
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def render_html(url: str, *, wait_ms: int = 4000, scroll_times: int = 0, timeout_ms: int = 30000) -> str:
    """
    Loads `url` in a real headless Chromium tab and returns the DOM's
    HTML after client-side JS has run — unlike a plain HTTP GET, which
    only returns the server's initial (often near-empty) response body
    for a client-rendered page.

    `wait_ms` gives the page's own JS time to fetch and render its data
    after the initial HTML loads. `scroll_times` simulates scrolling
    (some listings lazy-load more cards as the page scrolls) — each
    "scroll" is a mouse-wheel tick followed by a short pause.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            for _ in range(scroll_times):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1000)
            return page.content()
        finally:
            browser.close()
