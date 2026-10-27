from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

HEADERS = {"User-Agent": "SwipeX-portfolio-project/1.0 (educational project)"}
SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def hostname(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def registrable_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def check_website(url: str, client: httpx.Client) -> dict:
    target = url if url.startswith("http") else "https://" + url
    result = {"reachable": False, "https": False, "status": None}
    try:
        response = client.get(target, follow_redirects=True, timeout=8)
        result["status"] = response.status_code
        # Some real sites answer bots with 403, so anything below 500 counts as "alive".
        result["reachable"] = response.status_code < 500
        result["https"] = str(response.url).startswith("https://")
    except Exception:
        pass
    return result


def domain_registered_on(host: str, client: httpx.Client) -> datetime | None:
    try:
        response = client.get(
            f"https://rdap.org/domain/{registrable_domain(host)}",
            follow_redirects=True,
            timeout=10,
        )
        if response.status_code != 200:
            return None
        for event in response.json().get("events", []):
            if event.get("eventAction") == "registration" and event.get("eventDate"):
                value = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                if value.tzinfo is not None:
                    value = value.astimezone(timezone.utc).replace(tzinfo=None)
                return value
    except Exception:
        return None
    return None