from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QListWidget, QMainWindow, QSplitter, QStackedWidget

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.cleanup import run_cleanup
from codexsubmcp.core.config import load_config
from codexsubmcp.core.mcp_inventory import build_inventory
from codexsubmcp.gui.pages.cleanup_page import CleanupPage
from codexsubmcp.gui.pages.config_page import ConfigPage
from codexsubmcp.gui.pages.log_page import LogPage
from codexsubmcp.gui.pages.mcp_page import McpPage
from codexsubmcp.gui.pages.overview_page import OverviewPage
from codexsubmcp.gui.pages.task_page import TaskPage
from codexsubmcp.gui.task_runner import TaskRunner
from codexsubmcp.platform.windows.install_artifact import STABLE_EXE_NAME, install_current_executable
from codexsubmcp.platform.windows.mcp_sources import (
    scan_configured_sources,
    scan_npm_global_packages,
    scan_path_candidates,
    scan_python_candidates,
)
from codexsubmcp.platform.windows.processes import load_windows_processes
from codexsubmcp.platform.windows.tasks import (
    DEFAULT_TASK_NAME,
    TaskStatus,
    get_task_status,
    register_task,
    set_task_enabled,
    unregister_task,
)

class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        task_runner: TaskRunner | object | None = None,
        task_status: TaskStatus | None = None,
        config: dict[str, object] | None = None,
        config_path: Path | None = None,
        inventory: dict[str, list[dict[str, object]]] | None = None,
        log_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("CodexSubMcp Manager")
        self.resize(1080, 720)

        self.task_runner = task_runner or TaskRunner()
        if hasattr(self.task_runner, "requested"):
            self.task_runner.requested.connect(self._handle_request)
        resolved_config_path = config_path or ensure_runtime_config()
        resolved_config = config or load_config(runtime_path=resolved_config_path)
        resolved_inventory = inventory or {"configured": [], "installed_candidates": []}
        resolved_log_dir = log_dir or build_runtime_paths().logs
        self.config_path = resolved_config_path
        self.log_dir = resolved_log_dir
        self.task_status = task_status or TaskStatus(
            task_name=DEFAULT_TASK_NAME,
            installed=False,
            enabled=None,
            executable_path=None,
            arguments=None,
        )

        self.nav_list = QListWidget()
        self.nav_list.addItems(["总览", "清理", "计划任务", "配置", "MCP 检索", "日志"])

        self.stack = QStackedWidget()
        self.overview_page = OverviewPage(self.task_runner)
        self.cleanup_page = CleanupPage(self.task_runner)
        self.task_page = TaskPage(self.task_status, self.task_runner)
        self.config_page = ConfigPage(config=resolved_config, config_path=resolved_config_path)
        self.mcp_page = McpPage(inventory=resolved_inventory, task_runner=self.task_runner)
        self.log_page = LogPage(log_dir=resolved_log_dir)

        for page in (
            self.overview_page,
            self.cleanup_page,
            self.task_page,
            self.config_page,
            self.mcp_page,
            self.log_page,
        ):
            self.stack.addWidget(page)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

    def _default_install_source(self) -> Path | None:
        if getattr(sys, "frozen", False):
            return Path(sys.executable)
        project_root = Path(__file__).resolve().parents[2]
        bundled_exe = project_root / "dist" / STABLE_EXE_NAME
        if bundled_exe.exists():
            return bundled_exe
        return None

    def _refresh_task_status(self) -> None:
        self.task_status = get_task_status(task_name=DEFAULT_TASK_NAME)
        self.task_page.set_task_status(self.task_status)

    def _refresh_inventory(self) -> None:
        inventory = build_inventory(
            configured=scan_configured_sources(),
            installed_candidates=[
                *scan_npm_global_packages(),
                *scan_path_candidates(),
                *scan_python_candidates(),
            ],
        )
        self.mcp_page.set_inventory(inventory)

    def _run_cleanup(self, *, dry_run: bool) -> None:
        config = load_config(runtime_path=self.config_path)
        report = run_cleanup(
            load_windows_processes(),
            config=config,
            dry_run=dry_run,
            kill_runner=self._run_taskkill,
        )
        summary = (
            f"候选 {len(report.suites)} 套，需要处理 {len(report.cleanup_targets)} 套。"
        )
        if report.actions:
            summary = f"{summary} {'; '.join(report.actions)}"
        self.cleanup_page.set_summary(summary)

    @staticmethod
    def _run_taskkill(pid: int) -> None:
        import subprocess

        result = subprocess.run(
            ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"taskkill failed for {pid}")

    def _handle_request(self, command: str, payload: dict) -> None:
        if command == "dry-run":
            self._run_cleanup(dry_run=True)
            return
        if command == "cleanup":
            self._run_cleanup(dry_run=False)
            return
        if command == "task-status":
            self._refresh_task_status()
            return
        if command == "task-install":
            source = self._default_install_source()
            if source is None:
                self.task_page.status_label.setText("未找到可安装的 GUI 可执行文件")
                return
            installed_path = install_current_executable(source)
            register_task(task_name=DEFAULT_TASK_NAME, executable_path=installed_path, interval_minutes=10)
            self._refresh_task_status()
            return
        if command == "task-uninstall":
            unregister_task(task_name=DEFAULT_TASK_NAME)
            self._refresh_task_status()
            return
        if command == "task-enable":
            set_task_enabled(task_name=DEFAULT_TASK_NAME, enabled=True)
            self._refresh_task_status()
            return
        if command == "task-disable":
            set_task_enabled(task_name=DEFAULT_TASK_NAME, enabled=False)
            self._refresh_task_status()
            return
        if command == "scan-mcp":
            self._refresh_inventory()
