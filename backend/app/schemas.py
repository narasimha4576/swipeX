import re
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
    verification_status: str = "unverified"
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
    source: str = "native"
    apply_url: str | None = None
    created_at: datetime
    company: CompanyOut


class JobPage(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    page_size: int


class SwipeCreate(BaseModel):
    job_id: int
    direction: Literal["left", "right"]


class SwipeOut(BaseModel):
    job_id: int
    direction: str


class DeckOut(BaseModel):
    items: list[JobOut]
    remaining: int
    saved: int
    skipped: int


class CompanyUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    company_type: Literal["mnc", "startup", "new_startup"]
    location: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=255)
    founded_year: int | None = Field(default=None, ge=1800, le=2100)

    @field_validator("website")
    @classmethod
    def check_website(cls, value):
        if value is None:
            return value
        value = value.strip()
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        return value or None


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=5000)
    location: str | None = Field(default=None, max_length=120)
    is_remote: bool = False
    job_type: Literal["full_time", "internship"] = "full_time"
    experience_level: Literal["fresher", "junior", "mid", "senior"] = "fresher"
    salary_min_lpa: float | None = Field(default=None, ge=0, le=500)
    salary_max_lpa: float | None = Field(default=None, ge=0, le=500)
    skills: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("skills")
    @classmethod
    def clean_job_skills(cls, value: list[str]) -> list[str]:
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

    @model_validator(mode="after")
    def check_job(self):
        has_min = self.salary_min_lpa is not None
        has_max = self.salary_max_lpa is not None
        if has_min != has_max:
            raise ValueError("Give both minimum and maximum salary, or leave both empty")
        if has_min and self.salary_min_lpa > self.salary_max_lpa:
            raise ValueError("Minimum salary cannot be higher than maximum salary")
        if not self.is_remote and not (self.location and self.location.strip()):
            raise ValueError("Add a location or mark the job as remote")
        return self


class MyJobOut(JobOut):
    is_active: bool


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_name: str
    is_default: bool
    created_at: datetime


class ApplyIn(BaseModel):
    job_id: int
    resume_id: int


class ApplicationOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    resume_name: str | None
    job: JobOut


class StatusUpdate(BaseModel):
    status: Literal["applied", "shortlisted", "interview", "rejected"]


class ApplicantOut(BaseModel):
    application_id: int
    status: str
    updated_at: datetime
    full_name: str
    email: str
    headline: str | None
    location: str | None
    experience_years: float
    skills: list[str]
    bio: str | None
    resume_name: str | None
    experiences: list[ExperienceOut]
    portfolio: list[PortfolioOut]


class VerificationRequest(BaseModel):
    note: str = Field(min_length=10, max_length=1000)


class VerificationStatusOut(BaseModel):
    status: str
    note: str | None = None


class DecisionIn(BaseModel):
    decision: Literal["verified", "rejected", "unverified"]
    note: str | None = Field(default=None, max_length=1000)


class AdminCompanyOut(CompanyOut):
    verification_note: str | None = None
    verified_at: datetime | None = None
    source: str = "native"
    owner_email: str | None = None
    jobs_count: int = 0


class TrustSignal(BaseModel):
    key: str
    label: str
    ok: bool
    known: bool = True
    applicable: bool = True
    detail: str | None = None


class TrustFacts(BaseModel):
    founded_year: int | None = None
    employees: int | None = None
    headquarters: str | None = None
    website: str | None = None
    wikipedia_url: str | None = None
    wikidata_url: str | None = None
    description: str | None = None


class HiringStats(BaseModel):
    jobs_posted: int
    open_jobs: int
    applications: int
    responded: int
    response_rate: float | None = None
    avg_response_days: float | None = None


class TrustCardOut(BaseModel):
    company: CompanyOut
    level: Literal["strong", "good", "limited"]
    signals: list[TrustSignal]
    facts: TrustFacts
    hiring: HiringStats | None = None
    source: str
    checked_at: str | None = None


class MyJobStatus(BaseModel):
    application_id: int
    status: str


class ApplicationDetailsIn(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    linkedin_url: str | None = Field(default=None, max_length=255)
    github_url: str | None = Field(default=None, max_length=255)
    portfolio_url: str | None = Field(default=None, max_length=255)
    college: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=100)
    discipline: str | None = Field(default=None, max_length=100)
    graduation_year: int | None = Field(default=None, ge=1980, le=2100)
    authorized_countries: str | None = Field(default=None, max_length=200)
    requires_sponsorship: bool = False
    willing_to_relocate: bool = False
    notice_period_days: int | None = Field(default=None, ge=0, le=365)
    current_ctc_lpa: float | None = Field(default=None, ge=0, le=1000)
    expected_ctc_lpa: float | None = Field(default=None, ge=0, le=1000)
    cover_letter: str | None = Field(default=None, max_length=3000)

    @field_validator(
        "phone", "linkedin_url", "github_url", "portfolio_url", "college", "degree",
        "discipline", "authorized_countries", "cover_letter",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value):
        if value is None:
            return value
        digits = re.sub(r"\D", "", value)
        if not re.fullmatch(r"[0-9+()\-\s]+", value) or not 7 <= len(digits) <= 15:
            raise ValueError("Enter a valid phone number, for example +91 98765 43210")
        return value

    @field_validator("linkedin_url", "github_url", "portfolio_url")
    @classmethod
    def check_links(cls, value):
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("Links must start with http:// or https://")
        return value


class ApplicationDetailsOut(ApplicationDetailsIn):
    ready: bool
    missing: list[str]


class AutofillJob(BaseModel):
    id: int
    title: str
    company: str
    apply_url: str | None = None


class AutofillApplicant(BaseModel):
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    website: str | None = None
    college: str | None = None
    degree: str | None = None
    discipline: str | None = None
    graduation_year: int | None = None
    authorized_countries: str | None = None
    requires_sponsorship: bool = False
    willing_to_relocate: bool = False
    notice_period_days: int | None = None
    current_ctc_lpa: float | None = None
    expected_ctc_lpa: float | None = None
    cover_letter: str | None = None
    how_did_you_hear: str = "SwipeX"
    skills: list[str] = []


class AutofillResume(BaseModel):
    id: int
    name: str
    filename: str
    mime: str = "application/pdf"
    data_base64: str | None = None


class AutofillPayload(BaseModel):
    job: AutofillJob
    applicant: AutofillApplicant
    resume: AutofillResume | None = None
    ready: bool
    missing: list[str]