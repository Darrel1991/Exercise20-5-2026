# AiPipeline Logger Service - Start Script
Set-Location $PSScriptRoot

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "Starting AiPipeline Logger on http://localhost:5000" -ForegroundColor Green
python app.py
