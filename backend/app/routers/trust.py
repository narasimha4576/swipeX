from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Company, RecruiterProfile, User
from app.schemas import TrustCardOut
from app.trust.service import build_trust_card, enrich_company, is_fresh

router = APIRouter(tags=["trust"])


@router.get("/companies/{company_id}/trust", response_model=TrustCardOut)
def company_trust(
    company_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    allowed = company.verification_status != "rejected" or user.role == "admin"
    if not allowed and user.role == "recruiter":
        allowed = (
            db.scalar(
                select(RecruiterProfile.id).where(
                    RecruiterProfile.user_id == user.id,
                    RecruiterProfile.company_id == company.id,
                )
            )
            is not None
        )
    if not allowed:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_fresh(company):
        enrich_company(db, company)
    return build_trust_card(db, company)