import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Pluggable scraper interface. Each source (SIH, Devpost, Unstop, HackerEarth)
    implements `fetch`. Failures are caught and logged so one broken source
    never takes down the whole pipeline.
    """

    source_name: str = "base"

    @abstractmethod
    def fetch(self) -> list[dict]:
        raise NotImplementedError

    def run_safe(self) -> list[dict]:
        try:
            return self.fetch()
        except Exception as exc:  # graceful degradation
            logger.warning("Scraper '%s' failed: %s", self.source_name, exc)
            return []
