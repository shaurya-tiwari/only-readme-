$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

Write-Host "Starting RideShield development environment..."

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not running. Please start Docker first."
}

Write-Host "Starting PostgreSQL..."
Push-Location $rootDir
try {
    docker-compose up -d db | Out-Host
    Start-Sleep -Seconds 3

    Write-Host "Waiting for database..."
    do {
        docker-compose exec -T db pg_isready -U rideshield -d rideshield_db *> $null
        if ($LASTEXITCODE -ne 0) {
            Start-Sleep -Seconds 1
        }
    } while ($LASTEXITCODE -ne 0)
    Write-Host "Database ready"

    $activateScript = Join-Path $rootDir "venv\Scripts\Activate.ps1"
    if (-not (Test-Path $activateScript)) {
        Write-Error "Virtual environment not found at $activateScript"
    }

    . $activateScript

    Remove-Item Env:DEBUG -ErrorAction SilentlyContinue
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:DATABASE_URL_SYNC -ErrorAction SilentlyContinue

    Write-Host "Starting FastAPI backend..."
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
}
finally {
    Pop-Location
}
