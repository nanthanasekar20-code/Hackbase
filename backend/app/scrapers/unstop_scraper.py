from app.scrapers.base_scraper import BaseScraper


class UnstopScraper(BaseScraper):
    source_name = "unstop"

    def fetch(self) -> list[dict]:
        # TODO: implement
        return []
