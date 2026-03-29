from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.cleanup import build_cleanup_preview, execute_cleanup_preview
from codexsubmcp.core.config import DEFAULT_CONFIG, load_config
from codexsubmcp.core.mcp_inventory import build_inventory
from codexsubmcp.core.recognition import validate_parent_recognition
from codexsubmcp.core.runtime_logs import (
    write_cleanup_log,
    write_preview_log,
    write_refresh_log,
)
from codexsubmcp.core.system_snapshot import build_system_snapshot
from codexsubmcp.gui.app import launch_gui
from codexsubmcp.platform.windows.install_artifact import STABLE_EXE_NAME, install_current_executable
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


def _write_report_file(report_file: Path | None, payload: dict[str, object]) -> None:
    if report_file is None:
        return
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _payload_from_log(log_path: Path) -> dict[str, object]:
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    payload["log_path"] = str(log_path)
    return payload


def _build_snapshot_and_analysis(config_path: Path | None) -> tuple[dict[str, object], object, object, object]:
    config = load_config(runtime_path=_resolve_config_path(config_path))
    snapshot = build_system_snapshot()
    analysis = analyze_snapshot(snapshot, config=config)
    recognition = validate_parent_recognition(snapshot, analysis, config)
    return config, snapshot, analysis, recognition


def _emit_headless_payload(payload: dict[str, object], report_file: Path | None) -> int:
    _write_report_file(report_file, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    return launch_gui()


def _cmd_refresh(args: argparse.Namespace) -> int:
    _config, snapshot, analysis, recognition = _build_snapshot_and_analysis(args.config)
    log_path = write_refresh_log(snapshot=snapshot, analysis=analysis, recognition=recognition)
    payload = _payload_from_log(log_path)
    if args.headless:
        return _emit_headless_payload(payload, args.report_file)
    print(payload)
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    _config, _snapshot, analysis, recognition = _build_snapshot_and_analysis(args.config)
    if not recognition.trusted:
        raise RuntimeError(recognition.reason)
    preview = build_cleanup_preview(analysis)
    log_path = write_preview_log(preview=preview)
    payload = _payload_from_log(log_path)
    if args.headless:
        return _emit_headless_payload(payload, args.report_file)
    print(payload)
    return 0


def _cmd_cleanup(args: argparse.Namespace) -> int:
    if not args.yes:
        return _cmd_preview(args)
    _config, _snapshot, analysis, recognition = _build_snapshot_and_analysis(args.config)
    if not recognition.trusted:
        raise RuntimeError(recognition.reason)
    preview = build_cleanup_preview(analysis)
    result = execute_cleanup_preview(
        preview,
        kill_runner=_run_taskkill,
    )
    log_path = write_cleanup_log(result=result)
    payload = _payload_from_log(log_path)
    if args.headless:
        return _emit_headless_payload(payload, args.report_file)
    print(payload)
    return 0


def _cmd_run_once(args: argparse.Namespace) -> int:
    args.yes = True
    return _cmd_cleanup(args)


def _cmd_task(_args: argparse.Namespace) -> int:
    return 0


def _cmd_scan(_args: argparse.Namespace) -> int:
    return 0


def _cmd_scan_mcp(args: argparse.Namespace) -> int:
    _config, snapshot, analysis, _recognition = _build_snapshot_and_analysis(getattr(args, "config", None))
    payload = build_inventory(
        configured=list(snapshot.configured_mcps),
        running=list(analysis.running_mcps),
        drift={
            "configured_not_running": list(analysis.configured_not_running),
            "running_not_configured": list(analysis.running_not_configured),
        },
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

    for name, func in (
        ("refresh", _cmd_refresh),
        ("preview", _cmd_preview),
        ("dry-run", _cmd_preview),
        ("cleanup", _cmd_cleanup),
        ("run-once", _cmd_run_once),
    ):
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
