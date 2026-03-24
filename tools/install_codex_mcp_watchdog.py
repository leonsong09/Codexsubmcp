from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_ENV_DIRNAME = "venv"
COMPAT_ENV_DIRNAME = ".venv"
PYTHON_PATH_SUFFIXES = (Path("Scripts/python.exe"), Path("bin/python"))
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "tools" / "codex_mcp_watchdog.example.json"
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "temp" / "codex_mcp_watchdog" / "config.json"
RUNNER_SCRIPT_PATH = PROJECT_ROOT / "tools" / "run_codex_mcp_watchdog.ps1"


def _find_python_in_env(env_dir: Path) -> Path | None:
    for suffix in PYTHON_PATH_SUFFIXES:
        candidate = env_dir / suffix
        if candidate.exists():
            return candidate
    return None


def resolve_project_python(project_root: Path) -> Path:
    for env_name in (CANONICAL_ENV_DIRNAME, COMPAT_ENV_DIRNAME):
        candidate = _find_python_in_env(project_root / env_name)
        if candidate is not None:
            return candidate
    raise FileNotFoundError("未找到项目虚拟环境 Python，请先创建 venv 或 .venv。")


def ensure_runtime_config(example_path: Path, runtime_path: Path) -> bool:
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    if runtime_path.exists():
        return False
    shutil.copyfile(example_path, runtime_path)
    return True


def build_register_task_script(
    *,
    task_name: str,
    runner_script_path: Path,
    interval_minutes: int,
) -> str:
    escaped_runner = str(runner_script_path).replace("'", "''")
    escaped_task_name = task_name.replace("'", "''")
    return f"""
$taskName = '{escaped_task_name}'
$runner = '{escaped_runner}'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$repeatTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {interval_minutes}) -RepetitionDuration (New-TimeSpan -Days 3650)
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logonTrigger, $repeatTrigger) -Description 'Codex subagent MCP watchdog' -Force | Out-Null
Write-Output "REGISTERED:$taskName"
""".strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装 Codex MCP watchdog 计划任务")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--task-name", default="CodexSubMcpWatchdog")
    parser.add_argument("--interval-minutes", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        python_path = resolve_project_python(args.project_root)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    created = ensure_runtime_config(
        args.project_root / "tools" / "codex_mcp_watchdog.example.json",
        args.project_root / "temp" / "codex_mcp_watchdog" / "config.json",
    )
    script = build_register_task_script(
        task_name=args.task_name,
        runner_script_path=args.project_root / "tools" / "run_codex_mcp_watchdog.ps1",
        interval_minutes=args.interval_minutes,
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip() or "[ERROR] 注册计划任务失败", file=sys.stderr)
        return result.returncode or 1

    print(f"Python: {python_path}")
    print(f"Config: {'created' if created else 'kept'}")
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

