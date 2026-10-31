import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select

from app.database import SessionLocal
from app.geo import detect_country
from app.importers.greenhouse import clean_html, infer_level, job_type_for, parse_time
from app.models import Company, Job
from app.skills import extract_skills

MIN_GAP_SECONDS = 30 * 60
_last_run = 0.0


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:100]


def get_company(db, source: str, name: str, city: str | None) -> Company:
    key = slug(name) or "unknown"
    company = db.scalar(select(Company).where(Company.source == source, Company.source_id == key))
    if company is not None:
        return company
    candidates = [name, f"{name} ({source})"] + [f"{name} ({source} {n})" for n in range(2, 6)]
    for candidate in candidates:
        taken = db.scalar(select(Company).where(func.lower(Company.name) == candidate[:200].lower()))
        if taken is None:
            company = Company(
                name=candidate[:200],
                company_type="other",
                location=city or None,
                source=source,
                source_id=key,
                verification_status="unverified",
                verification_note="Third-party listing. Not verified by SwipeX.",
            )
            db.add(company)
            db.flush()
            return company
    raise RuntimeError("Could not create a company name")


def upsert_jobs(db, source: str, items: list[dict], started: datetime) -> dict:
    created = updated = 0
    for item in items:
        fields = dict(item)
        company = get_company(db, source, fields.pop("company_name"), fields.pop("city", None))
        external_id = fields.pop("external_id")
        posted = fields.pop("created_at", None)
        job = db.scalar(select(Job).where(Job.source == source, Job.external_id == external_id))
        if job is None:
            extra = {"created_at": posted} if posted else {}
            db.add(
                Job(
                    company_id=company.id,
                    source=source,
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
            job.company_id = company.id
            job.is_active = True
            job.last_seen_at = started
            updated += 1
    db.commit()
    return {"created": created, "updated": updated}


def close_stale(db, source: str, started: datetime, days: int) -> int:
    cutoff = started - timedelta(days=days)
    closed = 0
    for job in db.scalars(
        select(Job).where(Job.source == source, Job.is_active.is_(True), Job.last_seen_at < cutoff)
    ):
        job.is_active = False
        closed += 1
    db.commit()
    return closed


def fetch_remoteok(client: httpx.Client) -> list[dict]:
    response = client.get("https://remoteok.com/api", timeout=30)
    response.raise_for_status()
    items = []
    for raw in response.json():
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("position"):
            continue
        url = str(raw.get("url") or raw.get("apply_url") or "")
        company = (raw.get("company") or "").strip()
        if not url.startswith("https://") or not company:
            continue
        title = str(raw["position"]).strip()
        description = clean_html(raw.get("description") or "")[:5000]
        if len(description) < 20:
            description = f"{title} at {company}. Open the listing for the full description."
        tags = " ".join(str(t) for t in (raw.get("tags") or []))
        location = (raw.get("location") or "Remote").strip()
        items.append(
            {
                "company_name": company,
                "external_id": str(raw["id"]),
                "title": title[:200],
                "description": description,
                "location": location[:120],
                "country": detect_country(location),
                "is_remote": True,
                "job_type": job_type_for(title),
                "experience_level": infer_level(title),
                "skills": extract_skills(f"{title}\n{description}\n{tags}", limit=12),
                "apply_url": url[:1000],
                "created_at": parse_time(raw.get("date")),
            }
        )
    return items


def fetch_arbeitnow(client: httpx.Client) -> list[dict]:
    items = []
    for page in (1, 2, 3):
        response = client.get(
            "https://www.arbeitnow.com/api/job-board-api", params={"page": page}, timeout=30
        )
        response.raise_for_status()
        for raw in response.json().get("data", []):
            url = str(raw.get("url") or "")
            company = (raw.get("company_name") or "").strip()
            title = (raw.get("title") or "").strip()
            if not url.startswith("https://") or not company or not title:
                continue
            description = clean_html(raw.get("description") or "")[:5000]
            if len(description) < 20:
                description = f"{title} at {company}. Open the listing for the full description."
            location = (raw.get("location") or "").strip()
            kinds = " ".join(str(x) for x in (raw.get("job_types") or []))
            tags = " ".join(str(x) for x in (raw.get("tags") or []))
            created = raw.get("created_at")
            posted = (
                datetime.fromtimestamp(created, timezone.utc).replace(tzinfo=None)
                if isinstance(created, (int, float))
                else None
            )
            items.append(
                {
                    "company_name": company,
                    "external_id": str(raw.get("slug") or url)[:100],
                    "title": title[:200],
                    "description": description,
                    "location": location[:120] or None,
                    "country": detect_country(location),
                    "is_remote": bool(raw.get("remote")),
                    "job_type": job_type_for(f"{title} {kinds}"),
                    "experience_level": infer_level(f"{title} {kinds}"),
                    "skills": extract_skills(f"{title}\n{description}\n{tags}", limit=12),
                    "apply_url": url[:1000],
                    "created_at": posted,
                }
            )
        time.sleep(1)
    return items


def sync(client: httpx.Client) -> dict:
    global _last_run
    totals = {"created": 0, "updated": 0, "closed": 0}
    if time.time() - _last_run < MIN_GAP_SECONDS:
        return totals
    _last_run = time.time()

    started = now_utc()
    with SessionLocal() as db:
        for source, fetch in (("remoteok", fetch_remoteok), ("arbeitnow", fetch_arbeitnow)):
            try:
                items = fetch(client)
            except Exception as exc:
                print(f"  {source} import failed: {exc}", flush=True)
                continue
            result = upsert_jobs(db, source, items, started)
            totals["created"] += result["created"]
            totals["updated"] += result["updated"]
            totals["closed"] += close_stale(db, source, started, 3)
    return totals