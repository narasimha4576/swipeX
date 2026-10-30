import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from app.importers import ashby, greenhouse, lever
from app.importers.greenhouse import job_type_for, parse_time

SUFFIXES = {
    "inc", "incorporated", "ltd", "limited", "llc", "llp", "pvt", "private", "corp",
    "corporation", "company", "co", "technologies", "technology", "tech", "solutions",
    "labs", "systems", "software", "group", "holdings", "india", "global", "services",
}
MAX_JOBS = 25


def board_guesses(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", name.lower())
    core = [w for w in words if w not in SUFFIXES] or words
    guesses: list[str] = []

    def add(value: str) -> None:
        if value and value not in guesses:
            guesses.append(value)

    add("".join(core))
    add("-".join(core))
    add("".join(words))
    add("-".join(words))
    if core and len(core[0]) >= 4:
        add(core[0])
    return guesses[:5]


def _iso(value) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    parsed = parse_time(value) if isinstance(value, str) else None
    return parsed.isoformat() if parsed else None


def _from_greenhouse(raw: dict):
    title = (raw.get("title") or "").strip()
    return (
        title,
        (raw.get("location") or {}).get("name"),
        raw.get("absolute_url"),
        raw.get("first_published") or raw.get("updated_at"),
        title,
    )


def _from_lever(raw: dict):
    categories = raw.get("categories") or {}
    title = (raw.get("text") or "").strip()
    return (
        title,
        categories.get("location"),
        raw.get("hostedUrl") or raw.get("applyUrl"),
        raw.get("createdAt"),
        f"{title} {categories.get('commitment') or ''}",
    )


def _from_ashby(raw: dict):
    title = (raw.get("title") or "").strip()
    return (
        title,
        raw.get("location"),
        raw.get("jobUrl") or raw.get("applyUrl"),
        raw.get("publishedAt"),
        f"{title} {raw.get('employmentType') or ''}",
    )


SOURCES = [(greenhouse, _from_greenhouse), (lever, _from_lever), (ashby, _from_ashby)]


def _try(module, mapper, token: str):
    try:
        with httpx.Client(timeout=8, headers=greenhouse.HEADERS, follow_redirects=True) as client:
            if module is greenhouse:
                raws = greenhouse.fetch_jobs(token, client, with_content=False)
            else:
                raws = module.fetch_jobs(token, client)
    except Exception:
        return None

    jobs = []
    for raw in raws[:200]:
        title, location, url, posted, kind_text = mapper(raw)
        if not title or not url or not str(url).startswith("https://"):
            continue
        jobs.append(
            {
                "title": title[:200],
                "location": location,
                "url": url,
                "posted": _iso(posted),
                "job_type": job_type_for(kind_text),
                "source": module.SOURCE,
                "board_url": module.board_url(token),
            }
        )
    return jobs or None


def find_jobs(name: str) -> list[dict]:
    tasks = [(module, mapper, token) for token in board_guesses(name) for module, mapper in SOURCES]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda task: (task, _try(*task)), tasks))

    found: list[dict] = []
    used_sources: set[str] = set()
    for (module, _mapper, _token), jobs in results:
        if jobs and module.SOURCE not in used_sources:
            used_sources.add(module.SOURCE)
            found.extend(jobs)
    found.sort(key=lambda job: job["posted"] or "", reverse=True)
    return found[:MAX_JOBS]