$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/ and run setup again."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js is required. Install the current LTS release and run setup again."
}

Write-Host "Installing Elena and optional local providers..."
uv sync --extra dev --extra providers --extra desktop --extra voice

Write-Host "Building the browser interface..."
Push-Location apps/ui
try {
    npm ci
    npm run build
}
finally {
    Pop-Location
}

Write-Host "Preparing speech models. This is the only long first-run download..."
uv run --extra voice elena-voice-setup

Write-Host "Running Elena's local checks..."
uv run pytest
uv run ruff check src tests

Write-Host "Setup complete. Double-click Start-Elena.cmd."