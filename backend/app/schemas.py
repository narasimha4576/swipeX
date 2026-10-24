from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


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


class ExperienceCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    start_year: int = Field(ge=1980, le=2100)
    end_year: int | None = Field(default=None, ge=1980, le=2100)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_years(self):
        if self.end_year is not None and self.end_year < self.start_year:
            raise ValueError("End year cannot be before start year")
        return self


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    start_year: int
    end_year: int | None
    description: str | None


class PortfolioCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=500)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("Link must start with http:// or https://")
        return value


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    description: str | None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_type: str
    location: str | None
    website: str | None
    founded_year: int | None


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    location: str | None
    is_remote: bool
    job_type: str
    experience_level: str
    salary_min_lpa: float | None
    salary_max_lpa: float | None
    skills: list[str]
    applicant_count: int
    competition_level: str
    created_at: datetime
    company: CompanyOut


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int