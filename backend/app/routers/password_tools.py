import hashlib
import hmac
import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Notification, RecoveryCode, User
from app.notifications import now_utc
from app.ratelimit import RateLimiter, client_ip
from app.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["password"])

# No confusing characters (no I, O, 0 or 1). 12 characters give 60 bits of randomness.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_COUNT = 8

change_limit = RateLimiter(5, 900, "Too many wrong passwords. Please wait a few minutes and try again.")
reset_by_account = RateLimiter(5, 900, "Too many tries for this account. Please wait a few minutes and try again.")
reset_by_ip = RateLimiter(30, 900, "Too many tries from this network. Please wait a few minutes and try again.")


def digest_of(code: str) -> str:
    """Codes are stored only as a keyed one-way scramble, never as text."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", code or "").upper()
    key = (os.environ["SECRET_KEY"] + ":recovery").encode()
    return hmac.new(key, cleaned.encode(), hashlib.sha256).hexdigest()


def new_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def count_codes(db: Session, user_id: int, unused_only: bool = False) -> int:
    stmt = select(func.count()).select_from(RecoveryCode).where(RecoveryCode.user_id == user_id)
    if unused_only:
        stmt = stmt.where(RecoveryCode.used_at.is_(None))
    return db.scalar(stmt) or 0


def security_notice(db: Session, user_id: int) -> None:
    db.add(
        Notification(
            user_id=user_id,
            kind="security",
            title="Your password was changed",
            body="If this was not you, reset it from the sign-in page.",
            link="/account",
        )
    )


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RecoveryIn(BaseModel):
    password: str | None = Field(default=None, max_length=128)


class ForgotIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    recovery_code: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/change-password", status_code=204)
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = f"change:{user.id}"
    change_limit.check(key)
    if not user.password_hash or not verify_password(data.current_password, user.password_hash):
        change_limit.add(key)
        raise HTTPException(status_code=400, detail="Your current password is not correct")
    if data.new_password == data.current_password:
        raise HTTPException(status_code=400, detail="Please choose a password that is different from the current one")
    user.password_hash = hash_password(data.new_password)
    security_notice(db, user.id)
    db.commit()
    return Response(status_code=204)


@router.get("/recovery")
def recovery_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"created": count_codes(db, user.id) > 0, "remaining": count_codes(db, user.id, unused_only=True)}


@router.post("/recovery")
def make_recovery_codes(
    data: RecoveryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The first set needs no password. New sets (which replace the old ones) need your current password."""
    if count_codes(db, user.id) > 0:
        key = f"change:{user.id}"
        change_limit.check(key)
        if not data.password or not user.password_hash or not verify_password(data.password, user.password_hash):
            change_limit.add(key)
            raise HTTPException(status_code=400, detail="Enter your current password to make new codes")
        db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    codes = [new_code() for _ in range(CODE_COUNT)]
    for code in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=digest_of(code)))
    db.commit()
    return {"codes": codes}


@router.post("/forgot", status_code=204)
def forgot_password(data: ForgotIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = data.email.strip().lower()
    key = f"{ip}|{email}"
    reset_by_ip.check(ip)
    reset_by_account.check(key)

    user = db.scalar(select(User).where(User.email == email))
    digest = digest_of(data.recovery_code)
    row = None
    if user is not None and user.is_active:
        row = db.scalar(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user.id,
                RecoveryCode.code_hash == digest,
                RecoveryCode.used_at.is_(None),
            )
        )
    if row is None:
        reset_by_ip.add(ip)
        reset_by_account.add(key)
        # The same answer for a wrong email and a wrong code, so nothing is given away.
        raise HTTPException(status_code=400, detail="That email and recovery code do not match")

    row.used_at = now_utc()
    user.password_hash = hash_password(data.new_password)
    security_notice(db, user.id)
    db.commit()
    reset_by_account.clear(key)
    return Response(status_code=204)