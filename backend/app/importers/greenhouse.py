import html
import re
from datetime import datetime, timezone

import httpx

from app.skills import extract_skills

API = "https://boards-api.greenhouse.io/v1/boards"
HEADERS = {"User-Agent": "SwipeX-portfolio-project/1.0"}

# Only jobs whose location contains one of these words are imported.
LOCATION_KEYWORDS = (
    "india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai",
    "delhi", "gurgaon", "gurugram", "noida", "kolkata", "ahmedabad",
    "anywhere", "worldwide",
)
# Only jobs whose title contains one of these words are imported.
ROLE_KEYWORDS = (
    "engineer", "engineering", "developer", "software", "data", "machine learning",
    "ml", "ai", "analyst", "analytics", "scientist", "intern", "sde", "backend",
    "frontend", "full stack", "fullstack", "devops", "sre", "research",
)

ROLE_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in ROLE_KEYWORDS) + r")\b", re.I)
SENIOR_RE = re.compile(
    r"\b(senior|sr|staff|principal|lead|manager|director|architect|vp|head of)\b", re.I
)
FRESHER_RE = re.compile(
    r"\b(intern|internship|graduate|new grad|fresher|entry|junior|associate|trainee)\b", re.I
)


def fetch_board_name(token: str, client: httpx.Client) -> str | None:
    try:
        response = client.get(f"{API}/{token}")
        response.raise_for_status()
        return (response.json().get("name") or "").strip() or None
    except Exception:
        return None


def fetch_jobs(token: str, client: httpx.Client, with_content: bool = True) -> list[dict]:
    response = client.get(
        f"{API}/{token}/jobs", params={"content": "true"} if with_content else None
    )
    response.raise_for_status()
    return response.json().get("jobs", [])


def is_relevant(title: str, location: str) -> bool:
    location = location.lower()
    return any(k in location for k in LOCATION_KEYWORDS) and bool(ROLE_RE.search(title))


def clean_html(content: str) -> str:
    text = html.unescape(content or "")
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>|</div>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def infer_level(title: str) -> str:
    if SENIOR_RE.search(title):
        return "senior"
    if FRESHER_RE.search(title):
        return "fresher"
    return "mid"


def to_job_fields(raw: dict) -> dict | None:
    title = (raw.get("title") or "").strip()
    location = ((raw.get("location") or {}).get("name") or "").strip()
    apply_url = (raw.get("absolute_url") or "").strip()
    if not title or not apply_url or not is_relevant(title, location):
        return None

    description = clean_html(raw.get("content") or "")[:5000]
    if len(description) < 20:
        description = f"{title}. Open the company page for the full description."

    return {
        "external_id": str(raw.get("id")),
        "title": title[:200],
        "description": description,
        "location": location[:120] or None,
        "is_remote": any(w in location.lower() for w in ("remote", "anywhere", "worldwide")),
        "job_type": "internship" if "intern" in title.lower() else "full_time",
        "experience_level": infer_level(title),
        "skills": extract_skills(f"{title}\n{description}", limit=12),
        "apply_url": apply_url[:1000],
        "created_at": parse_time(raw.get("first_published")) or parse_time(raw.get("updated_at")),
    }