from contextlib import contextmanager

from sqlalchemy import text

from app.database import engine

IMPORT_LOCK_ID = 727001


@contextmanager
def exclusive(lock_id):
    """Yields True if this process got the lock, False if another process already holds it."""
    # AUTOCOMMIT: no transaction stays open, so Neon never ends the connection as "idle in transaction".
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    got = False
    try:
        got = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": lock_id}).scalar())
        try:
            yield got
        finally:
            if got:
                try:
                    conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": lock_id})
                except Exception:
                    pass  # a closed connection releases the lock by itself
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_exclusive(lock_id, work):
    """Runs work() only if nobody else is running the same job. Returns None when skipped."""
    with exclusive(lock_id) as got:
        if not got:
            print("Another run is already in progress, skipping this one", flush=True)
            return None
        return work()