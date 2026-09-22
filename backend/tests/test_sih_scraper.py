"""
Unit test for SIHScraper's HTML parsing logic, using a small fixture that
mirrors the real sih.gov.in table+modal structure. This intentionally does
NOT hit the network — fetch() (the network call) is a thin wrapper around
parse() (the pure parsing logic tested here), so CI stays fast and
deterministic regardless of whether sih.gov.in is reachable.

The fixture deliberately includes a row with extra hidden `<td>` cells
(cells 7+, unused) — this is exactly the real live 2026 page's structure
(18 `<td>`s per row vs. 2025's 7), which broke the old fixed-column-index
parsing: organization/category/theme/external_id must come from the
modal's label/value pairs, not a `<td>` position, or they silently read
the wrong cell.
"""

from bs4 import BeautifulSoup

from app.scrapers.sih_scraper import SIHScraper

FIXTURE_HTML = """
<html><body>
<table id="dataTablePS">
  <tbody>
    <tr>
      <td>1</td>
      <td>Ministry of Testing (unused - real org comes from modal)</td>
      <td><a data-target="#modal25001">Smart Test Monitoring System</a></td>
      <td>hidden-extra-1</td>
      <td>hidden-extra-2</td>
      <td>hidden-extra-3</td>
      <td>hidden-extra-4</td>
      <td>hidden-extra-5</td>
      <td>hidden-extra-6</td>
      <td>hidden-extra-7</td>
    </tr>
    <tr>
      <td>2</td>
      <td>Ministry of Roads</td>
      <td><a data-target="#modal25002">Pothole Detection Using Computer Vision</a></td>
    </tr>
    <tr>
      <td>3</td>
      <td>Some Org</td>
      <td>No link here, should be skipped</td>
    </tr>
    <tr>
      <td>4</td>
      <td>Ministry of Nothing</td>
      <td><a data-target="#modal-does-not-exist">Has a link but no matching modal</a></td>
    </tr>
  </tbody>
</table>

<div id="modal25001">
  <table id="settings">
    <tr><th>Problem Statement ID</th><td>25001</td></tr>
    <tr><th>Problem Statement Title</th><td>Smart Test Monitoring System</td></tr>
    <tr><th>Description</th><td>Build a system that<br/>monitors test outcomes in real time.</td></tr>
    <tr><th>Organization</th><td>Ministry of Testing</td></tr>
    <tr><th>Department</th><td>Ministry of Testing / QA Wing</td></tr>
    <tr><th>Category</th><td>Software</td></tr>
    <tr><th>Theme</th><td>MedTech / BioTech / HealthTech</td></tr>
    <tr><th>Youtube Link</th><td></td></tr>
  </table>
</div>

<div id="modal25002">
  <table id="settings">
    <tr><th>Problem Statement ID</th><td>25002</td></tr>
    <tr><th>Description</th><td>Use computer vision on dashcam footage to detect potholes automatically.</td></tr>
    <tr><th>Organization</th><td>Ministry of Roads</td></tr>
    <tr><th>Category</th><td>Hardware</td></tr>
    <tr><th>Theme</th><td>Transportation &amp; Logistics</td></tr>
  </table>
</div>
</body></html>
"""


def test_sih_scraper_parses_rows_and_modals():
    scraper = SIHScraper(year="2025")
    soup = BeautifulSoup(FIXTURE_HTML, "html.parser")
    records = scraper.parse(soup)

    # Row 3 (no <a> link) and row 4 (link but no matching modal) must both
    # be skipped, not crash the parse or fabricate missing fields.
    assert len(records) == 2

    first = records[0]
    assert first["title"] == "Smart Test Monitoring System"
    assert first["organization"] == "Ministry of Testing"
    assert first["category"] == "Software"
    assert first["external_id"] == "SIH25001"
    assert first["theme"] == "MedTech / BioTech / HealthTech"
    assert "monitors test outcomes in real time" in first["description"]
    assert first["source"] == "sih"
    assert first["hackathon_name"] == "Smart India Hackathon 2025"
    assert first["url"] == "https://sih.gov.in/sih2025PS"
    assert first["fetched_at"]  # non-empty ISO timestamp

    second = records[1]
    assert second["title"] == "Pothole Detection Using Computer Vision"
    assert second["external_id"] == "SIH25002"
    assert second["organization"] == "Ministry of Roads"
    assert second["category"] == "Hardware"
    assert second["theme"] == "Transportation & Logistics"
    assert "computer vision on dashcam footage" in second["description"]


def test_sih_scraper_handles_missing_table_gracefully():
    scraper = SIHScraper(year="2025")
    soup = BeautifulSoup("<html><body>page changed, no table here</body></html>", "html.parser")
    assert scraper.parse(soup) == []
