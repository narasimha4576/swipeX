import re
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Company, CompanyInvite, RecruiterProfile, User
from app.team_tools import owner_user_id

router = APIRouter(prefix="/recruiter/team", tags=["team"])
recruiter_only = require_roles("recruiter")

MAX_JOIN_TRIES_PER_HOUR = 10
_attempts = {}


class MemberOut(BaseModel):
    user_id: int
    full_name: str
    email: str
    is_owner: bool
    is_me: bool


class TeamOut(BaseModel):
    company_name: str | None = None
    is_owner: bool = False
    invite_code: str | None = None
    members: list[MemberOut] = []


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=20)


def new_code(db):
    while True:
        code = secrets.token_hex(4).upper()
        if db.scalar(select(CompanyInvite.id).where(CompanyInvite.code == code)) is None:
            return code


def build(db, user):
    profile = db.scalar(select(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
    if profile is None:
        return TeamOut()
    company = db.get(Company, profile.company_id)
    owner_id = owner_user_id(db, company.id)
    owner = owner_id == user.id

    code = None
    if owner:
        invite = db.scalar(select(CompanyInvite).where(CompanyInvite.company_id == company.id))
        if invite is None:
            invite = CompanyInvite(company_id=company.id, code=new_code(db))
            db.add(invite)
            db.commit()
        code = invite.code

    people = db.scalars(
        select(User)
        .join(RecruiterProfile, RecruiterProfile.user_id == User.id)
        .where(RecruiterProfile.company_id == company.id)
        .order_by(RecruiterProfile.id)
    ).all()
    return TeamOut(
        company_name=company.name,
        is_owner=owner,
        invite_code=code,
        members=[
            MemberOut(
                user_id=p.id,
                full_name=p.full_name,
                email=p.email,
                is_owner=p.id == owner_id,
                is_me=p.id == user.id,
            )
            for p in people
        ],
    )


def my_profile_or_400(db, user):
    profile = db.scalar(select(RecruiterProfile).where(RecruiterProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=400, detail="You are not part of a company yet")
    return profile


@router.get("", response_model=TeamOut)
def read_team(db: Session = Depends(get_db), user: User = Depends(recruiter_only)):
    return build(db, user)


@router.post("/regenerate", response_model=TeamOut)
def regenerate(db: Session = Depends(get_db), user: User = Depends(recruiter_only)):
    profile = my_profile_or_400(db, user)
    if owner_user_id(db, profile.company_id) != user.id:
        raise HTTPException(status_code=403, detail="Only the company owner can do this")
    invite = db.scalar(select(CompanyInvite).where(CompanyInvite.company_id == profile.company_id))
    if invite is None:
        invite = CompanyInvite(company_id=profile.company_id, code=new_code(db))
        db.add(invite)
    else:
        invite.code = new_code(db)
    db.commit()
    return build(db, user)


@router.post("/join", response_model=TeamOut)
def join_team(data: JoinIn, db: Session = Depends(get_db), user: User = Depends(recruiter_only)):
    now = time.time()
    tries = [t for t in _attempts.get(user.id, []) if now - t < 3600]
    if len(tries) >= MAX_JOIN_TRIES_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many tries. Please wait an hour and try again.")
    tries.append(now)
    _attempts[user.id] = tries

    if db.scalar(select(RecruiterProfile.id).where(RecruiterProfile.user_id == user.id)) is not None:
        raise HTTPException(status_code=400, detail="You already belong to a company")
    code = re.sub(r"[^A-Za-z0-9]", "", data.code).upper()
    invite = db.scalar(select(CompanyInvite).where(CompanyInvite.code == code))
    if invite is None:
        raise HTTPException(status_code=400, detail="That invite code is not valid")
    db.add(RecruiterProfile(user_id=user.id, company_id=invite.company_id))
    db.commit()
    return build(db, user)


@router.post("/leave", response_model=TeamOut)
def leave_team(db: Session = Depends(get_db), user: User = Depends(recruiter_only)):
    profile = my_profile_or_400(db, user)
    if owner_user_id(db, profile.company_id) == user.id:
        raise HTTPException(
            status_code=400,
            detail="The owner cannot leave. Remove the other members first, or keep running the company.",
        )
    db.delete(profile)
    db.commit()
    return TeamOut()


@router.delete("/members/{member_id}", response_model=TeamOut)
def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(recruiter_only),
):
    profile = my_profile_or_400(db, user)
    if owner_user_id(db, profile.company_id) != user.id:
        raise HTTPException(status_code=403, detail="Only the company owner can remove members")
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    target = db.scalar(
        select(RecruiterProfile).where(
            RecruiterProfile.user_id == member_id,
            RecruiterProfile.company_id == profile.company_id,
        )
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(target)
    db.commit()
    return build(db, user)