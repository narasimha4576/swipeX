import os
import re
import time

import httpx

from app.database import SessionLocal
from app.geo import detect_country
from app.importers import thirdparty
from app.importers.greenhouse import clean_html, infer_level, job_type_for, parse_time
from app.skills import extract_skills

SOURCE = "adzuna"
COUNTRIES = [c.strip() for c in os.getenv("ADZUNA_COUNTRIES", "in,gb,us,ca,au,de,sg").split(",") if c.strip()]
QUERIES = ("", "intern", "apprentice")
MIN_GAP_SECONDS = 6 * 3600
_last_run = 0.0


def enabled() -> bool:
    return bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))


def to_item(raw: dict, code: str) -> dict | None:
    title = re.sub(r"<[^>]+>", "", raw.get("title") or "").strip()
    url = (raw.get("redirect_url") or "").strip()
    company = ((raw.get("company") or {}).get("display_name") or "").strip()
    place = raw.get("location") or {}
    location = (place.get("display_name") or "").strip()
    if not title or not url or not company:
        return None

    description = clean_html(raw.get("description") or "")[:5000]
    if len(description) < 20:
        description = f"{title}. Open the listing for the full description."

    job_type = job_type_for(title)
    if job_type == "full_time":
        if raw.get("contract_time") == "part_time":
            job_type = "part_time"
        elif raw.get("contract_type") == "contract":
            job_type = "contract"

    low, high = raw.get("salary_min"), raw.get("salary_max")
    predicted = str(raw.get("salary_is_predicted", "0")) == "1"
    salary_min = salary_max = None
    if code == "in" and low and high and not predicted:
        salary_min, salary_max = round(low / 100000, 1), round(high / 100000, 1)

    area = " ".join(place.get("area") or [])
    lowered = f"{title} {location}".lower()
    return {
        "company_name": company,
        "city": location,
        "external_id": str(raw.get("id")),
        "title": title[:200],
        "description": description,
        "location": location[:120] or None,
        "country": detect_country(f"{area} {location}"),
        "is_remote": "remote" in lowered or "work from home" in lowered,
        "job_type": job_type,
        "experience_level": infer_level(title),
        "salary_min_lpa": salary_min,
        "salary_max_lpa": salary_max,
        "skills": extract_skills(f"{title}\n{description}", limit=12),
        "apply_url": url[:1000],
        "created_at": parse_time(raw.get("created")),
    }


def sync(client: httpx.Client) -> dict:
    global _last_run
    result = {"created": 0, "updated": 0, "closed": 0}
    if time.time() - _last_run < MIN_GAP_SECONDS:
        return result
    _last_run = time.time()

    started = thirdparty.now_utc()
    items = []
    for code in COUNTRIES:
        for query in QUERIES:
            params = {
                "app_id": os.getenv("ADZUNA_APP_ID"),
                "app_key": os.getenv("ADZUNA_APP_KEY"),
                "results_per_page": 50,
                "max_days_old": 14,
                "sort_by": "date",
            }
            if query:
                params["what"] = query
            try:
                response = client.get(
                    f"https://api.adzuna.com/v1/api/jobs/{code}/search/1", params=params, timeout=30
                )
                response.raise_for_status()
                results = response.json().get("results", [])
            except Exception as exc:
                print(f"  Adzuna {code} '{query}' failed: {exc}", flush=True)
                continue
            for raw in results:
                item = to_item(raw, code)
                if item:
                    items.append(item)
            time.sleep(1)

    with SessionLocal() as db:
        counts = thirdparty.upsert_jobs(db, SOURCE, items, started)
        result["created"], result["updated"] = counts["created"], counts["updated"]
        result["closed"] = thirdparty.close_stale(db, SOURCE, started, 3)
    return result