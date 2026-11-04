"""speed indexes

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

INDEXES = [
    ("ix_perf_jobs_active_created",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_active_created ON jobs (created_at DESC, id DESC) WHERE is_active"),
    ("ix_perf_jobs_country_created",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_country_created ON jobs (country, created_at DESC) WHERE is_active"),
    ("ix_perf_jobs_company",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_company ON jobs (company_id)"),
    ("ix_perf_jobs_source_external",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_source_external ON jobs (source, external_id)"),
    ("ix_perf_jobs_posted_by",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_posted_by ON jobs (posted_by) WHERE posted_by IS NOT NULL"),
    ("ix_perf_jobs_title_trgm",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops)"),
    ("ix_perf_jobs_skills_trgm",
     "CREATE INDEX IF NOT EXISTS ix_perf_jobs_skills_trgm ON jobs USING gin ((skills::text) gin_trgm_ops)"),
    ("ix_perf_companies_name_trgm",
     "CREATE INDEX IF NOT EXISTS ix_perf_companies_name_trgm ON companies USING gin (name gin_trgm_ops)"),
    ("ix_perf_companies_lower_name",
     "CREATE INDEX IF NOT EXISTS ix_perf_companies_lower_name ON companies (lower(name))"),
    ("ix_perf_companies_verification",
     "CREATE INDEX IF NOT EXISTS ix_perf_companies_verification ON companies (verification_status)"),
    ("ix_perf_applications_job",
     "CREATE INDEX IF NOT EXISTS ix_perf_applications_job ON applications (job_id)"),
    ("ix_perf_resumes_user",
     "CREATE INDEX IF NOT EXISTS ix_perf_resumes_user ON resumes (user_id)"),
    ("ix_perf_experiences_user",
     "CREATE INDEX IF NOT EXISTS ix_perf_experiences_user ON experiences (user_id)"),
    ("ix_perf_portfolio_user",
     "CREATE INDEX IF NOT EXISTS ix_perf_portfolio_user ON portfolio_items (user_id)"),
    ("ix_perf_recruiter_company",
     "CREATE INDEX IF NOT EXISTS ix_perf_recruiter_company ON recruiter_profiles (company_id)"),
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for _name, sql in INDEXES:
        op.execute(sql)


def downgrade() -> None:
    for name, _sql in reversed(INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")