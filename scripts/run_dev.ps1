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
    $logDir = Join-Path $rootDir "logs\runtime"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    foreach ($logName in @("app_runtime.txt", "trigger_cycles.txt")) {
        $logPath = Join-Path $logDir $logName
        if (Test-Path $logPath) {
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($logName)
            $archivedPath = Join-Path $logDir ("{0}_{1}.txt" -f $baseName, $timestamp)
            Move-Item -LiteralPath $logPath -Destination $archivedPath -Force
        }
    }

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
    $env:ENABLE_TRIGGER_SCHEDULER = "false"

    Write-Host "Starting FastAPI backend..."
    Write-Host "Local dev launcher disables the background scheduler by default to keep UI/debug paths responsive."
    Write-Host ("Runtime logs will be written to:")
    Write-Host (" - {0}" -f (Join-Path $logDir "app_runtime.txt"))
    Write-Host (" - {0}" -f (Join-Path $logDir "trigger_cycles.txt"))
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
}
finally {
    Pop-Location
}
