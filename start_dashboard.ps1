$root = $PSScriptRoot
Write-Host "API server naye window me start ho raha hai..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; & .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload"
Start-Sleep -Seconds 4
Write-Host "Dashboard start ho raha hai: http://localhost:8501"
& "$root\venv\Scripts\python.exe" -m streamlit run dashboard/app.py
