"""Scraper base: polite by default. Every module must:
  - check robots.txt before fetching
  - rate-limit (default: >= 3s between requests, configurable)
  - never log in, never bypass paywalls
  - return normalized lead dicts
"""
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "WholesaleStackBot/1.0 (+lead research; contact: owner of this server)"

_last_hit: dict[str, float] = {}


def _client() -> httpx.Client:
    # trust_env=False: the sandbox's no_proxy entries (bracketed IPv6) crash
    # httpx's proxy parsing. We pass the egress proxy explicitly instead.
    import os
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    verify = os.environ.get("SSL_CERT_FILE") or True
    return httpx.Client(proxy=proxy, trust_env=False, verify=verify, timeout=25.0,
                        follow_redirects=True, headers={"User-Agent": USER_AGENT})


def robots_allows(url: str) -> bool:
    """Best-effort robots.txt check. If robots.txt can't be fetched, allow."""
    try:
        import urllib.request
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(raw.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def polite_get(url: str, min_interval: float = 3.0, timeout: float = 25.0) -> httpx.Response:
    host = urlparse(url).netloc
    now = time.monotonic()
    wait = min_interval - (now - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    if not robots_allows(url):
        raise PermissionError(f"robots.txt disallows fetching {url}")
    with _client() as client:
        r = client.get(url)
    _last_hit[host] = time.monotonic()
    r.raise_for_status()
    return r


def soup_of(response: httpx.Response) -> BeautifulSoup:
    return BeautifulSoup(response.text, "html.parser")


def normalize_lead(**kwargs) -> dict:
    """Shape every scraper's output the same way the CRM expects."""
    return {
        "address": kwargs.get("address", "").strip(),
        "city": kwargs.get("city", "Winnipeg").strip() or "Winnipeg",
        "postal": kwargs.get("postal", ""),
        "source": kwargs.get("source", "scraper"),
        "source_url": kwargs.get("source_url", ""),
        "tags": kwargs.get("tags", ""),
        "asking_price": kwargs.get("asking_price"),
        "motivation": kwargs.get("motivation", ""),
        "owner_name": kwargs.get("owner_name", ""),
        "owner_phone": kwargs.get("owner_phone", ""),
    }


class BaseScraper:
    name = "base"
    min_interval = 3.0

    def fetch(self, url: str) -> BeautifulSoup:
        return soup_of(polite_get(url, min_interval=self.min_interval))

    def scrape(self, **kwargs) -> list[dict]:
        raise NotImplementedError
