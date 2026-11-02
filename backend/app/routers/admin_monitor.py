from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin_audit import log_admin
from app.deps import get_db, require_roles
from app.models import (
    AdminAudit,
    Application,
    Company,
    Job,
    Profile,
    RecruiterProfile,
    Resume,
    SavedSearch,
    Swipe,
    User,
)

router = APIRouter(prefix="/admin", tags=["admin-monitor"])
admin_only = require_roles("admin")


def days_ago(days):
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def count(db, stmt):
    return db.scalar(stmt) or 0


@router.get("/users/{user_id}/detail")
def user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    """Only what an admin needs to run the platform. No profile contents, no resumes."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    out = {
        "kind": user.role,
        "account": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        },
    }

    if user.role == "job_seeker":
        profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
        filled = 0
        if profile:
            filled = sum(1 for v in (profile.headline, profile.location, profile.skills, profile.bio) if v)
        out["summary"] = {
            "profile_completeness_percent": filled * 25,
            "public_profile": bool(profile and profile.is_public),
            "resumes": count(db, select(func.count()).select_from(Resume).where(Resume.user_id == user.id)),
            "applications": count(
                db,
                select(func.count())
                .select_from(Application)
                .where(Application.user_id == user.id, Application.status != "saved"),
            ),
        }

    elif user.role == "recruiter":
        link = db.scalar(select(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
        company = db.get(Company, link.company_id) if link else None
        out["company"] = (
            {
                "name": company.name,
                "company_type": company.company_type,
                "verification_status": company.verification_status,
                "website": company.website,
                "location": company.location,
            }
            if company
            else None
        )
        if company:
            out["summary"] = {
                "team_members": count(
                    db,
                    select(func.count())
                    .select_from(RecruiterProfile)
                    .where(RecruiterProfile.company_id == company.id),
                ),
                "jobs_posted": count(
                    db, select(func.count()).select_from(Job).where(Job.company_id == company.id)
                ),
                "jobs_open": count(
                    db,
                    select(func.count())
                    .select_from(Job)
                    .where(Job.company_id == company.id, Job.is_active.is_(True)),
                ),
                "applications_received": count(
                    db,
                    select(func.count())
                    .select_from(Application)
                    .join(Job, Application.job_id == Job.id)
                    .where(Job.company_id == company.id, Application.status != "saved"),
                ),
            }

    log_admin(db, admin, "viewed_account", user.id)
    db.commit()
    return jsonable_encoder(out)


@router.get("/overview")
def overview(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    def grouped(column):
        return {key: n for key, n in db.execute(select(column, func.count()).group_by(column)).all()}

    out = {
        "users_by_role": grouped(User.role),
        "users_active": count(db, select(func.count()).select_from(User).where(User.is_active.is_(True))),
        "users_disabled": count(db, select(func.count()).select_from(User).where(User.is_active.is_(False))),
        "signups_7d": count(db, select(func.count()).select_from(User).where(User.created_at >= days_ago(7))),
        "signups_30d": count(db, select(func.count()).select_from(User).where(User.created_at >= days_ago(30))),
        "jobs_total": count(db, select(func.count()).select_from(Job)),
        "jobs_active": count(db, select(func.count()).select_from(Job).where(Job.is_active.is_(True))),
        "jobs_posted_on_swipex": count(db, select(func.count()).select_from(Job).where(Job.source == "native")),
        "applications_by_status": grouped(Application.status),
        "swipes": grouped(Swipe.direction),
        "companies_by_verification": grouped(Company.verification_status),
        "saved_searches": count(db, select(func.count()).select_from(SavedSearch)),
        "public_profiles": count(db, select(func.count()).select_from(Profile).where(Profile.is_public.is_(True))),
    }

    out["recent_signups"] = [
        {"id": u.id, "full_name": u.full_name, "role": u.role, "created_at": u.created_at}
        for u in db.scalars(select(User).order_by(User.id.desc()).limit(10))
    ]

    audit = db.execute(
        select(AdminAudit, User).join(User, AdminAudit.admin_id == User.id).order_by(AdminAudit.id.desc()).limit(50)
    ).all()
    target_ids = {a.target_user_id for a, _ in audit if a.target_user_id}
    names = (
        {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_(target_ids)))} if target_ids else {}
    )
    out["activity_log"] = [
        {
            "when": a.created_at,
            "admin": admin_user.full_name,
            "action": a.action,
            "target_id": a.target_user_id,
            "target": names.get(a.target_user_id),
            "detail": a.detail,
        }
        for a, admin_user in audit
    ]
    return jsonable_encoder(out)