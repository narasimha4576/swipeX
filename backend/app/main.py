from fastapi import FastAPI
from sqlalchemy import text

from app import models  # noqa: F401  (this loads the tables)
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SwipeX API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "swipex-api"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "ok"}