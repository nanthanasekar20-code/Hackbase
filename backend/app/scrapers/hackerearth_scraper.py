from app.scrapers.base_scraper import BaseScraper


class HackerEarthScraper(BaseScraper):
    """
    HackerEarth renders listings client-side, so this needs a headless
    browser (Playwright) rather than a plain requests/BeautifulSoup pull.
    """

    source_name = "hackerearth"

    def fetch(self) -> list[dict]:
        # TODO: implement with Playwright once headless scraping coverage expands
        return []
