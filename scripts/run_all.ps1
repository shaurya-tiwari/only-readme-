$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$backendScript = Join-Path $scriptDir "run_dev.ps1"
$frontendScript = Join-Path $scriptDir "run_frontend.ps1"

if (-not (Test-Path $backendScript)) {
    Write-Error "Backend launcher not found at $backendScript"
}

if (-not (Test-Path $frontendScript)) {
    Write-Error "Frontend launcher not found at $frontendScript"
}

Write-Host "Launching RideShield full stack..."
Write-Host "This opens separate PowerShell windows for backend and frontend."

$powershellExe = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

Start-Process -FilePath $powershellExe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $backendScript
)

Start-Sleep -Seconds 2

Start-Process -FilePath $powershellExe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-File", $frontendScript
)

Write-Host "Backend window started."
Write-Host "Frontend window started."
Write-Host "Backend:  http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Fresh backend logs:"
Write-Host " - logs\\runtime\\app_runtime.txt"
Write-Host " - logs\\runtime\\trigger_cycles.txt"
