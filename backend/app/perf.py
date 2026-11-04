import logging
import os
import time

from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import event

log = logging.getLogger("swipex.slow_query")
_watched = set()


def install_slow_query_log(engine, threshold_ms=300):
    """Prints a warning for every database query slower than threshold_ms."""
    if id(engine) in _watched:
        return
    _watched.add(id(engine))

    @event.listens_for(engine, "before_cursor_execute")
    def start(conn, cursor, statement, parameters, context, executemany):
        conn.info["swipex_start"] = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def finish(conn, cursor, statement, parameters, context, executemany):
        started = conn.info.pop("swipex_start", None)
        if started is None:
            return
        ms = (time.perf_counter() - started) * 1000
        if ms >= threshold_ms:
            log.warning("slow query (%.0f ms): %s", ms, " ".join(statement.split())[:300])


def install_performance(app, engine):
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    install_slow_query_log(engine, int(os.getenv("SLOW_QUERY_MS", "300")))