from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QFileDialog

from codexsubmcp.gui.main_window import MainWindow
from codexsubmcp.core.config import DEFAULT_CONFIG
from codexsubmcp.core.models import ProcessInfo
from codexsubmcp.platform.windows.tasks import TaskStatus


class FakeTaskRunner:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    def dispatch(self, command: str, **payload: object) -> None:
        self.requests.append((command, payload))


def _proc(
    pid: int,
    ppid: int,
    name: str,
    created_at: str,
    command_line: str,
) -> ProcessInfo:
    return ProcessInfo(
        pid=pid,
        ppid=ppid,
        name=name,
        created_at=datetime.fromisoformat(created_at),
        command_line=command_line,
    )


def test_main_window_shows_all_navigation_sections(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    labels = [window.nav_list.item(index).text() for index in range(window.nav_list.count())]

    assert labels == ["总览", "清理", "计划任务", "配置", "MCP 检索", "日志"]


def test_main_window_applies_shell_theme_hooks(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    assert window.objectName() == "shellRoot"
    assert window.nav_list.objectName() == "navList"
    assert window.activity_drawer.objectName() == "activityDrawer"
    assert "#shellRoot" in QApplication.instance().styleSheet()


def test_main_window_has_top_status_bar_and_toggleable_activity_drawer(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    assert "总览" in window.top_page_label.text()
    assert "CodexSubMcpWatchdog" in window.top_status_label.text()
    assert str(window.log_dir) in window.top_path_label.text()
    assert window.activity_drawer.isHidden()

    qtbot.mouseClick(window.activity_toggle_button, Qt.LeftButton)
    assert not window.activity_drawer.isHidden()

    qtbot.mouseClick(window.activity_toggle_button, Qt.LeftButton)
    assert window.activity_drawer.isHidden()


def test_main_window_activity_drawer_records_lifecycle_events(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    window._handle_started("scan-mcp")
    window._handle_succeeded("scan-mcp", {"configured": [{"name": "memory"}], "installed_candidates": []})
    window._handle_failed("task-install", "elevation failed")

    activity_text = window.activity_log_view.toPlainText()
    assert "START scan-mcp" in activity_text
    assert "SUCCESS scan-mcp" in activity_text
    assert "FAILED task-install" in activity_text
    assert "elevation failed" in activity_text
    assert "失败" in window.top_activity_label.text()


def test_overview_preview_button_dispatches_dry_run(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.overview_page.preview_button, Qt.LeftButton)

    assert runner.requests == [("dry-run", {"headless": False})]


def test_overview_page_shows_summaries_and_dispatches_quick_actions(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(
        task_runner=runner,
        task_status=TaskStatus(
            task_name="CodexSubMcpWatchdog",
            installed=True,
            enabled=True,
            executable_path=Path("C:/Tools/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        ),
        config=DEFAULT_CONFIG,
        inventory={
            "configured": [{"name": "memory"}],
            "installed_candidates": [{"name": "@modelcontextprotocol/server-filesystem"}],
        },
    )
    qtbot.addWidget(window)

    assert "已安装" in window.overview_page.task_summary_label.text()
    assert "max_suites=6" in window.overview_page.config_summary_label.text()
    assert "已配置 1" in window.overview_page.mcp_summary_label.text()
    assert "候选 1" in window.overview_page.mcp_summary_label.text()
    assert "管理员" in window.overview_page.cleanup_button.text()
    assert "管理员" in window.overview_page.task_button.text()

    qtbot.mouseClick(window.overview_page.preview_button, Qt.LeftButton)
    qtbot.mouseClick(window.overview_page.cleanup_button, Qt.LeftButton)
    qtbot.mouseClick(window.overview_page.task_button, Qt.LeftButton)
    qtbot.mouseClick(window.overview_page.scan_button, Qt.LeftButton)

    assert runner.requests == [
        ("dry-run", {"headless": False}),
        ("cleanup", {"headless": False, "yes": True}),
        ("task-install", {"interval": 10}),
        ("scan-mcp", {}),
    ]


def test_task_page_renders_task_status_summary(qtbot):
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        task_status=TaskStatus(
            task_name="CodexSubMcpWatchdog",
            installed=True,
            enabled=False,
            executable_path=Path("C:/Tools/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
            interval_minutes=15,
            next_run_time="2026-03-26T10:30:00",
        ),
    )
    qtbot.addWidget(window)

    summary = window.task_page.status_label.text()

    assert "已安装" in summary
    assert "已禁用" in summary
    assert "15 分钟" in window.task_page.interval_label.text()
    assert "2026-03-26T10:30:00" in window.task_page.next_run_label.text()
    assert "重装" in window.task_page.reinstall_button.text()
    assert "管理员" in window.task_page.install_button.text()
    assert "管理员" in window.task_page.reinstall_button.text()
    assert "管理员" in window.task_page.uninstall_button.text()
    assert "管理员" in window.task_page.enable_button.text()
    assert "管理员" in window.task_page.disable_button.text()


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

    window.config_page.mode_tabs.setCurrentIndex(1)
    window.config_page.editor.setPlainText(json.dumps({**DEFAULT_CONFIG, "max_suites": 0}))
    qtbot.mouseClick(window.config_page.save_button, Qt.LeftButton)

    assert "max_suites" in window.config_page.error_label.text()
    assert json.loads(config_path.read_text(encoding="utf-8"))["max_suites"] == 6


def test_config_page_can_validate_reset_import_and_export(qtbot, tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    export_path = tmp_path / "exports" / "config-export.json"
    import_path = tmp_path / "import.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    import_path.write_text(
        json.dumps({**DEFAULT_CONFIG, "max_suites": 9}, ensure_ascii=False),
        encoding="utf-8",
    )
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        config=DEFAULT_CONFIG,
        config_path=config_path,
        export_dir=tmp_path / "exports",
    )
    qtbot.addWidget(window)

    qtbot.mouseClick(window.config_page.validate_button, Qt.LeftButton)
    assert "配置有效" in window.config_page.error_label.text()

    window.config_page.editor.setPlainText(json.dumps({**DEFAULT_CONFIG, "max_suites": 1}))
    qtbot.mouseClick(window.config_page.reset_button, Qt.LeftButton)
    assert '"max_suites": 6' in window.config_page.editor.toPlainText()

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(import_path), "JSON Files (*.json)"),
    )
    qtbot.mouseClick(window.config_page.import_button, Qt.LeftButton)
    assert '"max_suites": 9' in window.config_page.editor.toPlainText()

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(export_path), "JSON Files (*.json)"),
    )
    qtbot.mouseClick(window.config_page.export_button, Qt.LeftButton)

    assert export_path.exists()
    assert json.loads(export_path.read_text(encoding="utf-8"))["max_suites"] == 9
    assert "已导出" in window.config_page.error_label.text()


def test_config_page_supports_form_and_json_modes(qtbot, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        config=DEFAULT_CONFIG,
        config_path=config_path,
    )
    qtbot.addWidget(window)

    assert window.config_page.mode_tabs.tabText(0) == "表单"
    assert window.config_page.mode_tabs.tabText(1) == "JSON"
    assert window.config_page.max_suites_input.value() == 6
    assert window.config_page.interval_minutes_input.value() == 10

    window.config_page.max_suites_input.setValue(8)
    window.config_page.interval_minutes_input.setValue(12)
    window.config_page.mode_tabs.setCurrentIndex(1)
    assert '"max_suites": 8' in window.config_page.editor.toPlainText()
    assert '"interval_minutes": 12' in window.config_page.editor.toPlainText()

    window.config_page.editor.setPlainText(
        json.dumps({**DEFAULT_CONFIG, "suite_window_seconds": 30}, ensure_ascii=False)
    )
    window.config_page.mode_tabs.setCurrentIndex(0)
    assert window.config_page.suite_window_seconds_input.value() == 30

    qtbot.mouseClick(window.config_page.save_button, Qt.LeftButton)
    assert json.loads(config_path.read_text(encoding="utf-8"))["suite_window_seconds"] == 30


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


def test_mcp_page_uses_two_tabs_for_configured_and_candidate_lists(qtbot):
    window = MainWindow(
        inventory={
            "configured": [{"name": "memory"}],
            "installed_candidates": [{"name": "@modelcontextprotocol/server-filesystem"}],
        }
    )
    qtbot.addWidget(window)

    assert window.mcp_page.result_tabs.count() == 2
    assert window.mcp_page.result_tabs.tabText(0) == "已配置可用"
    assert window.mcp_page.result_tabs.tabText(1) == "疑似已安装"


def test_cleanup_page_can_copy_and_export_suite_table(qtbot, tmp_path):
    export_dir = tmp_path / "exports"
    window = MainWindow(export_dir=export_dir)
    qtbot.addWidget(window)
    window.cleanup_page.set_report(
        {
            "suites": [
                {
                    "suite_id": "orphan-1",
                    "classification": "orphaned_after_codex_exit",
                    "root_pid": 210,
                    "process_count": 2,
                    "created_at": "2026-03-26T10:00:00",
                    "process_ids": [210, 211],
                }
            ],
            "cleanup_targets": ["orphan-1"],
            "actions": ["dry-run pid=210 processes=2"],
        }
    )

    qtbot.mouseClick(window.cleanup_page.copy_table_button, Qt.LeftButton)
    copied_text = QGuiApplication.clipboard().text()
    assert "orphan-1" in copied_text
    assert "Root PID" in copied_text

    qtbot.mouseClick(window.cleanup_page.export_table_button, Qt.LeftButton)
    exported = export_dir / "cleanup-suites.tsv"
    assert exported.exists()
    assert "orphan-1" in exported.read_text(encoding="utf-8")
    assert "已导出" in window.cleanup_page.summary_label.text()


def test_log_page_lists_files_and_shows_selected_content(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "watchdog.log").write_text("hello log", encoding="utf-8")
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)

    window.log_page.log_list.setCurrentRow(0)

    assert window.log_page.log_list.count() == 1
    assert "hello log" in window.log_page.detail_view.toPlainText()


def test_log_page_filters_by_action_and_status(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "dry-run-20260326-100000.json").write_text(
        json.dumps(
            {
                "command": "dry-run",
                "status": "success",
                "suite_count": 3,
                "cleanup_target_count": 1,
                "actions": ["dry-run pid=210 processes=2"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (log_dir / "cleanup-20260326-100500.json").write_text(
        json.dumps(
            {
                "command": "cleanup",
                "status": "failure",
                "suite_count": 2,
                "cleanup_target_count": 1,
                "actions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)

    assert window.log_page.log_list.count() == 2

    window.log_page.action_filter.setCurrentText("dry-run")
    assert window.log_page.log_list.count() == 1
    assert "dry-run" in window.log_page.log_list.item(0).text()

    window.log_page.action_filter.setCurrentText("全部动作")
    window.log_page.status_filter.setCurrentText("failure")
    assert window.log_page.log_list.count() == 1
    assert "cleanup" in window.log_page.log_list.item(0).text()


def test_log_page_can_export_selected_log(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    export_dir = tmp_path / "exports"
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "command": "run-once",
        "status": "success",
        "suite_count": 0,
        "cleanup_target_count": 0,
        "actions": [],
    }
    (log_dir / "run-once-20260326-101000.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir, export_dir=export_dir)
    qtbot.addWidget(window)

    window.log_page.log_list.setCurrentRow(0)
    qtbot.mouseClick(window.log_page.export_button, Qt.LeftButton)

    exported_path = export_dir / "run-once-20260326-101000.json"
    assert exported_path.exists()
    assert json.loads(exported_path.read_text(encoding="utf-8"))["command"] == "run-once"
    assert "已导出" in window.log_page.status_label.text()


def test_log_page_can_open_log_directory(qtbot, tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)
    seen: list[str] = []

    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: seen.append(url.toLocalFile()) or True,
    )

    qtbot.mouseClick(window.log_page.open_dir_button, Qt.LeftButton)

    assert [Path(item) for item in seen] == [log_dir]
    assert "已打开日志目录" in window.log_page.status_label.text()


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
    qtbot.mouseClick(window.task_page.reinstall_button, Qt.LeftButton)
    qtbot.mouseClick(window.task_page.disable_button, Qt.LeftButton)
    qtbot.mouseClick(window.task_page.refresh_button, Qt.LeftButton)

    assert runner.requests == [
        ("task-install", {"interval": 10}),
        ("task-install", {"interval": 10}),
        ("task-disable", {}),
        ("task-status", {}),
    ]


def test_main_window_uses_elevated_subprocess_for_task_install_when_not_admin(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    seen: list[tuple[Path, list[str]]] = []

    monkeypatch.setattr("codexsubmcp.gui.main_window.is_user_admin", lambda: False)
    monkeypatch.setattr(
        window,
        "_elevation_entrypoint",
        lambda: (Path("C:/Python312/python.exe"), ["-m", "codexsubmcp"]),
    )
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.run_elevated",
        lambda executable_path, arguments: seen.append((executable_path, list(arguments))) or 0,
    )
    monkeypatch.setattr(window, "_default_install_source", lambda: Path("C:/Downloads/CodexSubMcpManager.exe"))
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.get_task_status",
        lambda task_name: TaskStatus(
            task_name=task_name,
            installed=True,
            enabled=True,
            executable_path=Path("C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        ),
    )

    status = window._install_or_refresh(Path("C:/Downloads/CodexSubMcpManager.exe"), interval=15)

    assert status.installed is True
    assert seen[0][0] == Path("C:/Python312/python.exe")
    assert seen[0][1][:-1] == [
        "-m",
        "codexsubmcp",
        "task",
        "install",
        "--task-name",
        "CodexSubMcpWatchdog",
        "--interval",
        "15",
        "--executable-path",
    ]
    assert Path(seen[0][1][-1]) == Path("C:/Downloads/CodexSubMcpManager.exe")


def test_main_window_uses_elevated_subprocess_for_task_disable_when_not_admin(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    seen: list[tuple[Path, list[str]]] = []

    monkeypatch.setattr("codexsubmcp.gui.main_window.is_user_admin", lambda: False)
    monkeypatch.setattr(window, "_elevation_entrypoint", lambda: (Path("C:/Tools/CodexSubMcpManager.exe"), []))
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.run_elevated",
        lambda executable_path, arguments: seen.append((executable_path, list(arguments))) or 0,
    )
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.get_task_status",
        lambda task_name: TaskStatus(
            task_name=task_name,
            installed=True,
            enabled=False,
            executable_path=Path("C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        ),
    )

    status = window._disable_or_refresh()

    assert status.enabled is False
    assert seen == [
        (
            Path("C:/Tools/CodexSubMcpManager.exe"),
            ["task", "disable", "--task-name", "CodexSubMcpWatchdog"],
        )
    ]


def test_main_window_uses_elevated_subprocess_for_cleanup_when_not_admin(qtbot, monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    window = MainWindow(config=DEFAULT_CONFIG, config_path=config_path)
    qtbot.addWidget(window)
    seen: list[tuple[Path, list[str]]] = []

    monkeypatch.setattr("codexsubmcp.gui.main_window.is_user_admin", lambda: False)
    monkeypatch.setattr(
        window,
        "_elevation_entrypoint",
        lambda: (Path("C:/Python312/python.exe"), ["-m", "codexsubmcp"]),
    )

    def fake_run_elevated(executable_path: Path, arguments: list[str]) -> int:
        seen.append((executable_path, list(arguments)))
        report_path = Path(arguments[arguments.index("--report-file") + 1])
        report_path.write_text(
            json.dumps(
                {
                    "suites": [{"suite_id": "orphan-1"}],
                    "cleanup_targets": ["orphan-1"],
                    "actions": ["killed pid=210 processes=2"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr("codexsubmcp.gui.main_window.run_elevated", fake_run_elevated)

    payload = window._cleanup_or_report(dry_run=False)

    assert payload["cleanup_targets"] == ["orphan-1"]
    assert payload["actions"] == ["killed pid=210 processes=2"]
    assert seen[0][0] == Path("C:/Python312/python.exe")
    assert seen[0][1][:5] == ["-m", "codexsubmcp", "cleanup", "--yes", "--headless"]
    assert "--config" in seen[0][1]
    assert Path(seen[0][1][seen[0][1].index("--config") + 1]) == config_path
    assert "--report-file" in seen[0][1]


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


def test_cleanup_page_can_render_suite_summary_and_details(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.cleanup_page.set_report(
        {
            "suites": [
                {
                    "suite_id": "orphan-1",
                    "classification": "orphaned_after_codex_exit",
                    "root_pid": 210,
                    "process_count": 2,
                    "created_at": "2026-03-26T10:00:00",
                    "process_ids": [210, 211],
                    "reason": "未找到仍存活的 Codex 父进程，判定为孤儿套件。",
                    "risk_hint": "该套件会被清理，请确认没有仍在使用的终端会话。",
                    "command_summaries": ["agentation-mcp server", "node agentation-mcp"],
                    "processes": [
                        {
                            "pid": 210,
                            "ppid": 9999,
                            "name": "node.exe",
                            "command_line": "agentation-mcp server",
                        },
                        {
                            "pid": 211,
                            "ppid": 210,
                            "name": "node.exe",
                            "command_line": "node agentation-mcp",
                        },
                    ],
                }
            ],
            "cleanup_targets": ["orphan-1"],
            "actions": ["dry-run pid=210 processes=2"],
        }
    )

    headers = [
        window.cleanup_page.suite_table.horizontalHeaderItem(index).text()
        for index in range(window.cleanup_page.suite_table.columnCount())
    ]
    assert headers == ["Suite", "分类", "Root PID", "进程数", "创建时间", "动作"]
    assert window.cleanup_page.suite_table.rowCount() == 1
    assert window.cleanup_page.suite_table.item(0, 0).text() == "orphan-1"
    assert window.cleanup_page.suite_table.item(0, 5).text() == "会被清理"
    assert "root_pid=210" in window.cleanup_page.detail_view.toPlainText()
    assert "判定原因" in window.cleanup_page.detail_view.toPlainText()
    assert "风险提示" in window.cleanup_page.detail_view.toPlainText()
    assert "进程树" in window.cleanup_page.detail_view.toPlainText()
    assert "agentation-mcp server" in window.cleanup_page.detail_view.toPlainText()
    assert "dry-run pid=210 processes=2" in window.cleanup_page.summary_label.text()


def test_main_window_cleanup_payload_includes_rich_suite_details(qtbot, tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config = {**DEFAULT_CONFIG, "max_suites": 1, "candidate_patterns": ["agentation-mcp"]}
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.load_windows_processes",
        lambda: [
            _proc(210, 9999, "node.exe", "2026-03-24T09:00:00", "agentation-mcp server"),
            _proc(211, 210, "node.exe", "2026-03-24T09:00:01", "node agentation-mcp"),
            _proc(310, 9998, "node.exe", "2026-03-24T09:01:00", "agentation-mcp server"),
            _proc(311, 310, "node.exe", "2026-03-24T09:01:01", "node agentation-mcp"),
        ],
    )
    window = MainWindow(config=config, config_path=config_path)
    qtbot.addWidget(window)

    payload = window._run_cleanup(dry_run=True)
    suite = next(item for item in payload["suites"] if item["suite_id"] == payload["cleanup_targets"][0])

    assert suite["reason"]
    assert suite["risk_hint"]
    assert suite["command_summaries"] == ["agentation-mcp server", "node agentation-mcp"]
    assert suite["processes"][0]["pid"] == 210


def test_task_page_renders_executable_path_and_arguments(qtbot):
    window = MainWindow(
        task_status=TaskStatus(
            task_name="CodexSubMcpWatchdog",
            installed=True,
            enabled=True,
            executable_path=Path("C:/Users/test/AppData/Local/CodexSubMcpManager/bin/CodexSubMcpManager.exe"),
            arguments="run-once --headless",
        )
    )
    qtbot.addWidget(window)

    assert "CodexSubMcpManager.exe" in window.task_page.path_label.text()
    assert "run-once --headless" in window.task_page.arguments_label.text()
    assert "已启用" in window.task_page.status_label.text()


def test_task_page_refresh_updates_path_and_status(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window.task_page.refresh_button, Qt.LeftButton)

    assert "CodexSubMcpWatchdog" in window.task_page.status_label.text()
    assert window.task_page.path_label.text()


def test_task_page_has_run_once_button_and_dispatches_action(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.task_page.run_once_button, Qt.LeftButton)

    assert runner.requests == [("task-run-once", {})]


def test_real_window_cleanup_runs_async_with_busy_feedback(qtbot, monkeypatch):
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.load_windows_processes",
        lambda: (time.sleep(0.05) or []),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window.cleanup_page.preview_button, Qt.LeftButton)

    qtbot.waitUntil(lambda: "执行中" in window.cleanup_page.summary_label.text(), timeout=1000)
    qtbot.waitUntil(lambda: "未发现需要处理的套件" in window.cleanup_page.summary_label.text(), timeout=2000)


def test_real_window_mcp_refresh_runs_async_with_status_feedback(qtbot, monkeypatch):
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.scan_npm_global_packages",
        lambda: (time.sleep(0.05) or []),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window.mcp_page.refresh_button, Qt.LeftButton)

    qtbot.waitUntil(lambda: "扫描中" in window.mcp_page.status_label.text(), timeout=1000)
    qtbot.waitUntil(lambda: "扫描完成" in window.mcp_page.status_label.text(), timeout=2000)


def test_mcp_page_renders_source_version_and_confidence(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_config",
                    "version": None,
                    "confidence": "high",
                    "command": "npx -y @modelcontextprotocol/server-memory",
                    "notes": "configured in codex",
                }
            ],
            "installed_candidates": [
                {
                    "name": "@modelcontextprotocol/server-filesystem",
                    "source": "npm_global",
                    "version": "1.0.0",
                    "confidence": "high",
                    "path": "C:/Tools/server-filesystem.exe",
                    "notes": "global package",
                }
            ],
        }
    )
    qtbot.addWidget(window)

    assert "codex_config" in window.mcp_page.configured_list.item(0).text()
    assert "@modelcontextprotocol/server-memory" in window.mcp_page.configured_list.item(0).text()
    assert "npm_global" in window.mcp_page.installed_list.item(0).text()
    assert "1.0.0" in window.mcp_page.installed_list.item(0).text()
    assert "C:/Tools/server-filesystem.exe" in window.mcp_page.installed_list.item(0).text()


def test_mcp_page_shows_detail_panel_for_selected_record(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_config",
                    "version": None,
                    "confidence": "high",
                    "notes": "configured in codex",
                    "command": "npx -y @modelcontextprotocol/server-memory",
                    "path": None,
                }
            ],
            "installed_candidates": [
                {
                    "name": "@modelcontextprotocol/server-filesystem",
                    "source": "npm_global",
                    "version": "1.0.0",
                    "confidence": "high",
                    "notes": None,
                    "command": None,
                    "path": "C:/Tools/server-filesystem.exe",
                }
            ],
        }
    )
    qtbot.addWidget(window)

    window.mcp_page.configured_list.setCurrentRow(0)

    configured_text = window.mcp_page.detail_view.toPlainText()
    assert "name=memory" in configured_text
    assert "source=codex_config" in configured_text
    assert "confidence=high" in configured_text
    assert "command=npx -y @modelcontextprotocol/server-memory" in configured_text
    assert "notes=configured in codex" in configured_text

    window.mcp_page.installed_list.setCurrentRow(0)

    installed_text = window.mcp_page.detail_view.toPlainText()
    assert "name=@modelcontextprotocol/server-filesystem" in installed_text
    assert "version=1.0.0" in installed_text
    assert "path=C:/Tools/server-filesystem.exe" in installed_text


def test_mcp_page_shows_selected_record_details(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_config",
                    "version": None,
                    "confidence": "high",
                    "command": "npx -y @modelcontextprotocol/server-memory",
                    "path": None,
                    "notes": "configured in codex",
                }
            ],
            "installed_candidates": [
                {
                    "name": "@modelcontextprotocol/server-filesystem",
                    "source": "npm_global",
                    "version": "1.0.0",
                    "confidence": "high",
                    "command": None,
                    "path": "C:/Users/test/AppData/Roaming/npm/server-filesystem.cmd",
                    "notes": "installed globally",
                }
            ],
        }
    )
    qtbot.addWidget(window)

    window.mcp_page.configured_list.setCurrentRow(0)
    configured_detail = window.mcp_page.detail_view.toPlainText()

    assert "name=memory" in configured_detail
    assert "source=codex_config" in configured_detail
    assert "confidence=high" in configured_detail
    assert "command=npx -y @modelcontextprotocol/server-memory" in configured_detail

    window.mcp_page.installed_list.setCurrentRow(0)
    installed_detail = window.mcp_page.detail_view.toPlainText()

    assert "name=@modelcontextprotocol/server-filesystem" in installed_detail
    assert "version=1.0.0" in installed_detail
    assert "path=C:/Users/test/AppData/Roaming/npm/server-filesystem.cmd" in installed_detail
    assert "notes=installed globally" in installed_detail


def test_mcp_page_can_copy_and_export_current_results(qtbot, tmp_path):
    export_dir = tmp_path / "exports"
    window = MainWindow(
        export_dir=export_dir,
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_config",
                    "version": None,
                    "confidence": "high",
                    "command": "npx -y @modelcontextprotocol/server-memory",
                    "notes": "configured in codex",
                }
            ],
            "installed_candidates": [
                {
                    "name": "@modelcontextprotocol/server-filesystem",
                    "source": "npm_global",
                    "version": "1.0.0",
                    "confidence": "high",
                    "path": "C:/Tools/server-filesystem.exe",
                    "notes": "installed globally",
                }
            ],
        },
    )
    qtbot.addWidget(window)

    qtbot.mouseClick(window.mcp_page.copy_button, Qt.LeftButton)
    copied_text = QGuiApplication.clipboard().text()
    assert "memory" in copied_text
    assert "source" in copied_text

    qtbot.mouseClick(window.mcp_page.export_button, Qt.LeftButton)
    exported = export_dir / "mcp-inventory.json"
    assert exported.exists()
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["configured"][0]["name"] == "memory"
    assert "已导出" in window.mcp_page.status_label.text()
