"""Craigslist Winnipeg housing-for-sale scraper (no login, polite rate limiting)."""
import re

from .base import BaseScraper, normalize_lead

SEARCH_URL = "https://winnipeg.craigslist.org/search/sss?query=house+for+sale+by+owner&sort=date"


class CraigslistWinnipegScraper(BaseScraper):
    name = "craigslist_winnipeg"

    def scrape(self, max_pages: int = 1, query: str | None = None) -> list[dict]:
        url = query or SEARCH_URL
        soup = self.fetch(url)
        leads: list[dict] = []
        for li in soup.select("li.cl-search-result"):
            a = li.select_one("a.cl-search-result-link, a.posting-title")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if href.startswith("/"):
                href = "https://winnipeg.craigslist.org" + href
            price_el = li.select_one(".priceinfo, .price")
            price = None
            if price_el:
                m = re.search(r"[\d,]+", price_el.get_text())
                if m:
                    price = float(m.group(0).replace(",", ""))
            hood = li.select_one(".meta .separator + span, .location")
            leads.append(normalize_lead(
                address=title[:120],
                city="Winnipeg",
                source="craigslist_winnipeg",
                source_url=href,
                asking_price=price,
                tags="craigslist",
                motivation=hood.get_text(strip=True) if hood else "",
            ))
            if len(leads) >= 25:
                break
        return leads
