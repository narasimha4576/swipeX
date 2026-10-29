import os
import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select

from app.database import SessionLocal
from app.importers.greenhouse import clean_html, infer_level, job_type_for, parse_time
from app.models import Company, Job
from app.skills import extract_skills

SOURCE = "adzuna"
API = "https://api.adzuna.com/v1/api/jobs/in/search/1"
QUERIES = (
    "intern", "internship", "apprentice", "fresher", "graduate engineer",
    "data analyst", "machine learning", "python developer",
)
RESULTS_PER_QUERY = 30
MAX_DAYS_OLD = 14


def enabled() -> bool:
    return bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY"))


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100]


def to_job_fields(raw: dict) -> dict | None:
    title = re.sub(r"<[^>]+>", "", raw.get("title") or "").strip()
    url = (raw.get("redirect_url") or "").strip()
    company_name = ((raw.get("company") or {}).get("display_name") or "").strip()
    location = ((raw.get("location") or {}).get("display_name") or "").strip()
    if not title or not url or not company_name:
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
    if low and high and not predicted:
        salary_min, salary_max = round(low / 100000, 1), round(high / 100000, 1)

    lowered = f"{title} {location}".lower()
    return {
        "company_name": company_name,
        "city": location,
        "external_id": str(raw.get("id")),
        "title": title[:200],
        "description": description,
        "location": location[:120] or None,
        "is_remote": "remote" in lowered or "work from home" in lowered,
        "job_type": job_type,
        "experience_level": infer_level(title),
        "salary_min_lpa": salary_min,
        "salary_max_lpa": salary_max,
        "skills": extract_skills(f"{title}\n{description}", limit=12),
        "apply_url": url[:1000],
        "created_at": parse_time(raw.get("created")),
    }


def get_company(db, name: str, city: str) -> Company:
    key = slug(name)
    company = db.scalar(select(Company).where(Company.source == SOURCE, Company.source_id == key))
    if company is None:
        taken = db.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
        company = Company(
            name=(name if taken is None else f"{name} (listing)")[:200],
            company_type="other",
            location=city or None,
            source=SOURCE,
            source_id=key,
            verification_status="unverified",
            verification_note="Found on a job aggregator. Not verified.",
        )
        db.add(company)
        db.flush()
    return company


def sync(client: httpx.Client) -> dict:
    created = updated = closed = 0
    started = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        for query in QUERIES:
            try:
                response = client.get(
                    API,
                    params={
                        "app_id": os.getenv("ADZUNA_APP_ID"),
                        "app_key": os.getenv("ADZUNA_APP_KEY"),
                        "results_per_page": RESULTS_PER_QUERY,
                        "what": query,
                        "max_days_old": MAX_DAYS_OLD,
                        "sort_by": "date",
                    },
                )
                response.raise_for_status()
                results = response.json().get("results", [])
            except Exception as exc:
                print(f"  Adzuna search '{query}' failed: {exc}", flush=True)
                continue

            for raw in results:
                fields = to_job_fields(raw)
                if fields is None:
                    continue
                company = get_company(db, fields.pop("company_name"), fields.pop("city"))
                external_id = fields.pop("external_id")
                posted = fields.pop("created_at", None)
                job = db.scalar(select(Job).where(Job.source == SOURCE, Job.external_id == external_id))
                if job is None:
                    extra = {"created_at": posted} if posted else {}
                    db.add(
                        Job(
                            company_id=company.id,
                            source=SOURCE,
                            external_id=external_id,
                            applicant_count=0,
                            is_active=True,
                            last_seen_at=started,
                            **fields,
                            **extra,
                        )
                    )
                    created += 1
                else:
                    for key, value in fields.items():
                        setattr(job, key, value)
                    job.is_active = True
                    job.last_seen_at = started
                    updated += 1
            db.commit()
            time.sleep(1)

        cutoff = started - timedelta(days=3)
        for job in db.scalars(
            select(Job).where(Job.source == SOURCE, Job.is_active.is_(True), Job.last_seen_at < cutoff)
        ):
            job.is_active = False
            closed += 1
        db.commit()
    return {"created": created, "updated": updated, "closed": closed}