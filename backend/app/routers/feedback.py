import re
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin_audit import log_admin
from app.deps import get_db, require_roles
from app.errors import clean_path
from app.models import Feedback, Notification, User
from app.ratelimit import RateLimiter, client_ip
from app.security import decode_access_token

router = APIRouter(prefix="/feedback", tags=["feedback"])
admin_router = APIRouter(prefix="/admin/feedback", tags=["admin-feedback"])
admin_only = require_roles("admin")

oauth2_optional = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
user_limit = RateLimiter(10, 3600, "You have sent a lot of feedback. Please try again in a while.")
ip_limit = RateLimiter(5, 3600, "Too many reports from this network. Please try again in a while.")

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REF = re.compile(r"^[0-9A-Fa-f]{8}$")


def optional_user(
    token: str | None = Depends(oauth2_optional), db: Session = Depends(get_db)
) -> User | None:
    """The person who is signed in, or None. Feedback also works when you cannot sign in."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if payload.get("scope"):
            return None
        user = db.get(User, int(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    return user if user is not None and user.is_active else None


class FeedbackIn(BaseModel):
    kind: Literal["feedback", "problem"]
    message: str = Field(min_length=5, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    page: str | None = Field(default=None, max_length=200)
    error_ref: str | None = Field(default=None, max_length=16)
    contact_ok: bool = False
    contact_email: str | None = Field(default=None, max_length=200)

    @field_validator("message", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("contact_email")
    @classmethod
    def check_email(cls, value):
        value = (value or "").strip()
        if not value:
            return None
        if not EMAIL.match(value):
            raise ValueError("Please enter a valid email address")
        return value

    @field_validator("error_ref")
    @classmethod
    def check_ref(cls, value):
        value = (value or "").strip()
        return value.upper() if REF.match(value) else None


def notify_admins(db: Session, title: str, message: str) -> None:
    admin_ids = db.scalars(select(User.id).where(User.role == "admin", User.is_active.is_(True))).all()
    for admin_id in admin_ids:
        db.add(
            Notification(
                user_id=admin_id,
                kind="feedback",
                title=title,
                body=message[:200],
                link="/admin/feedback",
            )
        )


@router.post("", status_code=201)
def send_feedback(
    data: FeedbackIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
):
    if user is not None:
        user_limit.hit(f"feedback:{user.id}")
    else:
        ip_limit.hit(client_ip(request))

    item = Feedback(
        kind=data.kind,
        message=data.message,
        rating=data.rating if data.kind == "feedback" else None,
        page=clean_path(data.page) if data.page else None,
        browser=(request.headers.get("user-agent") or "")[:160] or None,
        error_ref=data.error_ref if data.kind == "problem" else None,
        user_id=user.id if user else None,
        # Signed-in people choose with the tick box. Signed-out people allow contact by typing an email.
        contact_ok=data.contact_ok if user else bool(data.contact_email),
        contact_email=None if user else data.contact_email,
    )
    db.add(item)
    notify_admins(db, "New problem report" if data.kind == "problem" else "New feedback", data.message)
    db.commit()
    return {"id": item.id}


# ---------------- admin ----------------


def serialize(item: Feedback, user: User | None) -> dict:
    who = None
    if item.contact_ok:
        if user is not None:
            who = {"name": user.full_name, "email": user.email}
        elif item.contact_email:
            who = {"name": None, "email": item.contact_email}
    return {
        "id": item.id,
        "kind": item.kind,
        "message": item.message,
        "rating": item.rating,
        "page": item.page,
        "browser": item.browser,
        "error_ref": item.error_ref,
        "status": item.status,
        "admin_note": item.admin_note,
        "created_at": item.created_at,
        "who": who,
        "signed_in": item.user_id is not None,
    }


class FeedbackUpdate(BaseModel):
    status: Literal["new", "reviewing", "done"] | None = None
    note: str | None = Field(default=None, max_length=1000)


@admin_router.get("")
def list_feedback(
    kind: Literal["feedback", "problem"] | None = None,
    status: Literal["new", "reviewing", "done"] | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    stmt = (
        select(Feedback, User)
        .outerjoin(User, Feedback.user_id == User.id)
        .order_by(Feedback.id.desc())
        .limit(200)
    )
    if kind:
        stmt = stmt.where(Feedback.kind == kind)
    if status:
        stmt = stmt.where(Feedback.status == status)
    rows = db.execute(stmt).all()
    counts = {key: n for key, n in db.execute(select(Feedback.status, func.count()).group_by(Feedback.status)).all()}
    kinds = {key: n for key, n in db.execute(select(Feedback.kind, func.count()).group_by(Feedback.kind)).all()}
    return jsonable_encoder(
        {"items": [serialize(item, user) for item, user in rows], "counts": counts, "kinds": kinds}
    )


@admin_router.patch("/{feedback_id}")
def update_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    item = db.get(Feedback, feedback_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    if data.status is not None:
        item.status = data.status
    if data.note is not None:
        item.admin_note = data.note.strip() or None
    db.commit()
    user = db.get(User, item.user_id) if item.user_id else None
    return jsonable_encoder(serialize(item, user))


@admin_router.delete("/{feedback_id}", status_code=204)
def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    item = db.get(Feedback, feedback_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    log_admin(db, admin, "deleted_feedback", None, f"#{feedback_id}")
    db.commit()
    return Response(status_code=204)