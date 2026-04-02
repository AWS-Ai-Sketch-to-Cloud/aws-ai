param(
    [string]$ExpectedHead = "e7f8a9b0c1d2"
)

$ErrorActionPreference = "Stop"

if (-not $env:DATABASE_URL) {
    $envPath = Join-Path (Get-Location) ".env"
    if (Test-Path $envPath) {
        $line = Get-Content $envPath | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
        if ($line) {
            $env:DATABASE_URL = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
        }
    }
}

if (-not $env:DATABASE_URL) {
    Write-Error "DATABASE_URL is not set. Set env var or add DATABASE_URL to backend/.env"
    exit 1
}

Write-Host "Checking alembic heads..."
$heads = alembic heads
Write-Host $heads

Write-Host "Checking alembic current..."
$current = alembic current
Write-Host $current

if ($current -match $ExpectedHead) {
    Write-Host "OK: DB is synced to expected head ($ExpectedHead)."
    exit 0
}

Write-Warning "DB is not on expected head ($ExpectedHead). Run: alembic upgrade head"
exit 2

