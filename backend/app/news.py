import time
from email.utils import parsedate_to_datetime
from datetime import timezone
from urllib.parse import quote_plus

import httpx
from defusedxml import ElementTree as ET

FEED = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
HEADERS = {"User-Agent": "SwipeX-portfolio-project/1.0 (educational project)"}
CACHE_SECONDS = 1800
_cache: dict[str, tuple[float, list[dict]]] = {}


def recent_news(company_name: str, limit: int = 8) -> list[dict]:
    key = company_name.strip().lower()
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    items: list[dict] = []
    try:
        response = httpx.get(
            FEED.format(query=quote_plus(f'"{company_name}"')),
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        words = key.split()
        first_word = words[0] if words else key

        for node in root.iter("item"):
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            if not title or not link.startswith(("http://", "https://")):
                continue
            if len(first_word) >= 3 and first_word not in title.lower():
                continue

            source_node = node.find("source")
            source = (source_node.text or "").strip() if source_node is not None else ""
            if source and title.endswith(" - " + source):
                title = title[: -len(" - " + source)]

            published = None
            raw_date = node.findtext("pubDate")
            if raw_date:
                try:
                    published = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
                except (TypeError, ValueError):
                    published = None

            items.append(
                {
                    "title": title,
                    "link": link,
                    "source": source or None,
                    "published_at": published.isoformat() if published else None,
                    "_sort": published.timestamp() if published else 0,
                }
            )
    except Exception:
        return []

    items.sort(key=lambda item: item["_sort"], reverse=True)
    result = [{k: v for k, v in item.items() if k != "_sort"} for item in items[:limit]]
    _cache[key] = (time.time(), result)
    return result