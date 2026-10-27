import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.database import SessionLocal
from app.importers import greenhouse
from app.models import Company, Job

BOARDS_FILE = Path(__file__).with_name("boards.json")
MAX_JOBS_PER_COMPANY = 40


def load_boards() -> list[dict]:
    if not BOARDS_FILE.exists():
        return []
    return json.loads(BOARDS_FILE.read_text(encoding="utf-8"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_or_create_company(db, token: str, name: str, company_type: str) -> Company:
    company = db.scalar(
        select(Company).where(Company.source == "greenhouse", Company.source_id == token)
    )
    if company is None:
        taken = db.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
        company = Company(
            name=name if taken is None else f"{name} (Greenhouse)",
            company_type=company_type,
            source="greenhouse",
            source_id=token,
            verification_status="verified",
            verified_at=now_utc(),
            verification_note=(
                "Imported from the company's official Greenhouse job board: "
                f"https://boards.greenhouse.io/{token}"
            ),
        )
        db.add(company)
        db.flush()
    return company


def sync_board(db, client: httpx.Client, board: dict) -> dict:
    token = board["token"]
    raw_jobs = greenhouse.fetch_jobs(token, client)
    name = board.get("name") or greenhouse.fetch_board_name(token, client) or token.title()
    company = get_or_create_company(db, token, name, board.get("company_type", "mnc"))
    company.company_type = board.get("company_type", company.company_type)

    started = now_utc()
    seen: set[str] = set()
    created = updated = closed = 0

    for raw in raw_jobs:
        if len(seen) >= MAX_JOBS_PER_COMPANY:
            break
        fields = greenhouse.to_job_fields(raw)
        if fields is None:
            continue
        external_id = fields.pop("external_id")
        posted = fields.pop("created_at", None)
        seen.add(external_id)

        job = db.scalar(
            select(Job).where(Job.source == "greenhouse", Job.external_id == external_id)
        )
        if job is None:
            extra = {"created_at": posted} if posted else {}
            db.add(
                Job(
                    company_id=company.id,
                    source="greenhouse",
                    external_id=external_id,
                    applicant_count=0,
                    is_active=True,
                    last_seen_at=started,
                    **fields,
                    **extra,
                )
            )
            created += 1
        else:
            for key, value in fields.items():
                setattr(job, key, value)
            job.company_id = company.id
            job.is_active = True
            job.last_seen_at = started
            updated += 1

    open_jobs = db.scalars(
        select(Job).where(
            Job.company_id == company.id,
            Job.source == "greenhouse",
            Job.is_active.is_(True),
        )
    )
    for job in open_jobs:
        if job.external_id not in seen:
            job.is_active = False
            closed += 1

    db.commit()
    return {"created": created, "updated": updated, "closed": closed}


def sync_all() -> dict:
    boards = load_boards()
    totals = {"boards": 0, "created": 0, "updated": 0, "closed": 0, "failed": 0}
    print(f"Job import started for {len(boards)} companies...", flush=True)
    with httpx.Client(
        timeout=30, headers=greenhouse.HEADERS, follow_redirects=True
    ) as client:
        for board in boards:
            try:
                with SessionLocal() as db:
                    result = sync_board(db, client, board)
                totals["boards"] += 1
                for key in ("created", "updated", "closed"):
                    totals[key] += result[key]
            except Exception as exc:
                totals["failed"] += 1
                print(f"  Import failed for {board.get('token')}: {exc}", flush=True)
            time.sleep(1)
    print(f"Job import finished: {totals}", flush=True)
    return totals