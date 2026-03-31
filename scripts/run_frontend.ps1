$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$frontendDir = Join-Path $rootDir "frontend"

if (-not (Test-Path $frontendDir)) {
    Write-Error "Frontend directory not found at $frontendDir"
}

Write-Host "Starting RideShield frontend..."
Push-Location $frontendDir
try {
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Host "Installing frontend dependencies..."
        cmd /c npm install | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install failed."
        }
    }

    Write-Host "Starting Vite frontend on http://localhost:3000 ..."
    cmd /c npm run dev
}
finally {
    Pop-Location
}
