"""One scheduled run for GitHub Actions: import jobs, clean up, record a sign of life."""
import sys

from app.errors import cleanup_old_errors
from app.importers.scheduler import sync_all
from app.maintenance import cleanup_old_skips
from app.status import heartbeat


def main():
    heartbeat()
    totals = sync_all()
    print("Import result:", totals if totals is not None else "skipped (another import is running)", flush=True)
    print("Old skipped jobs removed:", cleanup_old_skips(), flush=True)
    print("Old errors removed:", cleanup_old_errors(), flush=True)
    heartbeat()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Scheduled run failed:", exc, flush=True)
        sys.exit(1)