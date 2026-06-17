# Run this script to auto-fix lint issues before pushing.
# Requires: pip install ruff
Set-Location $PSScriptRoot\..

Write-Host "Running ruff format..." -ForegroundColor Cyan
ruff format framework/ tests/

Write-Host "Running ruff check --fix..." -ForegroundColor Cyan
ruff check framework/ tests/ --fix

Write-Host "Done. Review changes and commit." -ForegroundColor Green
