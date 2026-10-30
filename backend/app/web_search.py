import html
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


def videos_enabled() -> bool:
    return bool(os.getenv("YOUTUBE_API_KEY"))


def web_and_images(query: str) -> dict:
    # Works without a key (limited free use). A free TAVILY_API_KEY gives more.
    key = os.getenv("TAVILY_API_KEY")
    headers = {"Authorization": "Bearer " + key} if key else {"X-Tavily-Access-Mode": "keyless"}
    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            headers=headers,
            json={"query": query, "search_depth": "basic", "max_results": 8, "include_images": True},
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {"results": [], "images": []}

    results = []
    for item in data.get("results", []):
        url = str(item.get("url") or "")
        if url.startswith(("http://", "https://")):
            results.append(
                {
                    "title": (item.get("title") or url)[:200],
                    "url": url,
                    "snippet": (item.get("content") or "")[:300],
                }
            )

    images = []
    for item in data.get("images", [])[:8]:
        url = item if isinstance(item, str) else (item or {}).get("url")
        if isinstance(url, str) and url.startswith("https://"):
            images.append(url)
    return {"results": results, "images": images}


def videos(query: str) -> list[dict]:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return []
    try:
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 6,
                "safeSearch": "moderate",
                "key": key,
            },
            timeout=15,
        )
        response.raise_for_status()
    except Exception:
        return []

    found = []
    for item in response.json().get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id:
            continue
        thumbs = snippet.get("thumbnails") or {}
        thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        found.append(
            {
                "id": video_id,
                "title": html.unescape(snippet.get("title") or ""),
                "channel": html.unescape(snippet.get("channelTitle") or ""),
                "thumbnail": thumb,
                "published_at": snippet.get("publishedAt"),
            }
        )
    return found