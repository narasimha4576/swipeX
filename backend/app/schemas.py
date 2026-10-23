from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["job_seeker", "recruiter"] = "job_seeker"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    experience_years: float = Field(default=0, ge=0, le=60)
    skills: list[str] = Field(default_factory=list, max_length=30)
    bio: str | None = Field(default=None, max_length=2000)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
        seen = set()
        cleaned = []
        for skill in value:
            skill = skill.strip()
            if not skill:
                continue
            if len(skill) > 50:
                raise ValueError("Each skill must be 50 characters or less")
            if skill.lower() not in seen:
                seen.add(skill.lower())
                cleaned.append(skill)
        return cleaned


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    headline: str | None
    location: str | None
    experience_years: float
    skills: list[str]
    bio: str | None