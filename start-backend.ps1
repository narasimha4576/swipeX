Set-Location $PSScriptRoot
docker compose up -d
Set-Location backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload