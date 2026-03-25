from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

from codexsubmcp.gui.main_window import MainWindow
from codexsubmcp.platform.windows.tasks import TaskStatus


class FakeTaskRunner:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    def dispatch(self, command: str, **payload: object) -> None:
        self.requests.append((command, payload))


def test_main_window_shows_all_navigation_sections(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    labels = [window.nav_list.item(index).text() for index in range(window.nav_list.count())]

    assert labels == ["总览", "清理", "计划任务", "配置", "MCP 检索", "日志"]


def test_overview_preview_button_dispatches_dry_run(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.overview_page.preview_button, Qt.LeftButton)

    assert runner.requests == [("dry-run", {"headless": False})]


def test_task_page_renders_task_status_summary(qtbot):
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        task_status=TaskStatus(
            task_name="CodexSubMcpWatchdog",
            installed=True,
            enabled=False,
            executable_path=Path("C:/Tools/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        ),
    )
    qtbot.addWidget(window)

    summary = window.task_page.status_label.text()

    assert "已安装" in summary
    assert "已禁用" in summary
