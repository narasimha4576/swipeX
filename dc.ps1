# A short way to run the production setup:  .\dc.ps1 up -d --build   |   .\dc.ps1 ps   |   .\dc.ps1 logs -f api
Set-Location (git rev-parse --show-toplevel)
docker compose --env-file .env.prod -f docker-compose.prod.yml @args