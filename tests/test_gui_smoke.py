from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt

from codexsubmcp.gui.main_window import MainWindow
from codexsubmcp.core.config import DEFAULT_CONFIG
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


def test_config_page_loads_current_config_and_blocks_invalid_save(qtbot, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        config=DEFAULT_CONFIG,
        config_path=config_path,
    )
    qtbot.addWidget(window)

    assert '"max_suites": 6' in window.config_page.editor.toPlainText()

    window.config_page.editor.setPlainText(json.dumps({**DEFAULT_CONFIG, "max_suites": 0}))
    qtbot.mouseClick(window.config_page.save_button, Qt.LeftButton)

    assert "max_suites" in window.config_page.error_label.text()
    assert json.loads(config_path.read_text(encoding="utf-8"))["max_suites"] == 6


def test_mcp_page_splits_configured_and_candidate_records(qtbot):
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        inventory={
            "configured": [{"name": "memory"}],
            "installed_candidates": [{"name": "@modelcontextprotocol/server-filesystem"}],
        },
    )
    qtbot.addWidget(window)

    assert window.mcp_page.configured_list.count() == 1
    assert window.mcp_page.installed_list.count() == 1


def test_log_page_lists_files_and_shows_selected_content(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "watchdog.log").write_text("hello log", encoding="utf-8")
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)

    window.log_page.log_list.setCurrentRow(0)

    assert window.log_page.log_list.count() == 1
    assert "hello log" in window.log_page.detail_view.toPlainText()


def test_cleanup_page_buttons_dispatch_preview_and_cleanup(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.cleanup_page.preview_button, Qt.LeftButton)
    qtbot.mouseClick(window.cleanup_page.cleanup_button, Qt.LeftButton)

    assert runner.requests == [
        ("dry-run", {"headless": False}),
        ("cleanup", {"headless": False, "yes": True}),
    ]


def test_task_page_buttons_dispatch_management_actions(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.task_page.install_button, Qt.LeftButton)
    qtbot.mouseClick(window.task_page.disable_button, Qt.LeftButton)
    qtbot.mouseClick(window.task_page.refresh_button, Qt.LeftButton)

    assert runner.requests == [
        ("task-install", {}),
        ("task-disable", {}),
        ("task-status", {}),
    ]


def test_real_window_updates_task_status_after_refresh(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window.task_page.refresh_button, Qt.LeftButton)

    summary = window.task_page.status_label.text()
    assert "CodexSubMcpWatchdog" in summary


def test_mcp_page_refresh_button_dispatches_scan(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.mcp_page.refresh_button, Qt.LeftButton)

    assert runner.requests == [("scan-mcp", {})]
