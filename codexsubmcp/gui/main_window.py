from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QListWidget, QMainWindow, QSplitter, QStackedWidget

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.config import load_config
from codexsubmcp.gui.pages.cleanup_page import CleanupPage
from codexsubmcp.gui.pages.config_page import ConfigPage
from codexsubmcp.gui.pages.log_page import LogPage
from codexsubmcp.gui.pages.mcp_page import McpPage
from codexsubmcp.gui.pages.overview_page import OverviewPage
from codexsubmcp.gui.pages.task_page import TaskPage
from codexsubmcp.gui.task_runner import TaskRunner
from codexsubmcp.platform.windows.tasks import DEFAULT_TASK_NAME, TaskStatus

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
        resolved_config_path = config_path or ensure_runtime_config()
        resolved_config = config or load_config(runtime_path=resolved_config_path)
        resolved_inventory = inventory or {"configured": [], "installed_candidates": []}
        resolved_log_dir = log_dir or build_runtime_paths().logs
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
        self.cleanup_page = CleanupPage()
        self.task_page = TaskPage(self.task_status)
        self.config_page = ConfigPage(config=resolved_config, config_path=resolved_config_path)
        self.mcp_page = McpPage(inventory=resolved_inventory)
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
