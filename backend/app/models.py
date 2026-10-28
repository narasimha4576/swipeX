from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="job_seeker")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    college: Mapped[str | None] = mapped_column(String(200), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authorized_countries: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requires_sponsorship: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    willing_to_relocate: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_ctc_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_ctc_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    company_type: Mapped[str] = mapped_column(String(20), default="mnc")
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="native", server_default="native")
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trust_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="one_job_per_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    posted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    job_type: Mapped[str] = mapped_column(String(20), default="full_time")
    experience_level: Mapped[str] = mapped_column(String(20), default="fresher")
    salary_min_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    applicant_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(30), default="native", server_default="native")
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    version_name: Mapped[str] = mapped_column(String(120))
    file_path: Mapped[str] = mapped_column(String(500))
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="one_swipe_per_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    direction: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="one_application_per_job"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="saved")
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    start_year: Mapped[int] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))


from sqlalchemy import event, inspect  # noqa: E402


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


@event.listens_for(Application, "after_insert")
def log_status_on_insert(mapper, connection, target):
    connection.execute(
        ApplicationEvent.__table__.insert().values(
            application_id=target.id, status=target.status
        )
    )


@event.listens_for(Application, "after_update")
def log_status_on_update(mapper, connection, target):
    if inspect(target).attrs.status.history.has_changes():
        connection.execute(
            ApplicationEvent.__table__.insert().values(
                application_id=target.id, status=target.status
            )
        )