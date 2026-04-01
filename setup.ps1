# Virtual Environment Setup Script for PowerShell

# 1. Create the virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# 2. Upgrade pip and install requirements
Write-Host "Upgrading pip and installing requirements..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Setup complete! You can activate the environment with: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
