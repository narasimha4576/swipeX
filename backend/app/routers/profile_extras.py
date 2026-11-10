import io
import re
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import Education, Experience, PortfolioItem, Profile, User
from app.routers.resumes import UPLOAD_DIR
from app.storage import photo_bytes
from app.schemas import ExperienceOut, PortfolioOut

router = APIRouter(prefix="/profile", tags=["profile-extras"])
public_router = APIRouter(tags=["public"])
seeker_only = require_roles("job_seeker")

PHOTO_DIR = UPLOAD_DIR / "photos"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)
MAX_PHOTO_BYTES = 3 * 1024 * 1024
MAX_EDUCATION = 10
PHOTO_NAME = re.compile(r"^u\d+-[0-9a-f]{16}\.jpg$")
Image.MAX_IMAGE_PIXELS = 30_000_000


# ---------- helpers ----------


def ensure_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id, skills=[])
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def make_slug(db: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:30] or "member"
    while True:
        slug = f"{base}-{secrets.token_hex(4)}"
        if db.scalar(select(Profile.id).where(Profile.public_slug == slug)) is None:
            return slug


class ExtrasOut(BaseModel):
    photo_url: str | None = None
    is_public: bool = False
    slug: str | None = None


class PublicIn(BaseModel):
    enabled: bool


def extras_out(profile: Profile) -> ExtrasOut:
    return ExtrasOut(
        photo_url=f"/photos/{profile.photo_path}" if profile.photo_path else None,
        is_public=bool(profile.is_public),
        slug=profile.public_slug if profile.is_public else None,
    )


# ---------- photo and sharing ----------


@router.get("/extras", response_model=ExtrasOut)
def read_extras(db: Session = Depends(get_db), user: User = Depends(seeker_only)):
    return extras_out(ensure_profile(db, user))


@router.post("/photo", response_model=ExtrasOut)
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    raw = await file.read(MAX_PHOTO_BYTES + 1)
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="The photo must be under 3 MB")
    try:
        Image.open(io.BytesIO(raw)).verify()
        image = Image.open(io.BytesIO(raw))
        if image.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError("format")
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="That file is not a valid JPG, PNG or WebP image")

    width, height = image.size
    side = min(width, height)
    left, top = (width - side) // 2, (height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize(
        (320, 320), Image.Resampling.LANCZOS
    )
    name = f"u{user.id}-{secrets.token_hex(8)}.jpg"
    jpeg = io.BytesIO()
    image.save(jpeg, "JPEG", quality=85, optimize=True)

    profile = ensure_profile(db, user)
    old = profile.photo_path
    profile.photo_path = name
    profile.photo_data = jpeg.getvalue()
    db.commit()
    if old and PHOTO_NAME.match(old):
        (PHOTO_DIR / old).unlink(missing_ok=True)
    return extras_out(profile)


@router.delete("/photo", response_model=ExtrasOut)
def delete_photo(db: Session = Depends(get_db), user: User = Depends(seeker_only)):
    profile = ensure_profile(db, user)
    old = profile.photo_path
    profile.photo_path = None
    profile.photo_data = None
    db.commit()
    if old and PHOTO_NAME.match(old):
        (PHOTO_DIR / old).unlink(missing_ok=True)
    return extras_out(profile)


@router.put("/public", response_model=ExtrasOut)
def set_public(data: PublicIn, db: Session = Depends(get_db), user: User = Depends(seeker_only)):
    profile = ensure_profile(db, user)
    profile.is_public = data.enabled
    if data.enabled and not profile.public_slug:
        profile.public_slug = make_slug(db, user.full_name)
    db.commit()
    return extras_out(profile)


@router.post("/public/regenerate", response_model=ExtrasOut)
def new_public_link(db: Session = Depends(get_db), user: User = Depends(seeker_only)):
    profile = ensure_profile(db, user)
    profile.public_slug = make_slug(db, user.full_name)
    db.commit()
    return extras_out(profile)


# ---------- education ----------


class EducationCreate(BaseModel):
    school: str = Field(min_length=2, max_length=200)
    degree: str = Field(min_length=2, max_length=120)
    field_of_study: str | None = Field(default=None, max_length=120)
    start_year: int = Field(ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100)
    grade: str | None = Field(default=None, max_length=40)

    @field_validator("school", "degree", "field_of_study", "grade", mode="before")
    @classmethod
    def clean(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def years_in_order(self):
        if self.end_year is not None and self.end_year < self.start_year:
            raise ValueError("End year cannot be before the start year")
        return self


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school: str
    degree: str
    field_of_study: str | None
    start_year: int
    end_year: int | None
    grade: str | None


@router.get("/educations", response_model=list[EducationOut])
def list_educations(db: Session = Depends(get_db), user: User = Depends(seeker_only)):
    return db.scalars(
        select(Education)
        .where(Education.user_id == user.id)
        .order_by(Education.start_year.desc(), Education.id.desc())
    ).all()


@router.post("/educations", response_model=EducationOut, status_code=status.HTTP_201_CREATED)
def add_education(
    data: EducationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    owned = db.scalar(select(func.count()).select_from(Education).where(Education.user_id == user.id))
    if owned >= MAX_EDUCATION:
        raise HTTPException(status_code=400, detail=f"You can add up to {MAX_EDUCATION} education entries")
    item = Education(user_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/educations/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(seeker_only),
):
    item = db.get(Education, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Education entry not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- public pages (no login) ----------


@public_router.get("/photos/{name}")
def serve_photo(name: str, db: Session = Depends(get_db)):
    if not PHOTO_NAME.match(name):
        raise HTTPException(status_code=404, detail="Not found")
    profile = db.scalar(select(Profile).where(Profile.photo_path == name))
    data = photo_bytes(profile, PHOTO_DIR)
    if data is None:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

class PublicProfileOut(BaseModel):
    full_name: str
    headline: str | None
    location: str | None
    experience_years: float
    skills: list[str]
    bio: str | None
    photo_url: str | None
    experiences: list[ExperienceOut]
    educations: list[EducationOut]
    portfolio: list[PortfolioOut]


@public_router.get("/public/profiles/{slug}", response_model=PublicProfileOut)
def public_profile(slug: str, db: Session = Depends(get_db)):
    profile = db.scalar(
        select(Profile).where(Profile.public_slug == slug, Profile.is_public.is_(True))
    )
    user = db.get(User, profile.user_id) if profile else None
    if profile is None or user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="This profile is not available")
    return PublicProfileOut(
        full_name=user.full_name,
        headline=profile.headline,
        location=profile.location,
        experience_years=profile.experience_years or 0,
        skills=profile.skills or [],
        bio=profile.bio,
        photo_url=f"/photos/{profile.photo_path}" if profile.photo_path else None,
        experiences=db.scalars(
            select(Experience)
            .where(Experience.user_id == user.id)
            .order_by(Experience.start_year.desc(), Experience.id.desc())
        ).all(),
        educations=db.scalars(
            select(Education)
            .where(Education.user_id == user.id)
            .order_by(Education.start_year.desc(), Education.id.desc())
        ).all(),
        portfolio=db.scalars(
            select(PortfolioItem).where(PortfolioItem.user_id == user.id).order_by(PortfolioItem.id.desc())
        ).all(),
    )