from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codexsubmcp.core.cleanup import (
    build_candidate_suites,
    cleanup_suites,
    run_cleanup,
    select_cleanup_suites,
)
from codexsubmcp.core.config import DEFAULT_CONFIG, load_config
from codexsubmcp.core.models import ProcessInfo, ProcessSuite
from codexsubmcp.platform.windows.processes import (
    build_process_query_command,
    load_windows_processes,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXAMPLE_CONFIG = PROJECT_ROOT / "tools" / "codex_mcp_watchdog.example.json"
DEFAULT_RUNTIME_CONFIG = PROJECT_ROOT / "temp" / "codex_mcp_watchdog" / "config.json"


def _load_config(config_path: Path) -> dict[str, object]:
    return load_config(runtime_path=config_path, example_path=DEFAULT_EXAMPLE_CONFIG)


def _run_taskkill(pid: int) -> None:
    result = subprocess.run(
        ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"taskkill failed for {pid}")


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="清理 Codex subagent 泄漏的 MCP 孤儿套件")
    parser.add_argument("--config", type=Path, default=DEFAULT_RUNTIME_CONFIG, help="本地配置路径")
    parser.add_argument("--yes", action="store_true", help="真正执行清理；默认仅预览")
    args = parser.parse_args(argv)

    report = run_cleanup(
        load_windows_processes(),
        config=_load_config(args.config),
        dry_run=not args.yes,
        kill_runner=_run_taskkill,
    )
    print(f"发现 {len(report.suites)} 套候选 MCP，其中需要清理 {len(report.cleanup_targets)} 套。")
    for action in report.actions:
        print(f"- {action}")
    if not report.actions:
        print("未发现需要清理的超额孤儿套件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
