"""Manitoba pre-foreclosure / probate lead source.

Realistic approach: Manitoba court registries do not publish a clean scrapeable
docket feed. This module documents the manual pipeline AND scrapes what is
publicly available: the Manitoba Courts decisions/judgments pages for
foreclosure-related filings, which sometimes name properties.

This is a starting point, not a finished data feed. The honest workflow is:
  1. Weekly manual check of the registries (module prints the checklist).
  2. Anything found gets entered via the CRM "Add lead" form.
"""
from .base import BaseScraper, normalize_lead

MANUAL_CHECKLIST = [
    "Manitoba Court of King's Bench foreclosure filings (court registry, in person or via agent)",
    "Manitoba probate applications (public search at the court registry)",
    "Winnipeg tax sale list (City of Winnipeg tax sales, published periodically)",
    "Manitoba Gazette notices",
]


class ManitobaProbateScraper(BaseScraper):
    name = "manitoba_probate"

    def scrape(self, **kwargs) -> list[dict]:
        # No reliable public feed; return the manual checklist as guidance.
        # The scheduler logs this so Jay's mom sees the reminder, not fake leads.
        return []

    def checklist(self) -> list[str]:
        return MANUAL_CHECKLIST
