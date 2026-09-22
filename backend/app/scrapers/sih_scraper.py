"""
Real scraper for Smart India Hackathon (SIH) official problem-statement
releases at https://sih.gov.in/sih{year}PS.

Page structure: the listing is server-rendered HTML — a
`<table id="dataTablePS">` with a title link (`<a data-target="#<id>">`) in
each real row's 3rd `<td>`. That link points to a hidden Bootstrap modal
`<div id="<id>">` containing a `<table id="settings">` of label/value
rows — Problem Statement ID, Problem Statement Title, Description,
Organization, Department, Category, Theme, Youtube Link, Dataset Link,
Contact info.

Every *other* structured field (organization, category, theme, the
PS-number-based external_id) is read from that modal by label, not by a
fixed `<td>` index. Verified against the live 2026 release (2025's listing
is empty now that 2026 is the active cycle) that this matters: 2026's
`<tr>` has 18 `<td>` cells, not the 8 visible ones a naive column-index
read would assume — DataTables renders extra hidden/duplicate columns for
its own search/sort machinery, and their positions aren't part of any
documented contract. The modal's label/value pairs are what's actually
rendered to a human reading the page and are stable regardless of how
many hidden columns the table happens to carry. A real row with a title
link but no matching modal is skipped (logged), never given fabricated
values, since there'd be no real source for them.

No JavaScript rendering is required, so plain requests + BeautifulSoup is
enough (unlike HackerEarth).

The site does apply basic bot-protection that rejects generic/non-browser
User-Agent headers with a 403, so this sends a realistic browser UA —
the same accommodation any normal browser visit makes, not an attempt to
bypass access controls.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from app.core.config import settings
from app.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"\s+", " ", value).strip()
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#039;", "'")):
        text = text.replace(entity, char)
    return text


def _extract_modal_fields(modal_div) -> dict[str, str]:
    """Pull label/value pairs out of a problem statement's detail modal."""
    fields: dict[str, str] = {}
    table = modal_div.find("table", {"id": "settings"}) if modal_div else None
    if not table:
        return fields
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = _clean_text(cells[0].get_text())
        value_cell = cells[1]
        if label.lower() == "description":
            html = re.sub(r"<br\s*/?>", "\n", str(value_cell))
            value = re.sub(r"\n\s*\n+", "\n\n", BeautifulSoup(html, "html.parser").get_text()).strip()
        else:
            link = value_cell.find("a")
            value = link.get("href", "").strip() if link and link.get("href") else _clean_text(value_cell.get_text())
        fields[label] = value
    return fields


class SIHScraper(BaseScraper):
    """
    Smart India Hackathon official problem-statement releases.
    Most reliable seed source — structured, stable, official format.
    """

    source_name = "sih"

    def __init__(self, year: str | None = None, timeout: int = 30):
        self.year = year or getattr(settings, "sih_year", "2025")
        self.base_url = f"https://sih.gov.in/sih{self.year}PS"
        self.timeout = timeout

    def fetch(self) -> list[dict]:
        response = requests.get(self.base_url, headers=_HEADERS, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return self.parse(soup)

    def parse(self, soup: BeautifulSoup) -> list[dict]:
        """Parsing logic split out from fetch() so it can be unit-tested
        against a saved/fixture HTML page without hitting the network."""
        table = soup.find("table", {"id": "dataTablePS"})
        tbody = table.find("tbody") if table else None
        if not tbody:
            logger.warning("SIH page structure changed — could not find table#dataTablePS > tbody")
            return []

        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        skipped_no_modal = 0

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue  # not a real listing row (DataTables renders some empty/template <tr>s)

            title_link = cells[2].find("a")
            if not title_link:
                continue
            title = _clean_text(title_link.get_text())

            modal_target = title_link.get("data-target", "")
            modal_div = soup.find("div", {"id": modal_target[1:]}) if modal_target.startswith("#") else None
            modal_fields = _extract_modal_fields(modal_div)
            if not modal_fields:
                # A row with a real title link should always have a modal —
                # if it doesn't, there's no reliable source for
                # organization/category/theme/PS-number for this row. Skip
                # rather than guess.
                skipped_no_modal += 1
                logger.warning("SIH row %r has a title link but no modal fields — skipping", title)
                continue

            ps_id = modal_fields.get("Problem Statement ID", "").strip()

            records.append(
                {
                    "title": modal_fields.get("Problem Statement Title") or title,
                    "description": modal_fields.get("Description", ""),
                    "organization": modal_fields.get("Organization") or modal_fields.get("Department"),
                    "source": self.source_name,
                    "hackathon_name": f"Smart India Hackathon {self.year}",
                    "external_id": f"SIH{ps_id}" if ps_id else None,
                    "category": modal_fields.get("Category") or None,
                    "theme": modal_fields.get("Theme") or None,
                    "url": self.base_url,
                    "fetched_at": fetched_at,
                }
            )

        if skipped_no_modal:
            logger.warning("SIH scraper skipped %d row(s) with no modal data (see above)", skipped_no_modal)

        logger.info("SIH scraper parsed %d problem statements from %s", len(records), self.base_url)
        return records
