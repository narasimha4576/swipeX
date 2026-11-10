import io
import json
import re
import zipfile
from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, select, update

from app.models import (
    Application,
    Company,
    CompanyInvite,
    Education,
    Experience,
    Job,
    Notification,
    PortfolioItem,
    Profile,
    RecruiterProfile,
    Resume,
    SavedSearch,
    Swipe,
)
from app.storage import photo_bytes, resume_bytes
from app.team_tools import owner_user_id

README = """SwipeX - a copy of your data

data.json   Your account, profile, experience, education, portfolio, resume list,
            applications, liked and skipped jobs, saved searches and notifications.
            If you are a recruiter it also holds your company and the jobs you posted.
resumes/    The resume PDF files you uploaded.
photo.jpg   Your profile photo, if you added one.

Your password is never included. It is stored only as a one-way scramble.
Other people's data (for example, applicants to your jobs) is not included.
"""


class DeletionBlocked(Exception):
    pass


def row_dict(obj, skip=()):
    """Every column of a row, except anything that looks like a password."""
    data = {}
    for column in obj.__table__.columns:
        key = column.key
        if key in skip or "password" in key or "hash" in key:
            continue
        data[key] = getattr(obj, key)
    return data


def collect_data(db, user):
    out = {
        "exported_at": datetime.now(timezone.utc),
        "account": row_dict(user, skip=("id",)),
    }

    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    out["profile"] = (
        row_dict(profile, skip=("id", "user_id", "photo_path", "photo_data", "public_slug")) if profile else None
    )

    for key, model in (("experiences", Experience), ("educations", Education), ("portfolio", PortfolioItem)):
        out[key] = [
            row_dict(x, skip=("id", "user_id"))
            for x in db.scalars(select(model).where(model.user_id == user.id).order_by(model.id))
        ]

    out["resumes"] = [
        {"name": r.version_name, "is_default": r.is_default, "uploaded_at": r.created_at}
        for r in db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id))
    ]

    applications = db.execute(
        select(Application, Job, Company)
        .join(Job, Application.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Application.user_id == user.id)
        .order_by(Application.id)
    ).all()
    out["applications"] = [
        {
            "job_title": job.title,
            "company": company.name,
            "status": app_row.status,
            "started_at": app_row.created_at,
            "updated_at": app_row.updated_at,
        }
        for app_row, job, company in applications
    ]

    swipes = db.execute(
        select(Swipe, Job, Company)
        .join(Job, Swipe.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(Swipe.user_id == user.id)
        .order_by(Swipe.id)
    ).all()
    out["swiped_jobs"] = [
        {
            "job_title": job.title,
            "company": company.name,
            "choice": "liked" if swipe.direction == "right" else "skipped",
            "when": swipe.updated_at,
        }
        for swipe, job, company in swipes
    ]

    out["saved_searches"] = [
        {"name": s.name, "filters": s.filters, "created_at": s.created_at}
        for s in db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.id))
    ]
    out["notifications"] = [
        {"title": n.title, "body": n.body, "is_read": n.is_read, "created_at": n.created_at}
        for n in db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id))
    ]

    link = db.scalar(select(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
    if link:
        company = db.get(Company, link.company_id)
        out["company"] = row_dict(company, skip=("id", "trust_data")) if company else None
        out["team_role"] = "owner" if owner_user_id(db, link.company_id) == user.id else "member"
    out["jobs_posted"] = [
        {
            "title": j.title,
            "description": j.description,
            "location": j.location,
            "is_active": j.is_active,
            "applicant_count": j.applicant_count,
            "created_at": j.created_at,
        }
        for j in db.scalars(select(Job).where(Job.posted_by == user.id).order_by(Job.id))
    ]
    return out


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9._ -]", "_", text or "resume").strip()[:60] or "resume"


def build_zip(db, user, upload_dir, photo_dir):
    data = collect_data(db, user)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("data.json", json.dumps(jsonable_encoder(data), indent=2, ensure_ascii=False))
        bundle.writestr("README.txt", README)
        for resume in db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id)):
            content = resume_bytes(resume, upload_dir)
            if content is not None:
                bundle.writestr(f"resumes/{resume.id}-{safe_name(resume.version_name)}.pdf", content)
        profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
        photo = photo_bytes(profile, photo_dir)
        if photo is not None:
            bundle.writestr("photo.jpg", photo)
    return buffer.getvalue()

def delete_account(db, user, upload_dir, photo_dir):
    """Erases the person's data. Companies and job postings stay (closed) so other people keep their history."""
    files = []

    if user.role == "recruiter":
        link = db.scalar(select(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
        if link:
            members = db.scalar(
                select(func.count()).select_from(RecruiterProfile).where(RecruiterProfile.company_id == link.company_id)
            )
            if owner_user_id(db, link.company_id) == user.id:
                if members > 1:
                    raise DeletionBlocked(
                        "You started this company's team. Remove the other team members first, then delete your account."
                    )
                db.execute(update(Job).where(Job.company_id == link.company_id).values(is_active=False))
                db.execute(delete(CompanyInvite).where(CompanyInvite.company_id == link.company_id))
            db.execute(delete(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
        db.execute(update(Job).where(Job.posted_by == user.id).values(posted_by=None))

    db.execute(delete(Application).where(Application.user_id == user.id))  # status history goes with it
    db.execute(delete(Swipe).where(Swipe.user_id == user.id))
    db.execute(delete(SavedSearch).where(SavedSearch.user_id == user.id))
    db.execute(delete(Notification).where(Notification.user_id == user.id))
    db.execute(delete(Education).where(Education.user_id == user.id))
    db.execute(delete(Experience).where(Experience.user_id == user.id))
    db.execute(delete(PortfolioItem).where(PortfolioItem.user_id == user.id))

    for name in db.scalars(select(Resume.file_path).where(Resume.user_id == user.id)):
        files.append(upload_dir / name)
    db.execute(delete(Resume).where(Resume.user_id == user.id))

    photo = db.scalar(select(Profile.photo_path).where(Profile.user_id == user.id))
    if photo:
        files.append(photo_dir / photo)
    db.execute(delete(Profile).where(Profile.user_id == user.id))

    user_id = user.id
    db.expunge(user)
    from app.models import User

    db.execute(delete(User).where(User.id == user_id))
    db.commit()

    for path in files:  # files go only after the database change succeeded
        path.unlink(missing_ok=True)