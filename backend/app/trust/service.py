import re
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationEvent, Company, Job
from app.schemas import CompanyOut, HiringStats, TrustCardOut, TrustFacts, TrustSignal
from app.trust import domain, wikidata

RESPONDED = ("shortlisted", "interview", "rejected")
REFRESH_AFTER = timedelta(days=7)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clean_name(name: str) -> str:
    name = re.sub(r"\s*\(greenhouse\)\s*$", "", name, flags=re.I)
    name = re.sub(r",?\s+(inc|ltd|llc|corp|corporation|limited)\.?$", "", name, flags=re.I)
    return name.strip()


def is_fresh(company: Company) -> bool:
    return bool(
        company.trust_data
        and company.enriched_at
        and now_utc() - company.enriched_at < REFRESH_AFTER
    )


def enrich_company(db: Session, company: Company) -> dict:
    data: dict = {"checked_at": now_utc().isoformat(timespec="seconds"), "wikidata": None}
    with httpx.Client(headers=domain.HEADERS, follow_redirects=True) as client:
        try:
            entity = wikidata.find_entity(clean_name(company.name), client)
            if entity:
                data["wikidata"] = wikidata.fetch_facts(entity["id"], client)
        except Exception as exc:
            data["wikidata_error"] = str(exc)[:200]

        website = company.website or (data["wikidata"] or {}).get("website")
        if website:
            host = domain.hostname(website)
            data["website"] = {"url": website, "host": host, **domain.check_website(website, client)}
            registered = domain.domain_registered_on(host, client) if host else None
            if registered:
                age = (now_utc() - registered).days / 365.25
                data["domain"] = {
                    "registered_on": registered.date().isoformat(),
                    "age_years": round(age, 1),
                }

    company.trust_data = data
    company.enriched_at = now_utc()
    db.commit()
    return data


def hiring_stats(db: Session, company_id: int) -> HiringStats | None:
    native_jobs = db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.company_id == company_id, Job.source == "native")
    )
    if not native_jobs:
        return None

    open_jobs = db.scalar(
        select(func.count())
        .select_from(Job)
        .where(Job.company_id == company_id, Job.source == "native", Job.is_active.is_(True))
    )
    base = (
        select(func.count())
        .select_from(Application)
        .join(Job, Job.id == Application.job_id)
        .where(Job.company_id == company_id, Job.source == "native")
    )
    applications = db.scalar(base.where(Application.status != "saved"))
    responded = db.scalar(base.where(Application.status.in_(RESPONDED)))
    rate = round(responded / applications, 2) if applications else None

    rows = db.execute(
        select(ApplicationEvent.application_id, ApplicationEvent.status, ApplicationEvent.created_at)
        .join(Application, Application.id == ApplicationEvent.application_id)
        .join(Job, Job.id == Application.job_id)
        .where(Job.company_id == company_id, Job.source == "native")
        .order_by(ApplicationEvent.application_id, ApplicationEvent.created_at, ApplicationEvent.id)
    ).all()
    applied_at: dict[int, datetime] = {}
    done: set[int] = set()
    delays: list[float] = []
    for application_id, status, created in rows:
        if status == "applied" and application_id not in applied_at:
            applied_at[application_id] = created
        elif status in RESPONDED and application_id in applied_at and application_id not in done:
            delays.append((created - applied_at[application_id]).total_seconds() / 86400)
            done.add(application_id)
    average = round(sum(delays) / len(delays), 1) if delays else None

    return HiringStats(
        jobs_posted=native_jobs,
        open_jobs=open_jobs,
        applications=applications,
        responded=responded,
        response_rate=rate,
        avg_response_days=average,
    )


def build_trust_card(db: Session, company: Company) -> TrustCardOut:
    data = company.trust_data or {}
    wiki = data.get("wikidata") or {}
    web = data.get("website") or {}
    dom = data.get("domain") or {}
    hiring = hiring_stats(db, company.id)

    verified = company.verification_status == "verified"
    official = company.source != "native"

    if hiring is None:
        hiring_ok, hiring_known, hiring_detail = False, False, "Not applicable"
    elif hiring.applications < 3:
        hiring_ok, hiring_known = False, False
        hiring_detail = f"Not enough applications yet ({hiring.applications} so far, needs 3)"
    else:
        percent = round((hiring.response_rate or 0) * 100)
        hiring_ok = (hiring.response_rate or 0) >= 0.5
        hiring_known = True
        hiring_detail = f"{percent}% of applicants received a response"
        if hiring.avg_response_days is not None:
            hiring_detail += f", on average after {hiring.avg_response_days} days"

    age = dom.get("age_years")
    signals = [
        TrustSignal(
            key="verified",
            label="Verified by SwipeX",
            ok=verified,
            detail=(
                "Curated from the company's own job board"
                if verified and official
                else "Reviewed and approved by a SwipeX admin"
                if verified
                else "Not verified yet"
            ),
        ),
        TrustSignal(
            key="official_board",
            label="Jobs come from the company's own job board",
            ok=official,
            applicable=official,
            detail="Listings are published by the company itself",
        ),
        TrustSignal(
            key="website",
            label="Official website works over HTTPS",
            ok=bool(web.get("reachable") and web.get("https")),
            known=bool(web),
            detail=web.get("host") if web else "No website found",
        ),
        TrustSignal(
            key="domain_age",
            label="Website domain is 2 or more years old",
            ok=age is not None and age >= 2,
            known=age is not None,
            detail=f"Registered {dom['registered_on']}" if dom.get("registered_on") else "Could not be checked",
        ),
        TrustSignal(
            key="public_record",
            label="Listed in public records (Wikidata)",
            ok=bool(wiki),
            detail=(wiki.get("description") or wiki.get("label")) if wiki else "No matching record found",
        ),
        TrustSignal(
            key="hiring",
            label="Responds to applicants on SwipeX",
            ok=hiring_ok,
            known=hiring_known,
            applicable=hiring is not None,
            detail=hiring_detail,
        ),
    ]

    applicable = [s for s in signals if s.applicable]
    ratio = sum(1 for s in applicable if s.ok) / len(applicable)
    level = "strong" if ratio >= 0.8 else "good" if ratio >= 0.5 else "limited"

    facts = TrustFacts(
        founded_year=wiki.get("founded_year") or company.founded_year,
        employees=wiki.get("employees"),
        headquarters=wiki.get("headquarters") or company.location,
        website=web.get("url") or company.website,
        wikipedia_url=wiki.get("wikipedia_url"),
        wikidata_url=wiki.get("wikidata_url"),
        description=wiki.get("description"),
    )
    return TrustCardOut(
        company=CompanyOut.model_validate(company),
        level=level,
        signals=signals,
        facts=facts,
        hiring=hiring,
        source=company.source,
        checked_at=data.get("checked_at"),
    )