from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Company, Job, RecruiterProfile, User
from app.routers.recruiter import get_my_company
from app.schemas import (
    AdminCompanyOut,
    CompanyOut,
    DecisionIn,
    VerificationRequest,
    VerificationStatusOut,
)

recruiter_router = APIRouter(
    prefix="/recruiter/company/verification", tags=["verification"]
)
admin_router = APIRouter(prefix="/admin/companies", tags=["verification"])

recruiter_only = require_roles("recruiter")
admin_only = require_roles("admin")


# ---------- Recruiter side ----------


@recruiter_router.get("", response_model=VerificationStatusOut)
def my_verification(
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    company = get_my_company(db, user)
    if company is None:
        raise HTTPException(status_code=404, detail="Create your company profile first")
    return VerificationStatusOut(
        status=company.verification_status, note=company.verification_note
    )


@recruiter_router.post("", response_model=VerificationStatusOut)
def request_verification(
    data: VerificationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    company = get_my_company(db, user)
    if company is None:
        raise HTTPException(status_code=404, detail="Create your company profile first")
    if company.verification_status == "verified":
        raise HTTPException(status_code=400, detail="Your company is already verified")
    if company.verification_status == "pending":
        raise HTTPException(status_code=400, detail="Your request is already waiting for review")

    company.verification_status = "pending"
    company.verification_note = data.note.strip()
    company.verified_at = None
    db.commit()
    return VerificationStatusOut(
        status=company.verification_status, note=company.verification_note
    )


# ---------- Admin side ----------


def to_admin_out(db: Session, company: Company, owner_email: str | None) -> AdminCompanyOut:
    jobs_count = db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == company.id)
    )
    return AdminCompanyOut(
        **CompanyOut.model_validate(company).model_dump(),
        verification_note=company.verification_note,
        verified_at=company.verified_at,
        source=company.source,
        owner_email=owner_email,
        jobs_count=jobs_count,
    )


@admin_router.get("", response_model=list[AdminCompanyOut])
def list_companies(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    stmt = (
        select(Company, User.email)
        .outerjoin(RecruiterProfile, RecruiterProfile.company_id == Company.id)
        .outerjoin(User, User.id == RecruiterProfile.user_id)
        .order_by(Company.id.desc())
    )
    if status:
        stmt = stmt.where(Company.verification_status == status)
    rows = db.execute(stmt).all()
    return [to_admin_out(db, company, email) for company, email in rows]


@admin_router.post("/{company_id}/decision", response_model=AdminCompanyOut)
def decide(
    company_id: int,
    data: DecisionIn,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    note = (data.note or "").strip()
    if data.decision == "rejected" and not note:
        raise HTTPException(status_code=400, detail="Give a reason when rejecting")

    company.verification_status = data.decision
    company.verified_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        if data.decision == "verified"
        else None
    )
    if note:
        company.verification_note = note
    db.commit()
    db.refresh(company)

    owner_email = db.scalar(
        select(User.email)
        .join(RecruiterProfile, RecruiterProfile.user_id == User.id)
        .where(RecruiterProfile.company_id == company.id)
    )
    return to_admin_out(db, company, owner_email)