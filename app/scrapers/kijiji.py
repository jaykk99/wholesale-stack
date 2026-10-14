"""Kijiji Winnipeg real-estate scraper (no login, polite rate limiting).

Note: Kijiji aggressively rate-limits bots. This module backs off on 403/429
and is safe to run on a slow schedule (default: once per day).
"""
import re
import time

import httpx

from .base import BaseScraper, normalize_lead, polite_get, soup_of

SEARCH_URL = "https://www.kijiji.ca/b-house-for-sale/winnipeg/c35l1700192"


class KijijiWinnipegScraper(BaseScraper):
    name = "kijiji_winnipeg"
    min_interval = 5.0

    def scrape(self, max_results: int = 20) -> list[dict]:
        try:
            soup = soup_of(polite_get(SEARCH_URL, min_interval=self.min_interval))
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 429):
                return []  # blocked or rate-limited: back off quietly
            raise
        leads: list[dict] = []
        for card in soup.select('[data-testid="listing-card"], .search-item'):
            link_el = card.select_one('[data-testid="listing-link"]')
            title_el = card.select_one('[data-testid="listing-title"]')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = (link_el.get("href", "") if link_el else "") or ""
            if link.startswith("/"):
                link = "https://www.kijiji.ca" + link
            price_el = card.select_one('[data-testid="listing-price"], .price')
            price = None
            if price_el:
                m = re.search(r"[\d,]+", price_el.get_text())
                if m:
                    price = float(m.group(0).replace(",", ""))
            leads.append(normalize_lead(
                address=title[:120], city="Winnipeg", source="kijiji_winnipeg",
                source_url=link, asking_price=price, tags="kijiji",
            ))
            if len(leads) >= max_results:
                break
        return leads
