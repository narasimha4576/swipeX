# Makes .env.prod with fresh random passwords. Run it once.
param([switch]$Force)
Set-Location (git rev-parse --show-toplevel)

if ((Test-Path .env.prod) -and -not $Force) {
  Write-Host ".env.prod already exists, so nothing was changed." -ForegroundColor Yellow
  Write-Host "Only use -Force on a brand new setup. New passwords will not fit an existing database volume." -ForegroundColor Yellow
  exit 1
}

function RandomHex($bytes) {
  $buffer = New-Object byte[] $bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
  -join ($buffer | ForEach-Object { $_.ToString("x2") })
}

$dbPassword = RandomHex 16
$lines = @(
  "POSTGRES_PASSWORD=$dbPassword",
  "DATABASE_URL=postgresql+psycopg://swipex:$dbPassword@db:5432/swipex",
  "SECRET_KEY=$(RandomHex 32)",
  "APP_ENV=production",
  "TRUST_PROXY=true",
  "ENABLE_HSTS=false",
  "ACCESS_TOKEN_EXPIRE_MINUTES=60",
  "IMPORT_ENABLED=true",
  "IMPORT_INTERVAL_MINUTES=15",
  "IMPORT_ALL_JOBS=true",
  "SKIP_RETENTION_DAYS=15"
)

# keep your AI and job-source keys from backend\.env
if (Test-Path backend\.env) {
  foreach ($line in Get-Content backend\.env) {
    if ($line -match '^(AI_BASE_URL|AI_MODEL|AI_API_KEY|ADZUNA_APP_ID|ADZUNA_APP_KEY|ADZUNA_COUNTRIES|TAVILY_API_KEY|YOUTUBE_API_KEY)=.+') {
      $lines += $line
    }
  }
}

[System.IO.File]::WriteAllLines("$PWD\.env.prod", $lines)

if (-not (Test-Path .gitignore) -or -not (Select-String -Path .gitignore -Pattern '^\.env\.prod$' -Quiet)) {
  Add-Content .gitignore "`n.env.prod"
}
Write-Host "Created .env.prod (passwords are random, and the file is ignored by git)." -ForegroundColor Green