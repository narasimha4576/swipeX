import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
MAX_BODY_BYTES = 12 * 1024 * 1024
DOC_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
WEAK_KEYS = {"changeme", "secret", "your-secret-key", "supersecret", "password"}


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


def cors_origins() -> list[str]:
    """Websites allowed to call the API. Add yours with CORS_ORIGINS=https://a.com,https://b.com"""
    extra = [o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if is_production() and extra:
        return extra
    return DEFAULT_ORIGINS + [o for o in extra if o not in DEFAULT_ORIGINS]


def check_secret_key(secret: str, production: bool) -> list[str]:
    problems = []
    if not secret or len(secret) < 32:
        problems.append("SECRET_KEY should be at least 32 characters long")
    if secret and secret.lower() in WEAK_KEYS:
        problems.append("SECRET_KEY is a well-known weak value")
    if problems and production:
        raise RuntimeError("; ".join(problems))
    return problems


def install_security(app: FastAPI) -> None:
    for problem in check_secret_key(os.getenv("SECRET_KEY", ""), is_production()):
        print(f"WARNING: {problem}", flush=True)

    if is_production():
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) not in DOC_PATHS]

    @app.middleware("http")
    async def protect(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "The request is too large"}, status_code=413)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if response.headers.get("content-type", "").startswith("application/json"):
            response.headers.setdefault("Cache-Control", "no-store")
        if os.getenv("ENABLE_HSTS", "").lower() == "true":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response