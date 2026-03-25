from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Sequence

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.cleanup import run_cleanup
from codexsubmcp.core.config import DEFAULT_CONFIG, load_config
from codexsubmcp.platform.windows.processes import load_windows_processes


def _run_taskkill(pid: int) -> None:
    result = subprocess.run(
        ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"taskkill failed for {pid}")


def _resolve_config_path(config_path: Path | None) -> Path:
    if config_path is not None:
        return config_path
    return ensure_runtime_config()


def _write_runtime_log(command_name: str, payload: dict[str, object]) -> Path:
    paths = build_runtime_paths()
    paths.logs.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = paths.logs / f"{command_name}-{timestamp}.json"
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return log_path


def _report_payload(command_name: str, *, dry_run: bool, report) -> dict[str, object]:
    return {
        "command": command_name,
        "dry_run": dry_run,
        "suite_count": len(report.suites),
        "cleanup_target_count": len(report.cleanup_targets),
        "actions": report.actions,
    }


def _run_cleanup_command(command_name: str, *, config_path: Path | None, dry_run: bool, headless: bool) -> int:
    config = load_config(runtime_path=_resolve_config_path(config_path))
    report = run_cleanup(
        load_windows_processes(),
        config=config,
        dry_run=dry_run,
        kill_runner=_run_taskkill,
    )
    payload = _report_payload(command_name, dry_run=dry_run, report=report)
    if headless:
        payload["log_path"] = str(_write_runtime_log(command_name, payload))
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    print(f"发现 {payload['suite_count']} 套候选 MCP，其中需要清理 {payload['cleanup_target_count']} 套。")
    for action in report.actions:
        print(f"- {action}")
    if not report.actions:
        print("未发现需要清理的超额孤儿套件。")
    return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    return 0


def _cmd_dry_run(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "dry-run",
        config_path=args.config,
        dry_run=True,
        headless=args.headless,
    )


def _cmd_cleanup(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "cleanup",
        config_path=args.config,
        dry_run=not args.yes,
        headless=args.headless,
    )


def _cmd_run_once(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "run-once",
        config_path=args.config,
        dry_run=False,
        headless=args.headless,
    )


def _cmd_task(_args: argparse.Namespace) -> int:
    return 0


def _cmd_scan(_args: argparse.Namespace) -> int:
    return 0


def _cmd_config_validate(args: argparse.Namespace) -> int:
    load_config(runtime_path=_resolve_config_path(args.config))
    print("valid")
    return 0


def _cmd_config_reset(args: argparse.Namespace) -> int:
    config_path = _resolve_config_path(args.config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(config_path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodexSubMcp desktop manager")
    subparsers = parser.add_subparsers(dest="command")

    gui_parser = subparsers.add_parser("gui")
    gui_parser.set_defaults(func=_cmd_gui)

    for name, func in (("dry-run", _cmd_dry_run), ("cleanup", _cmd_cleanup), ("run-once", _cmd_run_once)):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--config", type=Path)
        command_parser.add_argument("--headless", action="store_true")
        if name == "cleanup":
            command_parser.add_argument("--yes", action="store_true")
        command_parser.set_defaults(func=func)

    task_parser = subparsers.add_parser("task")
    task_parser.set_defaults(func=_cmd_task)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.set_defaults(func=_cmd_scan)

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    validate_parser = config_subparsers.add_parser("validate")
    validate_parser.add_argument("--config", type=Path)
    validate_parser.set_defaults(func=_cmd_config_validate)

    reset_parser = config_subparsers.add_parser("reset")
    reset_parser.add_argument("--config", type=Path)
    reset_parser.set_defaults(func=_cmd_config_reset)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
