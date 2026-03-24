$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    throw "Project virtualenv Python was not found. Create venv or .venv first."
}

$ConfigPath = Join-Path $ProjectRoot "temp\codex_mcp_watchdog\config.json"
$LogDir = Join-Path $ProjectRoot "temp\codex_mcp_watchdog\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("watchdog-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
$ScriptPath = Join-Path $ProjectRoot "tools\cleanup_codex_mcp_orphans.py"

& $Python $ScriptPath --config $ConfigPath --yes *>> $LogFile
exit $LASTEXITCODE
