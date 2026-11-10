FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as a normal user, not root. Uploaded files live in /app/uploads (a volume).
RUN useradd --create-home --uid 1000 swipex \
    && mkdir -p /app/uploads \
    && chown -R swipex:swipex /app/uploads
USER swipex

EXPOSE 8000

# Update the database, then start the website.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]