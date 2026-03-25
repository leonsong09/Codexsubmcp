from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.install_codex_mcp_watchdog import PROJECT_ROOT, resolve_project_python


def _run_step(
    command: list[str],
    *,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = runner(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}")


def run_setup(
    *,
    project_root: Path,
    bootstrap_python: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    try:
        project_python = resolve_project_python(project_root)
    except FileNotFoundError:
        venv_dir = project_root / "venv"
        _run_step(
            [str(bootstrap_python), "-m", "venv", str(venv_dir)],
            cwd=project_root,
            runner=runner,
        )
        project_python = venv_dir / "Scripts" / "python.exe"

    cleanup_script = project_root / "tools" / "cleanup_codex_mcp_orphans.py"
    install_script = project_root / "tools" / "install_codex_mcp_watchdog.py"
    commands = [
        [str(project_python), "-m", "pip", "install", "-e", ".[dev]"],
        [str(project_python), str(cleanup_script)],
        [str(project_python), str(install_script)],
    ]
    for command in commands:
        _run_step(command, cwd=project_root, runner=runner)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="一键初始化 Codex MCP watchdog")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--bootstrap-python", type=Path, default=Path(sys.executable))
    args = parser.parse_args(argv)

    try:
        return run_setup(
            project_root=args.project_root.resolve(),
            bootstrap_python=args.bootstrap_python.resolve(),
        )
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
