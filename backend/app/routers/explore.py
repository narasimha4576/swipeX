import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import news
from app.ai import AIUnavailable, is_configured
from app.company_ai import build_context, summarize
from app.deps import get_current_user, get_db
from app.models import Company, Job, User
from app.schemas import (
    CompanyBrief,
    CompanyOut,
    CompanyOverview,
    JobBrief,
    NewsItem,
    PublicMatch,
    SearchOut,
    SummaryOut,
    TrustFacts,
)
from app.trust import domain, wikidata
from app.trust.service import build_trust_card, enrich_company, is_fresh

router = APIRouter(prefix="/explore", tags=["explore"])
open_count = func.count(Job.id).filter(Job.is_active.is_(True))


def to_brief(company: Company, open_jobs: int) -> CompanyBrief:
    return CompanyBrief(
        id=company.id,
        name=company.name,
        company_type=company.company_type,
        location=company.location,
        verification_status=company.verification_status,
        open_jobs=open_jobs,
    )


def jobs_for(db: Session, company_id: int) -> list[JobBrief]:
    rows = db.scalars(
        select(Job)
        .where(Job.company_id == company_id, Job.is_active.is_(True))
        .order_by(Job.created_at.desc())
        .limit(10)
    ).all()
    return [
        JobBrief(
            id=j.id,
            title=j.title,
            location=j.location,
            job_type=j.job_type,
            is_remote=j.is_remote,
            created_at=j.created_at,
        )
        for j in rows
    ]


def visible_company(db: Session, user: User, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None or (company.verification_status == "rejected" and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def public_facts(qid: str) -> dict:
    if not re.fullmatch(r"Q\d{1,12}", qid):
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        with httpx.Client(headers=domain.HEADERS, follow_redirects=True) as client:
            return wikidata.fetch_facts(qid, client)
    except Exception:
        raise HTTPException(
            status_code=502, detail="Could not reach the public records service. Try again later."
        )


def facts_model(facts: dict) -> TrustFacts:
    return TrustFacts(
        founded_year=facts.get("founded_year"),
        employees=facts.get("employees"),
        headquarters=facts.get("headquarters"),
        website=facts.get("website"),
        wikipedia_url=facts.get("wikipedia_url"),
        wikidata_url=facts.get("wikidata_url"),
        description=facts.get("description"),
    )


def run_summary(key: str, name: str, facts: dict, headlines: list[dict], job_titles: list[str]):
    try:
        result = summarize(key, build_context(name, facts, headlines, job_titles))
    except AIUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return SummaryOut(**result)


@router.get("/featured", response_model=list[CompanyBrief])
def featured(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Company, open_count)
        .outerjoin(Job, Job.company_id == Company.id)
        .where(Company.verification_status == "verified")
        .group_by(Company.id)
        .order_by(open_count.desc(), Company.name)
        .limit(12)
    ).all()
    return [to_brief(company, count) for company, count in rows]


@router.get("/search", response_model=SearchOut)
def search(
    q: str = Query(..., min_length=2, max_length=80),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    text = q.strip()
    rows = db.execute(
        select(Company, open_count)
        .outerjoin(Job, Job.company_id == Company.id)
        .where(Company.name.ilike(f"%{text}%"), Company.verification_status != "rejected")
        .group_by(Company.id)
        .order_by(Company.verification_status != "verified", Company.name)
        .limit(10)
    ).all()

    try:
        with httpx.Client(headers=domain.HEADERS, follow_redirects=True) as client:
            found = wikidata.search_companies(text, client)
    except Exception:
        found = []
    known = {company.name.lower() for company, _ in rows}
    public = [PublicMatch(**item) for item in found if item["label"].lower() not in known]

    return SearchOut(companies=[to_brief(c, n) for c, n in rows], public=public)


@router.get("/company/{company_id}", response_model=CompanyOverview)
def company_overview(
    company_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = visible_company(db, user, company_id)
    if not is_fresh(company):
        enrich_company(db, company)
    card = build_trust_card(db, company)
    return CompanyOverview(
        name=company.name,
        kind="swipex",
        company=CompanyOut.model_validate(company),
        swipex_company_id=company.id,
        description=card.facts.description,
        facts=card.facts,
        trust_level=card.level,
        jobs=jobs_for(db, company.id),
        news=[NewsItem(**item) for item in news.recent_news(company.name)],
        ai_available=is_configured(),
    )


@router.get("/public/{qid}", response_model=CompanyOverview)
def public_overview(
    qid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    facts = public_facts(qid)
    label = facts.get("label") or qid
    match = db.scalar(
        select(Company).where(
            func.lower(Company.name) == label.lower(),
            Company.verification_status != "rejected",
        )
    )
    return CompanyOverview(
        name=label,
        kind="public",
        swipex_company_id=match.id if match else None,
        description=facts.get("description"),
        facts=facts_model(facts),
        jobs=jobs_for(db, match.id) if match else [],
        news=[NewsItem(**item) for item in news.recent_news(label)],
        ai_available=is_configured(),
    )


@router.post("/company/{company_id}/summary", response_model=SummaryOut)
def company_summary(
    company_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = visible_company(db, user, company_id)
    if not is_fresh(company):
        enrich_company(db, company)
    card = build_trust_card(db, company)
    jobs = jobs_for(db, company.id)
    return run_summary(
        f"swipex:{company.id}",
        company.name,
        card.facts.model_dump(),
        news.recent_news(company.name),
        [j.title for j in jobs],
    )


@router.post("/public/{qid}/summary", response_model=SummaryOut)
def public_summary(
    qid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    facts = public_facts(qid)
    label = facts.get("label") or qid
    match = db.scalar(
        select(Company).where(
            func.lower(Company.name) == label.lower(),
            Company.verification_status != "rejected",
        )
    )
    jobs = jobs_for(db, match.id) if match else []
    return run_summary(
        f"public:{qid}", label, facts, news.recent_news(label), [j.title for j in jobs]
    )