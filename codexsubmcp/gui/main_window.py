from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

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
from codexsubmcp.gui.theme import apply_theme
from codexsubmcp.platform.windows.elevation import is_user_admin, run_elevated
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


def _task_shell_summary(task_status: TaskStatus) -> str:
    if not task_status.installed:
        return f"{task_status.task_name} / 未安装"
    enabled_text = "已启用" if task_status.enabled else "已禁用"
    return f"{task_status.task_name} / 已安装 / {enabled_text}"


def _cleanup_reason(classification: str) -> str:
    if classification == "orphaned_after_codex_exit":
        return "未找到仍存活的 Codex 父进程，判定为孤儿套件。"
    if classification == "attached_to_live_codex":
        return "检测到仍存活的 Codex 父进程，该套件仍附着在活动会话上。"
    return "暂无判定原因。"


def _cleanup_risk_hint(*, classification: str, targeted: bool, dry_run: bool) -> str:
    if targeted and dry_run:
        return "该套件会被清理，请确认没有仍在使用的终端会话。"
    if targeted:
        return "该套件将执行真实清理，请确认相关 MCP 进程可以安全终止。"
    if classification == "attached_to_live_codex":
        return "该套件仍附着在 live Codex 会话上，默认不会执行清理。"
    return "该套件当前会被保留，不会执行终止操作。"


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
        export_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("CodexSubMcp Manager")
        self.resize(1080, 720)

        self.task_runner = task_runner or TaskRunner()
        if hasattr(self.task_runner, "requested"):
            self.task_runner.requested.connect(self._handle_request)
        if hasattr(self.task_runner, "started"):
            self.task_runner.started.connect(self._handle_started)
        if hasattr(self.task_runner, "succeeded"):
            self.task_runner.succeeded.connect(self._handle_succeeded)
        if hasattr(self.task_runner, "failed"):
            self.task_runner.failed.connect(self._handle_failed)

        runtime_paths = build_runtime_paths()
        resolved_config_path = config_path or ensure_runtime_config()
        resolved_config = config or load_config(runtime_path=resolved_config_path)
        resolved_inventory = inventory or {"configured": [], "installed_candidates": []}
        resolved_log_dir = log_dir or runtime_paths.logs
        resolved_export_dir = export_dir or runtime_paths.exports
        self.config_path = resolved_config_path
        self.log_dir = resolved_log_dir
        self.task_status = task_status or TaskStatus(
            task_name=DEFAULT_TASK_NAME,
            installed=False,
            enabled=None,
            executable_path=None,
            arguments=None,
        )

        self.top_page_label = QLabel("页面：总览")
        self.top_status_label = QLabel("")
        self.top_path_label = QLabel(f"日志目录：{resolved_log_dir}")
        self.top_activity_label = QLabel("活动：就绪")
        self.activity_toggle_button = QPushButton("显示活动抽屉")
        self.activity_log_view = QPlainTextEdit()
        self.activity_log_view.setReadOnly(True)
        self.activity_drawer = QWidget()
        self.activity_drawer.setVisible(False)
        self.top_page_label.setObjectName("pageTitle")
        self.top_status_label.setObjectName("statusPill")
        self.top_path_label.setObjectName("pathLabel")
        self.top_activity_label.setObjectName("activityPill")
        self.activity_drawer.setObjectName("activityDrawer")

        self.nav_list = QListWidget()
        self.nav_list.addItems(["总览", "清理", "计划任务", "配置", "MCP 检索", "日志"])
        self.nav_list.setObjectName("navList")

        self.stack = QStackedWidget()
        self.overview_page = OverviewPage(
            self.task_runner,
            task_status=self.task_status,
            config=resolved_config,
            inventory=resolved_inventory,
        )
        self.cleanup_page = CleanupPage(self.task_runner, export_dir=resolved_export_dir)
        self.task_page = TaskPage(self.task_status, self.task_runner)
        self.config_page = ConfigPage(
            config=resolved_config,
            config_path=resolved_config_path,
            export_dir=resolved_export_dir,
        )
        self.mcp_page = McpPage(
            inventory=resolved_inventory,
            task_runner=self.task_runner,
            export_dir=resolved_export_dir,
        )
        self.log_page = LogPage(log_dir=resolved_log_dir, export_dir=resolved_export_dir)

        for page in (
            self.overview_page,
            self.cleanup_page,
            self.task_page,
            self.config_page,
            self.mcp_page,
            self.log_page,
        ):
            self.stack.addWidget(page)

        self.nav_list.currentRowChanged.connect(self._handle_navigation_changed)
        self.nav_list.setCurrentRow(0)

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)

        top_bar_widget = QWidget()
        top_bar_widget.setObjectName("topBar")
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 8)
        top_bar.addWidget(self.top_page_label)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.top_status_label)
        top_bar.addSpacing(12)
        top_bar.addWidget(self.top_activity_label)
        top_bar.addStretch(1)
        top_bar.addWidget(self.top_path_label)
        top_bar.addWidget(self.activity_toggle_button)
        top_bar_widget.setLayout(top_bar)

        self.activity_toggle_button.clicked.connect(self._toggle_activity_drawer)

        drawer_layout = QVBoxLayout()
        drawer_layout.addWidget(QLabel("活动抽屉"))
        drawer_layout.addWidget(self.activity_log_view)
        self.activity_drawer.setLayout(drawer_layout)

        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(14, 14, 14, 14)
        central_layout.setSpacing(12)
        central_layout.addWidget(top_bar_widget)
        central_layout.addWidget(splitter, 1)
        central_layout.addWidget(self.activity_drawer)

        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        for page in (
            self.overview_page,
            self.cleanup_page,
            self.task_page,
            self.config_page,
            self.mcp_page,
            self.log_page,
        ):
            page.setObjectName("contentPage")

        apply_theme(self)
        self._set_top_task_status(self.task_status)
        self._append_activity("READY shell initialized")

    def _default_install_source(self) -> Path | None:
        if getattr(sys, "frozen", False):
            return Path(sys.executable)
        project_root = Path(__file__).resolve().parents[2]
        bundled_exe = project_root / "dist" / STABLE_EXE_NAME
        if bundled_exe.exists():
            return bundled_exe
        return None

    def _elevation_entrypoint(self) -> tuple[Path, list[str]]:
        if getattr(sys, "frozen", False):
            return Path(sys.executable), []
        bundled_exe = self._default_install_source()
        if bundled_exe is not None:
            return bundled_exe, []
        return Path(sys.executable), ["-m", "codexsubmcp"]

    def _refresh_task_status(self) -> None:
        self.task_status = get_task_status(task_name=DEFAULT_TASK_NAME)
        return self.task_status

    def _refresh_inventory(self) -> None:
        return build_inventory(
            configured=scan_configured_sources(),
            installed_candidates=[
                *scan_npm_global_packages(),
                *scan_path_candidates(),
                *scan_python_candidates(),
            ],
        )

    def _run_cleanup(self, *, dry_run: bool) -> None:
        config = load_config(runtime_path=self.config_path)
        report = run_cleanup(
            load_windows_processes(),
            config=config,
            dry_run=dry_run,
            kill_runner=self._run_taskkill,
        )
        cleanup_target_ids = {suite.suite_id for suite in report.cleanup_targets}
        payload = {
            "suites": [
                {
                    "suite_id": suite.suite_id,
                    "classification": suite.classification,
                    "root_pid": suite.root_pid,
                    "process_count": len(suite.processes),
                    "created_at": suite.created_at.isoformat(),
                    "process_ids": suite.process_ids,
                    "reason": _cleanup_reason(suite.classification),
                    "risk_hint": _cleanup_risk_hint(
                        classification=suite.classification,
                        targeted=suite.suite_id in cleanup_target_ids,
                        dry_run=dry_run,
                    ),
                    "command_summaries": [
                        process.command_line
                        for process in suite.processes
                        if process.command_line
                    ],
                    "processes": [
                        {
                            "pid": process.pid,
                            "ppid": process.ppid,
                            "name": process.name,
                            "created_at": process.created_at.isoformat(),
                            "command_line": process.command_line,
                        }
                        for process in suite.processes
                    ],
                }
                for suite in report.suites
            ],
            "cleanup_targets": list(cleanup_target_ids),
            "actions": report.actions,
        }
        return payload

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
        if not hasattr(self.task_runner, "run_task"):
            return
        if command == "dry-run":
            self.task_runner.run_task(command, lambda: self._cleanup_or_report(dry_run=True))
            return
        if command == "cleanup":
            self.task_runner.run_task(command, lambda: self._cleanup_or_report(dry_run=False))
            return
        if command == "task-status":
            self.task_runner.run_task(command, self._refresh_task_status)
            return
        if command == "task-install":
            source = self._default_install_source()
            if source is None:
                message = "未找到可安装的 GUI 可执行文件"
                self.task_page.set_error(message)
                self._set_top_activity(message)
                self._append_activity(f"FAILED task-install: {message}")
                return
            self.task_runner.run_task(
                command,
                lambda: self._install_or_refresh(source, interval=int(payload.get("interval") or 10)),
            )
            return
        if command == "task-uninstall":
            self.task_runner.run_task(command, self._uninstall_or_refresh)
            return
        if command == "task-enable":
            self.task_runner.run_task(command, self._enable_or_refresh)
            return
        if command == "task-disable":
            self.task_runner.run_task(command, self._disable_or_refresh)
            return
        if command == "task-run-once":
            self.task_runner.run_task(command, self._run_once_and_refresh)
            return
        if command == "scan-mcp":
            self.task_runner.run_task(command, self._refresh_inventory)

    def _install_and_refresh(self, source: Path, *, interval: int) -> TaskStatus:
        installed_path = install_current_executable(source)
        register_task(task_name=DEFAULT_TASK_NAME, executable_path=installed_path, interval_minutes=interval)
        return self._refresh_task_status()

    def _install_or_refresh(self, source: Path, *, interval: int) -> TaskStatus:
        if is_user_admin():
            return self._install_and_refresh(source, interval=interval)
        return self._run_elevated_task(
            [
                "task",
                "install",
                "--task-name",
                DEFAULT_TASK_NAME,
                "--interval",
                str(interval),
                "--executable-path",
                str(source),
            ]
        )

    def _uninstall_and_refresh(self) -> TaskStatus:
        unregister_task(task_name=DEFAULT_TASK_NAME)
        return self._refresh_task_status()

    def _uninstall_or_refresh(self) -> TaskStatus:
        if is_user_admin():
            return self._uninstall_and_refresh()
        return self._run_elevated_task(["task", "uninstall", "--task-name", DEFAULT_TASK_NAME])

    def _enable_and_refresh(self) -> TaskStatus:
        set_task_enabled(task_name=DEFAULT_TASK_NAME, enabled=True)
        return self._refresh_task_status()

    def _enable_or_refresh(self) -> TaskStatus:
        if is_user_admin():
            return self._enable_and_refresh()
        return self._run_elevated_task(["task", "enable", "--task-name", DEFAULT_TASK_NAME])

    def _disable_and_refresh(self) -> TaskStatus:
        set_task_enabled(task_name=DEFAULT_TASK_NAME, enabled=False)
        return self._refresh_task_status()

    def _disable_or_refresh(self) -> TaskStatus:
        if is_user_admin():
            return self._disable_and_refresh()
        return self._run_elevated_task(["task", "disable", "--task-name", DEFAULT_TASK_NAME])

    def _run_once_and_refresh(self) -> TaskStatus:
        self._run_cleanup(dry_run=False)
        return self._refresh_task_status()

    def _cleanup_or_report(self, *, dry_run: bool) -> dict[str, object]:
        if dry_run or is_user_admin():
            return self._run_cleanup(dry_run=dry_run)
        executable_path, prefix_arguments = self._elevation_entrypoint()
        runtime_paths = build_runtime_paths()
        runtime_paths.cache.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            suffix=".json",
            prefix="cleanup-report-",
            dir=runtime_paths.cache,
            delete=False,
        ) as handle:
            report_path = Path(handle.name)
        try:
            exit_code = run_elevated(
                executable_path,
                [
                    *prefix_arguments,
                    "cleanup",
                    "--yes",
                    "--headless",
                    "--config",
                    str(self.config_path),
                    "--report-file",
                    str(report_path),
                ],
            )
            if exit_code != 0:
                raise RuntimeError(f"Elevated cleanup failed with exit code {exit_code}")
            if not report_path.exists():
                raise RuntimeError("Elevated cleanup did not produce a report file")
            return json.loads(report_path.read_text(encoding="utf-8"))
        finally:
            report_path.unlink(missing_ok=True)

    def _run_elevated_task(self, arguments: list[str]) -> TaskStatus:
        executable_path, prefix_arguments = self._elevation_entrypoint()
        exit_code = run_elevated(executable_path, [*prefix_arguments, *arguments])
        if exit_code != 0:
            raise RuntimeError(f"Elevated command failed with exit code {exit_code}")
        return self._refresh_task_status()

    def _handle_started(self, command: str) -> None:
        self._set_top_activity(f"{command} 执行中")
        self._append_activity(f"START {command}")
        if command in {"dry-run", "cleanup"}:
            self.cleanup_page.set_busy("执行中...")
        elif command.startswith("task-"):
            self.task_page.set_busy("执行中...")
        elif command == "scan-mcp":
            self.mcp_page.set_busy("扫描中...")

    def _handle_succeeded(self, command: str, result: object) -> None:
        self._set_top_activity(f"{command} 成功")
        self._append_activity(f"SUCCESS {command}")
        if command in {"dry-run", "cleanup"} and isinstance(result, dict):
            self.cleanup_page.set_report(result)
            self.overview_page.set_cleanup_summary(result)
            return
        if command.startswith("task-") and isinstance(result, TaskStatus):
            self.task_status = result
            self.task_page.set_task_status(result)
            self.overview_page.set_task_status(result)
            self._set_top_task_status(result)
            return
        if command == "scan-mcp" and isinstance(result, dict):
            self.mcp_page.set_inventory(result)
            self.overview_page.set_inventory_summary(result)

    def _handle_failed(self, command: str, message: str) -> None:
        self._set_top_activity(f"{command} 失败")
        self._append_activity(f"FAILED {command}: {message}")
        if command in {"dry-run", "cleanup"}:
            self.cleanup_page.set_summary(message)
        elif command.startswith("task-"):
            self.task_page.set_error(message)
        elif command == "scan-mcp":
            self.mcp_page.set_busy(message)

    def _handle_navigation_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        item = self.nav_list.item(index)
        if item is None:
            return
        self.top_page_label.setText(f"页面：{item.text()}")

    def _toggle_activity_drawer(self) -> None:
        visible = self.activity_drawer.isHidden()
        self.activity_drawer.setVisible(visible)
        self.activity_toggle_button.setText("隐藏活动抽屉" if visible else "显示活动抽屉")

    def _set_top_task_status(self, task_status: TaskStatus) -> None:
        self.top_status_label.setText(f"计划任务：{_task_shell_summary(task_status)}")

    def _set_top_activity(self, message: str) -> None:
        self.top_activity_label.setText(f"活动：{message}")

    def _append_activity(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log_view.appendPlainText(f"{timestamp} {message}")
