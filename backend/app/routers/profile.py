from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Profile, User
from app.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


def get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id, skills=[])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/me", response_model=ProfileOut)
def read_my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    return get_or_create_profile(db, user)


@router.put("/me", response_model=ProfileOut)
def update_my_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("job_seeker")),
):
    profile = get_or_create_profile(db, user)
    profile.headline = data.headline
    profile.location = data.location
    profile.experience_years = data.experience_years
    profile.skills = data.skills
    profile.bio = data.bio
    db.commit()
    db.refresh(profile)
    return profile