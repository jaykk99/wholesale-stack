from .base import BaseScraper
from .craigslist import CraigslistWinnipegScraper
from .kijiji import KijijiWinnipegScraper
from .probate import ManitobaProbateScraper
from .us_county_stub import USCountyScraper

SCRAPERS = {
    "craigslist_winnipeg": CraigslistWinnipegScraper,
    "kijiji_winnipeg": KijijiWinnipegScraper,
    "manitoba_probate": ManitobaProbateScraper,
    "us_county_stub": USCountyScraper,
}


def run_scraper(name: str, **kwargs) -> list[dict]:
    cls = SCRAPERS.get(name)
    if not cls:
        raise ValueError(f"unknown scraper: {name}")
    return cls().scrape(**kwargs)
