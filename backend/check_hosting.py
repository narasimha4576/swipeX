"""Checks a Postgres database before SwipeX is hosted on it.
Usage:  python backend\check_hosting.py "<the DIRECT connection string>"
"""
import re
import sys
import time

import psycopg


def clean(url):
    url = url.strip().replace("postgres://", "postgresql://")
    return re.sub(r"^postgresql\+psycopg://", "postgresql://", url)


def host_of(url):
    match = re.search(r"@([^/:?]+)", url)
    return match.group(1) if match else "?"


def say(ok, text, extra=""):
    print(("PASS  " if ok else "WARN  ") + text + (f"   [{extra}]" if extra else ""))
    return ok


def main():
    if len(sys.argv) < 2:
        print('Usage: python backend\\check_hosting.py "<direct connection string>"')
        sys.exit(1)
    url = clean(sys.argv[1])
    host = host_of(url)
    print(f"Checking {host}\n")
    if "-pooler" in host:
        say(False, "This is the POOLED address. Use the DIRECT one for this check.")

    started = time.perf_counter()
    try:
        conn = psycopg.connect(url, connect_timeout=40, autocommit=True)
    except Exception as exc:
        say(False, "Could not connect", str(exc).splitlines()[0][:120])
        sys.exit(1)
    say(True, "Connected", f"{time.perf_counter() - started:.1f} s, the first time includes waking the database")

    version = conn.execute("SHOW server_version").fetchone()[0]
    say(version.split(".")[0].isdigit() and int(version.split(".")[0]) >= 15, "PostgreSQL version", version)

    timings = []
    for _ in range(5):
        t = time.perf_counter()
        conn.execute("SELECT 1").fetchone()
        timings.append((time.perf_counter() - t) * 1000)
    say(True, "Speed of a simple question", f"{sum(timings) / len(timings):.0f} ms on average")

    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        score = conn.execute("SELECT similarity('hello', 'hallo')").fetchone()[0]
        say(score > 0, "Text search extension (pg_trgm) works")
    except Exception as exc:
        say(False, "pg_trgm is not available", str(exc).splitlines()[0][:100])

    try:
        length = conn.execute("SELECT json_array_length('[1,2,3]'::json)").fetchone()[0]
        say(length == 3, "JSON functions work")
    except Exception as exc:
        say(False, "JSON functions failed", str(exc).splitlines()[0][:100])

    try:
        conn.execute("CREATE TEMP TABLE swipex_check (id int)")
        conn.execute("INSERT INTO swipex_check VALUES (1)")
        conn.execute("DROP TABLE swipex_check")
        say(True, "Can create tables and write data")
    except Exception as exc:
        say(False, "Cannot write", str(exc).splitlines()[0][:100])

    other = psycopg.connect(url, connect_timeout=40, autocommit=True)
    first = conn.execute("SELECT pg_try_advisory_lock(990001)").fetchone()[0]
    second = other.execute("SELECT pg_try_advisory_lock(990001)").fetchone()[0]
    say(first and not second, "The one-import-at-a-time lock works on this address",
        "if this says WARN, you are on a pooled address" if not (first and not second) else "")
    conn.execute("SELECT pg_advisory_unlock(990001)")
    other.close()

    size = conn.execute("SELECT pg_database_size(current_database())").fetchone()[0]
    mb = size / (1024 * 1024)
    say(True, "Database size now", f"{mb:.1f} MB of the free 1024 MB")
    conn.close()
    print("\nIf every line says PASS, this database is ready for SwipeX.")


if __name__ == "__main__":
    main()