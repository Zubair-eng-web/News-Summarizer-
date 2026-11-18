# One-command setup (Windows PowerShell). Docker ki zaroorat nahi.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path venv)) { python -m venv venv }
$py = ".\venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt -r requirements-dev.txt
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host ".env ban gayi: ab usme GEMINI_API_KEY waghera bharein"
}
& $py -m app.core.migrate
& $py -m pytest tests -q
Write-Host "Setup mukammal. API: uvicorn app.main:app --reload"