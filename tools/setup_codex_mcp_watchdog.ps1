$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $PythonCommand) {
        throw "python.exe was not found. Install Python first."
    }
    $Python = $PythonCommand.Source
}

$Setup = Join-Path $ProjectRoot "tools\setup_codex_mcp_watchdog.py"
& $Python $Setup
exit $LASTEXITCODE
