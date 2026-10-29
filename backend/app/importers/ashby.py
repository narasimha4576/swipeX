import httpx

from app.importers.greenhouse import clean_html, infer_level, is_relevant, job_type_for, parse_time
from app.skills import extract_skills

SOURCE = "ashby"
LABEL = "Ashby"
API = "https://api.ashbyhq.com/posting-api/job-board"


def board_url(token: str) -> str:
    return f"https://jobs.ashbyhq.com/{token}"


def fetch_board_name(token: str, client: httpx.Client) -> str | None:
    return None


def fetch_jobs(token: str, client: httpx.Client) -> list[dict]:
    response = client.get(f"{API}/{token}", params={"includeCompensation": "false"})
    response.raise_for_status()
    return response.json().get("jobs", [])


def to_job_fields(raw: dict) -> dict | None:
    if raw.get("isListed") is False:
        return None
    title = (raw.get("title") or "").strip()
    location = (raw.get("location") or "").strip()
    others = []
    for item in raw.get("secondaryLocations") or []:
        name = item.get("location") if isinstance(item, dict) else str(item)
        if name:
            others.append(name)
    location_text = "; ".join([location] + others)
    apply_url = (raw.get("applyUrl") or raw.get("jobUrl") or "").strip()
    if not title or not apply_url or not is_relevant(title, location_text):
        return None

    description = (raw.get("descriptionPlain") or clean_html(raw.get("descriptionHtml") or "")).strip()[:5000]
    if len(description) < 20:
        description = f"{title}. Open the company page for the full description."

    employment = raw.get("employmentType") or ""
    text = f"{title} {employment}"
    return {
        "external_id": str(raw.get("id") or raw.get("jobId") or apply_url),
        "title": title[:200],
        "description": description,
        "location": (location or location_text)[:120] or None,
        "is_remote": bool(raw.get("isRemote"))
        or any(w in location_text.lower() for w in ("remote", "anywhere", "worldwide")),
        "job_type": job_type_for(text),
        "experience_level": infer_level(text),
        "skills": extract_skills(f"{title}\n{description}", limit=12),
        "apply_url": apply_url[:1000],
        "created_at": parse_time(raw.get("publishedAt") or raw.get("publishedDate")),
    }