from datetime import datetime, timezone

import httpx

from app.importers.greenhouse import clean_html, infer_level, is_relevant, job_type_for
from app.geo import detect_country
from app.skills import extract_skills

SOURCE = "lever"
LABEL = "Lever"
API = "https://api.lever.co/v0/postings"
EU_API = "https://api.eu.lever.co/v0/postings"


def board_url(token: str) -> str:
    return f"https://jobs.lever.co/{token}"


def fetch_board_name(token: str, client: httpx.Client) -> str | None:
    return None


def fetch_jobs(token: str, client: httpx.Client) -> list[dict]:
    for base in (API, EU_API):
        response = client.get(f"{base}/{token}", params={"mode": "json"})
        if response.status_code == 404:
            continue
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
    raise LookupError(f"Lever site '{token}' was not found")


def to_job_fields(raw: dict) -> dict | None:
    title = (raw.get("text") or "").strip()
    categories = raw.get("categories") or {}
    location = (categories.get("location") or "").strip()
    others = [x for x in (categories.get("allLocations") or []) if x and x != location]
    location_text = "; ".join([location] + others)
    apply_url = (raw.get("hostedUrl") or raw.get("applyUrl") or "").strip()
    if not title or not apply_url or not is_relevant(title, location_text):
        return None

    description = (raw.get("descriptionPlain") or clean_html(raw.get("description") or "")).strip()
    for block in raw.get("lists") or []:
        heading = (block.get("text") or "").strip()
        content = clean_html(block.get("content") or "")
        if heading or content:
            description += f"\n\n{heading}\n{content}"
    extra = (raw.get("additionalPlain") or clean_html(raw.get("additional") or "")).strip()
    if extra:
        description += f"\n\n{extra}"
    description = description.strip()[:5000]
    if len(description) < 20:
        description = f"{title}. Open the company page for the full description."

    posted = None
    created = raw.get("createdAt")
    if isinstance(created, (int, float)):
        posted = datetime.fromtimestamp(created / 1000, timezone.utc).replace(tzinfo=None)

    commitment = categories.get("commitment") or ""
    text = f"{title} {commitment}"
    return {
        "external_id": str(raw.get("id")),
        "title": title[:200],
        "description": description,
        "location": (location or location_text)[:120] or None,
        "country": detect_country(location_text),
        "is_remote": raw.get("workplaceType") == "remote"
        or any(w in location_text.lower() for w in ("remote", "anywhere", "worldwide")),
        "job_type": job_type_for(text),
        "experience_level": infer_level(text),
        "skills": extract_skills(f"{title}\n{description}", limit=12),
        "apply_url": apply_url[:1000],
        "created_at": posted,
    }