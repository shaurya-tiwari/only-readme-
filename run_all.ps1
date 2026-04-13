# RideShield - Start API + Scheduler + Frontend as separate processes
# Usage: .\run_all.ps1

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  RideShield - System Launcher" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting three separate processes:" -ForegroundColor Yellow
Write-Host "  [1] API Server    (uvicorn - port 8000)" -ForegroundColor Green
Write-Host "  [2] Scheduler     (trigger engine)" -ForegroundColor Green
Write-Host "  [3] Frontend      (Vite - port 3000)" -ForegroundColor Green
Write-Host ""

# Start API server in a new window
$apiProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "backend.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory $PSScriptRoot `
    -PassThru `
    -NoNewWindow:$false

Write-Host "[API] Started (PID: $($apiProcess.Id))" -ForegroundColor Green

# Give the API server a moment to bind the port
Start-Sleep -Seconds 2

# Start scheduler in a new window
$schedulerProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m", "backend.scheduler_worker" `
    -WorkingDirectory $PSScriptRoot `
    -PassThru `
    -NoNewWindow:$false

Write-Host "[Scheduler] Started (PID: $($schedulerProcess.Id))" -ForegroundColor Green

# Start frontend in a new window
$frontendProcess = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory (Join-Path $PSScriptRoot "frontend") `
    -PassThru `
    -NoNewWindow:$false

Write-Host "[Frontend] Started (PID: $($frontendProcess.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "All processes running. Close their windows to stop." -ForegroundColor Yellow
Write-Host "Frontend:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "API:       http://localhost:8000" -ForegroundColor Cyan
Write-Host "Docs:      http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
