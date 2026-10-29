import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.importers.sync import sync_all
from app.maintenance import SKIP_RETENTION_DAYS, cleanup_old_skips

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    now = datetime.now(timezone.utc)

    scheduler.add_job(
        cleanup_old_skips,
        "interval",
        hours=6,
        id="cleanup-skips",
        next_run_time=now + timedelta(seconds=30),
        max_instances=1,
        coalesce=True,
    )
    print(f"Skipped jobs older than {SKIP_RETENTION_DAYS} days are cleared every 6 hours", flush=True)

    if os.getenv("IMPORT_ENABLED", "true").lower() == "true":
        minutes = int(os.getenv("IMPORT_INTERVAL_MINUTES", "15"))
        scheduler.add_job(
            sync_all,
            "interval",
            minutes=minutes,
            id="job-import",
            next_run_time=now + timedelta(seconds=20),
            max_instances=1,
            coalesce=True,
        )
        print(f"Job import scheduled every {minutes} minutes", flush=True)
    else:
        print("Job import is switched off (IMPORT_ENABLED=false)", flush=True)

    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)