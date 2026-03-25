from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from codexsubmcp.gui.pages.cleanup_page import CleanupPage
from codexsubmcp.gui.pages.overview_page import OverviewPage
from codexsubmcp.gui.pages.task_page import TaskPage
from codexsubmcp.gui.task_runner import TaskRunner
from codexsubmcp.platform.windows.tasks import DEFAULT_TASK_NAME, TaskStatus


def _placeholder_page(title: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout()
    layout.addWidget(QLabel(title))
    layout.addStretch(1)
    widget.setLayout(layout)
    return widget


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        task_runner: TaskRunner | object | None = None,
        task_status: TaskStatus | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("CodexSubMcp Manager")
        self.resize(1080, 720)

        self.task_runner = task_runner or TaskRunner()
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
        self.config_page = _placeholder_page("配置")
        self.mcp_page = _placeholder_page("MCP 检索")
        self.log_page = _placeholder_page("日志")

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
