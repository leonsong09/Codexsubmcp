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


class WorkflowRunner(FakeTaskRunner):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[str] = []

    def run_task(self, command: str, callback) -> None:
        self.tasks.append(command)


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

    assert labels == ["总览", "计划任务", "配置", "日志"]


def test_main_window_applies_shell_theme_hooks(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    assert window.objectName() == "shellRoot"
    assert window.nav_list.objectName() == "navList"
    assert "#shellRoot" in QApplication.instance().styleSheet()


def test_main_window_has_top_status_bar(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    assert "总览" in window.top_page_label.text()
    assert "CodexSubMcpWatchdog" in window.top_status_label.text()
    assert str(window.log_dir) in window.top_path_label.text()


def test_main_window_top_activity_reflects_lifecycle_events(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    window._handle_started("refresh")
    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {"configured": [{"name": "memory"}], "running": [], "drift": {}},
            "preview": {"summary": {"target_count": 0}, "targets": []},
        },
    )
    window._handle_failed("task-install", "elevation failed")

    assert "失败" in window.top_activity_label.text()


def test_overview_buttons_dispatch_refresh_preview_and_cleanup(qtbot):
    runner = FakeTaskRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    qtbot.mouseClick(window.overview_page.refresh_button, Qt.LeftButton)
    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {"configured": [{"name": "memory"}], "running": [], "drift": {}},
            "preview": {"summary": {"target_count": 1}, "targets": []},
        },
    )
    qtbot.mouseClick(window.overview_page.cleanup_button, Qt.LeftButton)

    assert runner.requests == [
        ("refresh", {"headless": False}),
        ("cleanup", {"headless": False, "yes": True}),
    ]


def test_overview_page_shows_only_main_workflow_buttons(qtbot):
    window = MainWindow(
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
            "running": [{"tool_signature": "memory", "instance_count": 1}],
            "drift": {"configured_not_running": [], "running_not_configured": []},
        },
    )
    qtbot.addWidget(window)

    assert "已安装" in window.overview_page.task_summary_label.text()
    assert "max_suites=6" in window.overview_page.config_summary_label.text()
    assert "已配置 1" in window.overview_page.mcp_summary_label.text()
    assert "运行中 1" in window.overview_page.mcp_summary_label.text()
    assert window.overview_page.refresh_button.text() == "刷新"
    assert window.overview_page.cleanup_button.text() == "执行清理（管理员）"


def test_overview_page_shows_runtime_totals_latest_cleanup_and_lifetime_stats(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    window.overview_page.set_refresh_summary(
        {
            "snapshot_id": "snapshot-1",
            "captured_at": "2026-03-28T12:00:00",
            "recognition": {"status": "trusted", "reason": "ok"},
            "summary": {
                "open_subagent_count": 3,
                "live_suite_count": 2,
                "running_mcp_instance_count": 4,
                "configured_mcp_count": 7,
            },
        }
    )
    window.overview_page.set_preview_summary({"summary": {"target_count": 2}})
    window.overview_page.set_cleanup_result(
        {
            "summary": {
                "success": True,
                "closed_suite_count": 1,
                "killed_process_count": 4,
            }
        }
    )
    window.overview_page.set_lifetime_stats(
        {
            "total_cleanup_count": 3,
            "total_closed_suite_count": 4,
            "total_killed_mcp_instance_count": 9,
            "total_killed_process_count": 18,
            "last_cleanup_at": "2026-03-28T12:10:00",
        }
    )

    assert "运行中子代理 3" in window.overview_page.state_summary_label.text()
    assert "运行中 suite 2" in window.overview_page.state_summary_label.text()
    assert "运行中 MCP 实例 4" in window.overview_page.state_summary_label.text()
    assert "已配置 MCP 7" in window.overview_page.state_summary_label.text()
    assert "可清理目标 2" in window.overview_page.state_summary_label.text()
    assert "已通过" in window.overview_page.recognition_label.text()
    assert "最近清理成功" in window.overview_page.latest_result_label.text()
    assert "累计 cleanup 3" in window.overview_page.lifetime_stats_label.text()
    assert "snapshot-1" in window.overview_page.refresh_status_label.text()


def test_workflow_buttons_are_disabled_before_refresh(qtbot):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)

    assert not window.overview_page.cleanup_button.isEnabled()
    assert not window.cleanup_page.copy_table_button.isEnabled()


def test_refresh_success_updates_pages_and_enables_workflow(qtbot, monkeypatch):
    window = MainWindow(task_runner=FakeTaskRunner())
    qtbot.addWidget(window)
    seen: list[str] = []
    monkeypatch.setattr(window.log_page, "refresh_logs", lambda: seen.append("logs"))

    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {
                "configured": [{"name": "memory"}],
                "running": [{"tool_signature": "memory", "instance_count": 1}],
                "drift": {"configured_not_running": [], "running_not_configured": []},
            },
            "preview": {"summary": {"target_count": 0}, "targets": []},
        },
    )

    assert not window.overview_page.cleanup_button.isEnabled()
    assert window.cleanup_page.copy_table_button.isEnabled()
    assert "已配置 1" in window.mcp_page.status_label.text()
    assert "校验已通过" in window.cleanup_page.summary_label.text()
    assert seen == ["logs"]


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


def test_mcp_page_shows_configured_and_running_records_without_installed_candidates_tab(qtbot):
    window = MainWindow(
        task_runner=FakeTaskRunner(),
        inventory={
            "configured": [{"name": "memory"}],
            "running": [{"tool_signature": "server-memory", "instance_count": 1, "live_codex_pid_count": 0}],
            "drift": {"configured_not_running": [], "running_not_configured": []},
        },
    )
    qtbot.addWidget(window)

    assert window.mcp_page.configured_list.count() == 1
    assert window.mcp_page.running_list.count() == 1
    assert window.mcp_page.result_tabs.count() == 2
    assert window.mcp_page.result_tabs.tabText(0) == "已配置"
    assert window.mcp_page.result_tabs.tabText(1) == "运行中"


def test_mcp_page_shows_drift_summary(qtbot):
    window = MainWindow(
        inventory={
            "configured": [{"name": "memory"}],
            "running": [{"tool_signature": "agentation-mcp", "instance_count": 2, "live_codex_pid_count": 1}],
            "drift": {
                "configured_not_running": ["server-memory"],
                "running_not_configured": ["agentation-mcp"],
            },
        }
    )
    qtbot.addWidget(window)

    assert "drift 2 项" in window.mcp_page.status_label.text()
    assert "agentation-mcp" in window.mcp_page.drift_label.text()
    assert "server-memory" in window.mcp_page.drift_label.text()


def test_cleanup_page_can_copy_and_export_preview_targets(qtbot, tmp_path):
    export_dir = tmp_path / "exports"
    window = MainWindow(export_dir=export_dir)
    qtbot.addWidget(window)
    window.cleanup_page.set_preview(
        {
            "summary": {"target_count": 1},
            "targets": [
                {
                    "target_id": "orphan-1",
                    "target_type": "orphan_suite",
                    "kill_pid": 210,
                    "process_ids": [210, 211],
                    "created_at": "2026-03-26T10:00:00",
                    "reason": "orphan suite",
                    "risk_hint": "safe to kill",
                }
            ],
        }
    )

    qtbot.mouseClick(window.cleanup_page.copy_table_button, Qt.LeftButton)
    copied_text = QGuiApplication.clipboard().text()
    assert "orphan-1" in copied_text
    assert "Target" in copied_text

    qtbot.mouseClick(window.cleanup_page.export_table_button, Qt.LeftButton)
    exported = export_dir / "cleanup-targets.tsv"
    assert exported.exists()
    assert "orphan-1" in exported.read_text(encoding="utf-8")
    assert "已导出" in window.cleanup_page.summary_label.text()


def test_log_page_lists_files_and_shows_selected_content(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "refresh-20260326-100000.json").write_text(
        json.dumps({"kind": "refresh", "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 2}}),
        encoding="utf-8",
    )
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)

    window.log_page.log_list.setCurrentRow(0)

    assert window.log_page.log_list.count() == 1
    assert "configured_mcp_count" in window.log_page.detail_view.toPlainText()


def test_log_page_filters_by_action_and_status(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "preview-20260326-100000.json").write_text(
        json.dumps(
            {
                "kind": "preview",
                "summary": {"target_count": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (log_dir / "cleanup-20260326-100500.json").write_text(
        json.dumps(
            {
                "kind": "cleanup",
                "summary": {
                    "success": False,
                    "closed_suite_count": 0,
                    "killed_mcp_instance_count": 0,
                    "killed_process_count": 0,
                    "failed_target_count": 1,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir)
    qtbot.addWidget(window)

    assert window.log_page.log_list.count() == 2

    window.log_page.action_filter.setCurrentText("preview")
    assert window.log_page.log_list.count() == 1
    assert "preview" in window.log_page.log_list.item(0).text()

    window.log_page.action_filter.setCurrentText("全部动作")
    window.log_page.status_filter.setCurrentText("failure")
    assert window.log_page.log_list.count() == 1
    assert "cleanup" in window.log_page.log_list.item(0).text()


def test_log_page_can_export_selected_log(qtbot, tmp_path):
    log_dir = tmp_path / "logs"
    export_dir = tmp_path / "exports"
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "cleanup",
        "summary": {
            "success": True,
            "closed_suite_count": 1,
            "killed_mcp_instance_count": 1,
            "killed_process_count": 2,
        },
    }
    (log_dir / "cleanup-20260326-101000.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    window = MainWindow(task_runner=FakeTaskRunner(), log_dir=log_dir, export_dir=export_dir)
    qtbot.addWidget(window)

    window.log_page.log_list.setCurrentRow(0)
    qtbot.mouseClick(window.log_page.export_button, Qt.LeftButton)

    exported_path = export_dir / "cleanup-20260326-101000.json"
    assert exported_path.exists()
    assert json.loads(exported_path.read_text(encoding="utf-8"))["kind"] == "cleanup"
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

    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {"configured": [{"name": "memory"}], "running": [], "drift": {}},
            "preview": {"summary": {"target_count": 1}, "targets": []},
        },
    )
    qtbot.mouseClick(window.overview_page.cleanup_button, Qt.LeftButton)

    assert runner.requests == [
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
    window._latest_preview = object()
    window._latest_recognition = {"status": "trusted", "reason": "ok"}

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
                    "kind": "cleanup",
                    "summary": {
                        "success": True,
                        "closed_suite_count": 1,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr("codexsubmcp.gui.main_window.run_elevated", fake_run_elevated)

    payload = window._cleanup_or_report()

    assert payload["summary"]["success"] is True
    assert payload["summary"]["closed_suite_count"] == 1
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


def test_cleanup_success_triggers_follow_up_refresh(qtbot):
    runner = WorkflowRunner()
    window = MainWindow(task_runner=runner)
    qtbot.addWidget(window)

    window._handle_succeeded("cleanup", {"summary": {"success": True}})

    assert runner.tasks == ["refresh"]


def test_cleanup_page_can_render_preview_target_summary_and_details(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.cleanup_page.set_preview(
        {
            "summary": {"target_count": 1},
            "targets": [
                {
                    "target_id": "orphan-1",
                    "target_type": "orphan_suite",
                    "kill_pid": 210,
                    "created_at": "2026-03-26T10:00:00",
                    "process_ids": [210, 211],
                    "reason": "未找到仍存活的 Codex 父进程，判定为孤儿套件。",
                    "risk_hint": "该套件会被清理，请确认没有仍在使用的终端会话。",
                }
            ],
        }
    )

    headers = [
        window.cleanup_page.target_table.horizontalHeaderItem(index).text()
        for index in range(window.cleanup_page.target_table.columnCount())
    ]
    assert headers == ["Target", "类型", "Kill PID", "进程数", "创建时间", "动作"]
    assert window.cleanup_page.target_table.rowCount() == 1
    assert window.cleanup_page.target_table.item(0, 0).text() == "orphan-1"
    window.cleanup_page.target_table.setCurrentCell(0, 0)
    assert "kill_pid=210" in window.cleanup_page.detail_view.toPlainText()
    assert "判定原因" in window.cleanup_page.detail_view.toPlainText()
    assert "风险提示" in window.cleanup_page.detail_view.toPlainText()
    assert "已载入 orphan 结果" in window.cleanup_page.summary_label.text()


def test_run_cleanup_executes_preview_without_policy(qtbot, tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    log_path = tmp_path / "cleanup.json"
    log_path.write_text(json.dumps({"summary": {"failed_target_count": 0}}), encoding="utf-8")
    window = MainWindow(config=DEFAULT_CONFIG, config_path=config_path)
    qtbot.addWidget(window)
    window._latest_preview = {"summary": {"target_count": 1}}
    window._latest_recognition = {"status": "trusted", "reason": "ok"}

    seen: dict[str, object] = {}

    def fake_execute(preview, *, kill_runner):
        seen["preview"] = preview
        return {"summary": {"success": True, "failed_target_count": 0}}

    monkeypatch.setattr("codexsubmcp.gui.main_window.execute_cleanup_preview", fake_execute)
    monkeypatch.setattr(
        "codexsubmcp.gui.main_window.write_cleanup_log",
        lambda *, result, log_dir: log_path,
    )

    window._run_cleanup()

    assert seen["preview"] == {"summary": {"target_count": 1}}


def test_cleanup_success_summary_shows_failed_target_count(qtbot, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    window = MainWindow(task_runner=FakeTaskRunner(), config=DEFAULT_CONFIG, config_path=config_path)
    qtbot.addWidget(window)

    window._handle_succeeded(
        "cleanup",
        {
            "summary": {
                "success": True,
                "failed_target_count": 0,
            }
        },
    )

    assert "0" in window.cleanup_page.summary_label.text()


def test_main_window_refresh_success_updates_inventory_and_cleanup_summary(qtbot, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(DEFAULT_CONFIG), encoding="utf-8")
    window = MainWindow(config=DEFAULT_CONFIG, config_path=config_path)
    qtbot.addWidget(window)

    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {
                "configured": [{"name": "memory"}],
                "running": [{"tool_signature": "memory", "instance_count": 1}],
                "drift": {"configured_not_running": [], "running_not_configured": []},
            },
            "preview": {"summary": {"target_count": 0}, "targets": []},
        },
    )

    assert "已配置 1" in window.overview_page.mcp_summary_label.text()
    assert "校验已通过" in window.cleanup_page.summary_label.text()


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
    window = MainWindow()
    qtbot.addWidget(window)
    window._handle_succeeded(
        "refresh",
        {
            "summary": {"configured_mcp_count": 1, "running_mcp_instance_count": 1},
            "recognition": {"status": "trusted", "reason": "ok"},
            "inventory": {"configured": [{"name": "memory"}], "running": [], "drift": {}},
            "preview": {"summary": {"target_count": 1}, "targets": [{"target_id": "orphan-1"}]},
        },
    )
    monkeypatch.setattr(
        window,
        "_cleanup_or_report",
        lambda: (time.sleep(0.05) or {"summary": {"success": False, "failed_target_count": 0}}),
    )

    qtbot.mouseClick(window.overview_page.cleanup_button, Qt.LeftButton)

    qtbot.waitUntil(lambda: "执行中" in window.cleanup_page.summary_label.text(), timeout=1000)
    qtbot.waitUntil(lambda: "清理完成" in window.cleanup_page.summary_label.text(), timeout=2000)


def test_mcp_page_renders_configured_source_env_and_timeouts(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_global_config",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"],
                    "env_keys": ["MEMORY_TOKEN"],
                    "startup_timeout_ms": 1500,
                    "tool_timeout_sec": 10.0,
                }
            ],
            "running": [
                {
                    "tool_signature": "server-memory",
                    "instance_count": 1,
                    "live_codex_pid_count": 0,
                }
            ],
            "drift": {"configured_not_running": [], "running_not_configured": []},
        }
    )
    qtbot.addWidget(window)

    assert "codex_global_config" in window.mcp_page.configured_list.item(0).text()
    assert "npx" in window.mcp_page.configured_list.item(0).text()


def test_mcp_page_shows_configured_detail_panel(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_global_config",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-memory"],
                    "env_keys": ["MEMORY_TOKEN"],
                    "startup_timeout_ms": 1500,
                    "tool_timeout_sec": 10.0,
                    "path": None,
                }
            ],
            "running": [
                {
                    "tool_signature": "server-memory",
                    "instance_count": 1,
                    "live_codex_pid_count": 0,
                }
            ],
            "drift": {"configured_not_running": [], "running_not_configured": []},
        }
    )
    qtbot.addWidget(window)

    window.mcp_page.configured_list.setCurrentRow(0)

    configured_text = window.mcp_page.detail_view.toPlainText()
    assert "name=memory" in configured_text
    assert "source=codex_global_config" in configured_text
    assert "env_keys=['MEMORY_TOKEN']" in configured_text
    assert "startup_timeout_ms=1500" in configured_text


def test_mcp_page_shows_running_record_details(qtbot):
    window = MainWindow(
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_global_config",
                    "command": "npx",
                }
            ],
            "running": [
                {
                    "tool_signature": "agentation-mcp",
                    "instance_count": 2,
                    "live_codex_pid_count": 1,
                }
            ],
            "drift": {"configured_not_running": [], "running_not_configured": ["agentation-mcp"]},
        }
    )
    qtbot.addWidget(window)

    window.mcp_page.running_list.setCurrentRow(0)
    running_detail = window.mcp_page.detail_view.toPlainText()

    assert "tool_signature=agentation-mcp" in running_detail
    assert "instance_count=2" in running_detail
    assert "live_codex_pid_count=1" in running_detail


def test_mcp_page_can_copy_and_export_current_results(qtbot, tmp_path):
    export_dir = tmp_path / "exports"
    window = MainWindow(
        export_dir=export_dir,
        inventory={
            "configured": [
                {
                    "name": "memory",
                    "source": "codex_global_config",
                    "command": "npx",
                }
            ],
            "running": [
                {
                    "tool_signature": "agentation-mcp",
                    "instance_count": 2,
                    "live_codex_pid_count": 1,
                }
            ],
            "drift": {"configured_not_running": [], "running_not_configured": ["agentation-mcp"]},
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
    assert payload["running"][0]["tool_signature"] == "agentation-mcp"
    assert "已导出" in window.mcp_page.status_label.text()

