"""Internet job search (plan 3.7).

Google Custom Search is deliberately NOT an option: closed to new customers,
shut down 2027-01-01. Providers: Brave (own index, free tier) or Tavily
(AI-ready snippets). Saving a result as a notice only downloads from the
trusted-domain allowlist (SSRF / hostile-page guard).
"""
from __future__ import annotations

from urllib.parse import urlparse

import httpx

from app.core.config import get_settings


class SearchUnavailable(RuntimeError):
    pass


def search(query: str, count: int = 5) -> list[dict]:
    s = get_settings()
    print(f"search_provider: {s.search_provider}, brave_api_key: {s.brave_api_key}, tavily_api_key: {s.tavily_api_key}")
    if s.search_provider == "brave" and s.brave_api_key:
        r = httpx.get("https://api.search.brave.com/res/v1/web/search",
                      params={"q": query, "count": count},
                      headers={"X-Subscription-Token": s.brave_api_key, "Accept": "application/json"}, timeout=20)
        r.raise_for_status()
        return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")}
                for x in r.json().get("web", {}).get("results", [])]
    if s.search_provider == "tavily" and s.tavily_api_key:
        r = httpx.post("https://api.tavily.com/search",
                       json={"api_key": s.tavily_api_key, "query": query, "max_results": count}, timeout=20)
        r.raise_for_status()
        return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")[:400]}
                for x in r.json().get("results", [])]
    raise SearchUnavailable("Search is not configured. Set SEARCH_PROVIDER=brave or tavily with its API key.")


def allowed_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if urlparse(url).scheme not in ("http", "https") or not host:
        return False
    return any(host == d or host.endswith("." + d) for d in get_settings().search_domain_list)


def fetch_page(url: str) -> tuple[bytes, str]:
    if not allowed_url(url):
        raise SearchUnavailable("That site is not on the trusted list, so I cannot save it as a notice.")
    r = httpx.get(url, timeout=30, follow_redirects=True, headers={"User-Agent": "ApplyPilot/1.0"})
    r.raise_for_status()
    if len(r.content) > 5 * 1024 * 1024:
        raise SearchUnavailable("That page is larger than 5 MB.")
    return r.content, r.headers.get("content-type", "")
