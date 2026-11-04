"""The background worker: job imports and cleanup, as its own program.

Run it with:   python worker.py        (or .\start-worker.ps1 from the project folder)
Then start the website with RUN_SCHEDULER_IN_API=false so only this program imports jobs.
"""
import signal
import threading

from app.importers.scheduler import start_scheduler, stop_scheduler

stop = threading.Event()


def request_stop(signum, frame):
    stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    start_scheduler()
    print("SwipeX worker is running. Press Ctrl+C to stop it.", flush=True)
    while not stop.wait(1):
        pass
    stop_scheduler()
    print("SwipeX worker stopped.", flush=True)