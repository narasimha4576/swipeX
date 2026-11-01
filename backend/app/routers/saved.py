from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Job, SavedSearch, User

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])
seeker_only = require_roles("job_seeker")
MAX_SEARCHES = 10


class SearchFilters(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=80)
    company_type: str | None = Field(default=None, max_length=20)
    job_type: str | None = Field(default=None, max_length=20)
    experience_level: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=60)
    remote: bool | None = None
    fresher_friendly: bool = False
    low_competition: bool = False
    min_salary: float | None = Field(default=None, ge=0)
    max_age_days: int | None = Field(default=None, ge=1, le=365)
    verified_only: bool = False


class SavedSearchIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    filters: SearchFilters


class SavedSearchOut(BaseModel):
    id: int
    name: str
    filters: dict
    created_at: datetime

    model_config = {"from_attributes": True}


def label_for(f):
    parts = []
    for key in ("q", "skill", "location", "country"):
        if f.get(key):
            parts.append(str(f[key]))
    for key, text in (
        ("remote", "Remote"),
        ("fresher_friendly", "Fresher-friendly"),
        ("low_competition", "Low competition"),
    ):
        if f.get(key):
            parts.append(text)
    for key in ("job_type", "experience_level", "company_type"):
        if f.get(key):
            parts.append(str(f[key]).replace("_", " ").title())
    return (", ".join(parts) or "My search")[:120]


@router.get("", response_model=list[SavedSearchOut])
def list_searches(
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    return db.scalars(
        select(SavedSearch)
        .where(SavedSearch.user_id == user.id)
        .order_by(SavedSearch.created_at.desc(), SavedSearch.id.desc())
    ).all()


@router.post("", response_model=SavedSearchOut)
def create_search(
    data: SavedSearchIn,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    filters = data.filters.model_dump(exclude_none=True)
    if not any(value for key, value in filters.items() if key != "verified_only"):
        raise HTTPException(status_code=400, detail="Type a search or choose a filter before saving")
    owned = db.scalar(
        select(func.count()).select_from(SavedSearch).where(SavedSearch.user_id == user.id)
    )
    if owned >= MAX_SEARCHES:
        raise HTTPException(
            status_code=400, detail=f"You can keep up to {MAX_SEARCHES} saved searches. Delete one first."
        )
    search = SavedSearch(
        user_id=user.id,
        name=(data.name or "").strip() or label_for(filters),
        filters=filters,
        last_job_id=db.scalar(select(func.max(Job.id))) or 0,
    )
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.delete("/{search_id}")
def delete_search(
    search_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    search = db.get(SavedSearch, search_id)
    if search is None or search.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved search not found")
    db.delete(search)
    db.commit()
    return {"ok": True}