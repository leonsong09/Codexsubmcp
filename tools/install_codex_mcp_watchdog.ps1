$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    throw "Project virtualenv Python was not found. Create venv or .venv first."
}

$Installer = Join-Path $ProjectRoot "tools\install_codex_mcp_watchdog.py"
& $Python $Installer
exit $LASTEXITCODE
