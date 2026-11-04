import re
import sys
from pathlib import Path

from sqlalchemy import text

from app.database import engine

BASE = Path(__file__).resolve().parent
MIGRATIONS = list(BASE.glob("alembic/versions/0010*.py"))

ACTIVE = "j.is_active AND c.verification_status != 'rejected'"
JOIN = "FROM jobs j JOIN companies c ON c.id = j.company_id"
QUERIES = {
    "newest jobs (the Jobs page)": f"SELECT j.id {JOIN} WHERE {ACTIVE} ORDER BY j.created_at DESC, j.id DESC LIMIT 12",
    "search the word python": (
        f"SELECT j.id {JOIN} WHERE {ACTIVE} AND (j.title ILIKE '%python%' OR c.name ILIKE '%python%' "
        "OR CAST(j.skills AS TEXT) ILIKE '%python%') ORDER BY j.created_at DESC, j.id DESC LIMIT 12"
    ),
    "newest jobs in one country": (
        f"SELECT j.id {JOIN} WHERE {ACTIVE} AND j.country = 'India' ORDER BY j.created_at DESC, j.id DESC LIMIT 12"
    ),
    "applicants of one job": "SELECT a.id FROM applications a WHERE a.job_id = 1",
}


def explain(conn, sql):
    best = None
    plan = ""
    for _ in range(3):
        rows = conn.execute(text("EXPLAIN ANALYZE " + sql)).fetchall()
        plan = "\n".join(r[0] for r in rows)
        ms = float(re.search(r"Execution Time: ([0-9.]+) ms", plan).group(1))
        best = ms if best is None else min(best, ms)
    used = sorted(set(re.findall(r"(?:using|Bitmap Index Scan on) (ix_\w+)", plan)))
    return best, used


def main():
    with engine.connect() as conn:
        jobs = conn.execute(text("SELECT count(*) FROM jobs")).scalar()
        print(f"Jobs in the database: {jobs}")
        print()
        print("Speed indexes")
        if not MIGRATIONS:
            print("  (not added yet)")
        else:
            wanted = sorted(set(re.findall(r'"(ix_perf_\w+)"', MIGRATIONS[0].read_text(encoding="utf-8"))))
            have = {r[0] for r in conn.execute(text("SELECT indexname FROM pg_indexes WHERE indexname LIKE 'ix_perf_%'"))}
            for name in wanted:
                print(f"  {'ok     ' if name in have else 'MISSING'}  {name}")
            if not wanted or not all(n in have for n in wanted):
                print("  Run:  cd backend; alembic upgrade head")
        print()
        print("Query speed (best of 3)")
        for label, sql in QUERIES.items():
            ms, used = explain(conn, sql)
            print(f"  {label:<30} {ms:8.2f} ms   {', '.join(used) if used else 'reads the whole table'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Could not run the check:", exc)
        sys.exit(1)