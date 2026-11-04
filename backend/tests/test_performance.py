import logging
import os
import time

from sqlalchemy import create_engine

from app.cache import cached, clear_cache
from app.database import engine
from app.joblock import exclusive, run_exclusive
from app.perf import install_slow_query_log


# ---------- only one import at a time ----------


def test_only_one_process_gets_the_lock():
    with exclusive(999001) as first:
        assert first is True
        with exclusive(999001) as second:
            assert second is False
    with exclusive(999001) as again:
        assert again is True


def test_a_second_run_is_skipped_while_the_first_is_running():
    assert run_exclusive(999002, lambda: "ran") == "ran"
    with exclusive(999002):
        assert run_exclusive(999002, lambda: "ran") is None


# ---------- the cache ----------


def test_cache_keeps_a_value_for_a_while():
    calls = []

    def build():
        calls.append(1)
        return len(calls)

    assert cached("k", 60, build) == 1
    assert cached("k", 60, build) == 1
    assert len(calls) == 1


def test_cache_forgets_after_its_time():
    calls = []

    def build():
        calls.append(1)
        return len(calls)

    assert cached("short", 0.05, build) == 1
    time.sleep(0.1)
    assert cached("short", 0.05, build) == 2


def test_clearing_the_cache_forces_a_fresh_answer():
    assert cached("c", 60, lambda: "old") == "old"
    clear_cache()
    assert cached("c", 60, lambda: "new") == "new"


def test_the_country_list_is_cached(client, seeker, make_job, db):
    first = make_job()
    first.country = "India"
    db.commit()
    assert client.get("/job-countries", headers=seeker["headers"]).json() == [{"country": "India", "count": 1}]

    second = make_job("Another Job", company="Beta Corp")
    second.country = "India"
    db.commit()
    assert client.get("/job-countries", headers=seeker["headers"]).json()[0]["count"] == 1  # still remembered

    clear_cache()
    assert client.get("/job-countries", headers=seeker["headers"]).json()[0]["count"] == 2


# ---------- compression, slow queries, connections ----------


def test_big_answers_are_compressed(client, seeker, make_job):
    for i in range(6):
        make_job(f"Python Developer {i}", company=f"Company {i}")
    response = client.get("/jobs", headers={**seeker["headers"], "Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"


def test_slow_queries_are_logged(caplog):
    small = create_engine("sqlite://")
    install_slow_query_log(small, threshold_ms=0)
    with caplog.at_level(logging.WARNING, logger="swipex.slow_query"):
        with small.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    assert "slow query" in caplog.text


def test_fast_queries_are_not_logged(caplog):
    small = create_engine("sqlite://")
    install_slow_query_log(small, threshold_ms=10_000)
    with caplog.at_level(logging.WARNING, logger="swipex.slow_query"):
        with small.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    assert "slow query" not in caplog.text


def test_the_connection_pool_has_the_expected_size():
    assert engine.pool.size() == int(os.getenv("DB_POOL_SIZE", "10"))