from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Sequence

from codexsubmcp.app_paths import build_runtime_paths
from codexsubmcp.platform.windows.install_artifact import STABLE_EXE_NAME
from codexsubmcp.platform.windows.tasks import build_register_task_script as build_task_script
from codexsubmcp.platform.windows.tasks import register_task


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_ENV_DIRNAME = "venv"
COMPAT_ENV_DIRNAME = ".venv"
PYTHON_PATH_SUFFIXES = (Path("Scripts/python.exe"), Path("bin/python"))
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "tools" / "codex_mcp_watchdog.example.json"
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "temp" / "codex_mcp_watchdog" / "config.json"


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
    executable_path: Path,
    interval_minutes: int,
) -> str:
    return build_task_script(
        task_name=task_name,
        executable_path=executable_path,
        interval_minutes=interval_minutes,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装 Codex MCP watchdog 计划任务")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--task-name", default="CodexSubMcpWatchdog")
    parser.add_argument("--interval-minutes", type=int, default=10)
    parser.add_argument("--executable-path", type=Path)
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
    executable_path = args.executable_path or (build_runtime_paths().bin_dir / STABLE_EXE_NAME)
    try:
        output = register_task(
            task_name=args.task_name,
            executable_path=executable_path,
            interval_minutes=args.interval_minutes,
        )
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"Python: {python_path}")
    print(f"Config: {'created' if created else 'kept'}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

