param(
    [string]$ExpectedHead = "01898398e88a"
)

$ErrorActionPreference = "Stop"

if (-not $env:DATABASE_URL) {
    Write-Error "DATABASE_URL is not set."
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

