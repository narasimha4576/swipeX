import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.database import SessionLocal
from app.importers import adzuna, ashby, greenhouse, lever, thirdparty
from app.models import Company, Job

SOURCES = {module.SOURCE: module for module in (greenhouse, lever, ashby)}
BOARDS_FILE = Path(__file__).with_name("boards.json")
MAX_JOBS_PER_COMPANY = 300


def load_boards() -> list[dict]:
    if not BOARDS_FILE.exists():
        return []
    boards = json.loads(BOARDS_FILE.read_text(encoding="utf-8"))
    for board in boards:
        board.setdefault("source", "greenhouse")
    return boards


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_or_create_company(db, module, token: str, name: str, company_type: str) -> Company:
    company = db.scalar(
        select(Company).where(Company.source == module.SOURCE, Company.source_id == token)
    )
    if company is None:
        taken = db.scalar(select(Company).where(func.lower(Company.name) == name.lower()))
        company = Company(
            name=name if taken is None else f"{name} ({module.LABEL})",
            company_type=company_type,
            source=module.SOURCE,
            source_id=token,
            verification_status="verified",
            verified_at=now_utc(),
            verification_note=(
                f"Imported from the company's official {module.LABEL} job board: "
                f"{module.board_url(token)}"
            ),
        )
        db.add(company)
        db.flush()
    return company


def sync_board(db, client: httpx.Client, module, board: dict) -> dict:
    token = board["token"]
    raw_jobs = module.fetch_jobs(token, client)
    name = board.get("name") or module.fetch_board_name(token, client) or token.title()
    company = get_or_create_company(db, module, token, name, board.get("company_type", "mnc"))
    company.company_type = board.get("company_type", company.company_type)

    started = now_utc()
    seen: set[str] = set()
    created = updated = closed = 0

    for raw in raw_jobs:
        if len(seen) >= MAX_JOBS_PER_COMPANY:
            break
        fields = module.to_job_fields(raw)
        if fields is None:
            continue
        external_id = fields.pop("external_id")
        posted = fields.pop("created_at", None)
        seen.add(external_id)

        job = db.scalar(
            select(Job).where(Job.source == module.SOURCE, Job.external_id == external_id)
        )
        if job is None:
            extra = {"created_at": posted} if posted else {}
            db.add(
                Job(
                    company_id=company.id,
                    source=module.SOURCE,
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
            Job.source == module.SOURCE,
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
    print(f"Job import started for {len(boards)} company boards...", flush=True)
    with httpx.Client(
        timeout=30, headers=greenhouse.HEADERS, follow_redirects=True
    ) as client:
        for board in boards:
            module = SOURCES.get(board.get("source", "greenhouse"))
            if module is None:
                totals["failed"] += 1
                print(f"  Unknown source for {board.get('token')}", flush=True)
                continue
            try:
                with SessionLocal() as db:
                    result = sync_board(db, client, module, board)
                totals["boards"] += 1
                for key in ("created", "updated", "closed"):
                    totals[key] += result[key]
            except Exception as exc:
                totals["failed"] += 1
                print(f"  Import failed for {board.get('source')}:{board.get('token')}: {exc}", flush=True)
            time.sleep(1)

        try:
            result = thirdparty.sync(client)
            for key in ("created", "updated", "closed"):
                totals[key] += result[key]
        except Exception as exc:
            totals["failed"] += 1
            print(f"  Third-party import failed: {exc}", flush=True)

        if adzuna.enabled():
            try:
                result = adzuna.sync(client)
                for key in ("created", "updated", "closed"):
                    totals[key] += result[key]
            except Exception as exc:
                totals["failed"] += 1
                print(f"  Adzuna import failed: {exc}", flush=True)

    print(f"Job import finished: {totals}", flush=True)
    return totals