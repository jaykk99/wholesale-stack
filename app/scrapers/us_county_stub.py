"""US county-records module STUB.

County recorder / GIS / court sites differ per county and most require
per-county configuration (base URLs, parcel formats, search endpoints).
This stub defines the interface; fill in TARGET_COUNTY in .env or the
scraper config to activate a real county.

To activate for a county:
  1. Set WHOLESALE_US_COUNTY="Maricopa County, AZ" (example) in .env
  2. Implement the county's search URL pattern in county_search_url()
  3. Map the result HTML in parse_results()
"""
import os

from .base import BaseScraper, normalize_lead


class USCountyScraper(BaseScraper):
    name = "us_county_stub"

    def __init__(self):
        self.target_county = os.environ.get("WHOLESALE_US_COUNTY", "")

    def county_search_url(self) -> str:
        raise NotImplementedError(
            "Set WHOLESALE_US_COUNTY and implement county_search_url() for that county."
        )

    def parse_results(self, soup) -> list[dict]:
        raise NotImplementedError("Implement parse_results() for the target county.")

    def scrape(self, **kwargs) -> list[dict]:
        if not self.target_county:
            return []  # stub inactive until a county is configured
        soup = self.fetch(self.county_search_url())
        return self.parse_results(soup)
