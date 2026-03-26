from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.cleanup import run_cleanup
from codexsubmcp.core.config import DEFAULT_CONFIG, load_config
from codexsubmcp.core.mcp_inventory import build_inventory
from codexsubmcp.gui.app import launch_gui
from codexsubmcp.platform.windows.install_artifact import STABLE_EXE_NAME, install_current_executable
from codexsubmcp.platform.windows.processes import load_windows_processes
from codexsubmcp.platform.windows.mcp_sources import (
    discover_config_paths,
    scan_configured_sources,
    scan_npm_global_packages,
    scan_path_candidates,
    scan_python_candidates,
)
from codexsubmcp.platform.windows.tasks import (
    DEFAULT_TASK_NAME,
    get_task_status,
    register_task,
    set_task_enabled,
    unregister_task,
)


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


def _run_cleanup_command(
    command_name: str,
    *,
    config_path: Path | None,
    dry_run: bool,
    headless: bool,
    report_file: Path | None = None,
) -> int:
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
        if report_file is not None:
            report_file.parent.mkdir(parents=True, exist_ok=True)
            report_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    print(f"发现 {payload['suite_count']} 套候选 MCP，其中需要清理 {payload['cleanup_target_count']} 套。")
    for action in report.actions:
        print(f"- {action}")
    if not report.actions:
        print("未发现需要清理的超额孤儿套件。")
    return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    return launch_gui()


def _cmd_dry_run(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "dry-run",
        config_path=args.config,
        dry_run=True,
        headless=args.headless,
        report_file=args.report_file,
    )


def _cmd_cleanup(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "cleanup",
        config_path=args.config,
        dry_run=not args.yes,
        headless=args.headless,
        report_file=args.report_file,
    )


def _cmd_run_once(args: argparse.Namespace) -> int:
    return _run_cleanup_command(
        "run-once",
        config_path=args.config,
        dry_run=False,
        headless=args.headless,
        report_file=args.report_file,
    )


def _cmd_task(_args: argparse.Namespace) -> int:
    return 0


def _cmd_scan(_args: argparse.Namespace) -> int:
    return 0


def _cmd_scan_mcp(args: argparse.Namespace) -> int:
    payload = build_inventory(
        configured=scan_configured_sources(args.config_paths),
        installed_candidates=[
            *scan_npm_global_packages(),
            *scan_path_candidates(),
            *scan_python_candidates(),
        ],
    )
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    print(payload)
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


def _task_status_to_dict(task_status) -> dict[str, object]:
    return {
        "task_name": task_status.task_name,
        "installed": task_status.installed,
        "enabled": task_status.enabled,
        "executable_path": str(task_status.executable_path) if task_status.executable_path else None,
        "arguments": task_status.arguments,
        "interval_minutes": task_status.interval_minutes,
        "next_run_time": task_status.next_run_time,
    }


def _default_executable_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return build_runtime_paths().bin_dir / STABLE_EXE_NAME


def _cmd_task_install(args: argparse.Namespace) -> int:
    source_path = args.executable_path or _default_executable_path()
    installed_path = install_current_executable(source_path)
    output = register_task(
        task_name=args.task_name,
        executable_path=installed_path,
        interval_minutes=args.interval,
    )
    print(output)
    return 0


def _cmd_task_uninstall(args: argparse.Namespace) -> int:
    print(unregister_task(task_name=args.task_name))
    return 0


def _cmd_task_status(args: argparse.Namespace) -> int:
    status = get_task_status(task_name=args.task_name)
    payload = _task_status_to_dict(status)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    print(payload)
    return 0


def _cmd_task_enable(args: argparse.Namespace) -> int:
    print(set_task_enabled(task_name=args.task_name, enabled=True))
    return 0


def _cmd_task_disable(args: argparse.Namespace) -> int:
    print(set_task_enabled(task_name=args.task_name, enabled=False))
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
        command_parser.add_argument("--report-file", type=Path)
        if name == "cleanup":
            command_parser.add_argument("--yes", action="store_true")
        command_parser.set_defaults(func=func)

    task_parser = subparsers.add_parser("task")
    task_subparsers = task_parser.add_subparsers(dest="task_command")

    task_install_parser = task_subparsers.add_parser("install")
    task_install_parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    task_install_parser.add_argument("--executable-path", type=Path)
    task_install_parser.add_argument("--interval", type=int, default=10)
    task_install_parser.set_defaults(func=_cmd_task_install)

    task_uninstall_parser = task_subparsers.add_parser("uninstall")
    task_uninstall_parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    task_uninstall_parser.set_defaults(func=_cmd_task_uninstall)

    task_status_parser = task_subparsers.add_parser("status")
    task_status_parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    task_status_parser.add_argument("--format", choices=["json"], default="json")
    task_status_parser.set_defaults(func=_cmd_task_status)

    task_enable_parser = task_subparsers.add_parser("enable")
    task_enable_parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    task_enable_parser.set_defaults(func=_cmd_task_enable)

    task_disable_parser = task_subparsers.add_parser("disable")
    task_disable_parser.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    task_disable_parser.set_defaults(func=_cmd_task_disable)

    scan_parser = subparsers.add_parser("scan")
    scan_subparsers = scan_parser.add_subparsers(dest="scan_command")

    scan_mcp_parser = scan_subparsers.add_parser("mcp")
    scan_mcp_parser.add_argument("--format", choices=["json"], default="json")
    scan_mcp_parser.add_argument("--config-path", dest="config_paths", type=Path, action="append")
    scan_mcp_parser.set_defaults(func=_cmd_scan_mcp)

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
    resolved_argv = tuple(sys.argv[1:] if argv is None else argv)
    if not resolved_argv:
        return launch_gui()
    parser = build_parser()
    args = parser.parse_args(resolved_argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)
