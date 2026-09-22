from app.scrapers.base_scraper import BaseScraper


class DevpostScraper(BaseScraper):
    source_name = "devpost"

    def fetch(self) -> list[dict]:
        # TODO: implement — check Devpost ToS before scraping at scale
        return []
