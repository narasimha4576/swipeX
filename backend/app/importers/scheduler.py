import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.importers.sync import sync_all

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if os.getenv("IMPORT_ENABLED", "true").lower() != "true":
        print("Job import is switched off (IMPORT_ENABLED=false)", flush=True)
        return
    minutes = int(os.getenv("IMPORT_INTERVAL_MINUTES", "60"))
    scheduler.add_job(
        sync_all,
        "interval",
        minutes=minutes,
        id="job-import",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=20),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print(f"Job import scheduled every {minutes} minutes", flush=True)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)