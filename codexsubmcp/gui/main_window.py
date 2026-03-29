from __future__ import annotations

from dataclasses import asdict
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from codexsubmcp.app_paths import build_runtime_paths, ensure_runtime_config
from codexsubmcp.core.analysis import analyze_snapshot
from codexsubmcp.core.cleanup import build_cleanup_preview, execute_cleanup_preview
from codexsubmcp.core.config import load_config
from codexsubmcp.core.mcp_inventory import build_inventory
from codexsubmcp.core.recognition import validate_parent_recognition
from codexsubmcp.core.runtime_logs import (
    load_lifetime_stats,
    write_cleanup_log,
    write_refresh_log,
)
from codexsubmcp.core.system_snapshot import build_system_snapshot
from codexsubmcp.gui.pages.config_page import ConfigPage
from codexsubmcp.gui.pages.log_page import LogPage
from codexsubmcp.gui.pages.mcp_page import McpPage
from codexsubmcp.gui.pages.overview_page import OverviewPage
from codexsubmcp.gui.pages.task_page import TaskPage
from codexsubmcp.gui.task_runner import TaskRunner
from codexsubmcp.gui.theme import apply_theme
from codexsubmcp.platform.windows.elevation import is_user_admin, run_elevated
from codexsubmcp.platform.windows.install_artifact import STABLE_EXE_NAME, install_current_executable
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
        resolved_inventory = inventory or {"configured": [], "running": [], "drift": {}}
        resolved_log_dir = log_dir or runtime_paths.logs
        resolved_export_dir = export_dir or runtime_paths.exports
        self.config_path = resolved_config_path
        self.log_dir = resolved_log_dir
        self._latest_snapshot = None
        self._latest_analysis = None
        self._latest_preview = None
        self._latest_recognition: dict[str, object] | None = None
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
        self.top_page_label.setObjectName("pageTitle")
        self.top_status_label.setObjectName("statusPill")
        self.top_path_label.setObjectName("pathLabel")
        self.top_activity_label.setObjectName("activityPill")

        self.nav_list = QListWidget()
        self.nav_list.addItems(["总览", "计划任务", "配置", "MCP 检索", "日志"])
        self.nav_list.setObjectName("navList")

        self.stack = QStackedWidget()
        self.overview_page = OverviewPage(
            self.task_runner,
            task_status=self.task_status,
            config=resolved_config,
            inventory=resolved_inventory,
            export_dir=resolved_export_dir,
        )
        self.cleanup_page = self.overview_page.cleanup_panel
        self.task_page = TaskPage(self.task_status, self.task_runner)
        self.config_page = ConfigPage(
            config=resolved_config,
            config_path=resolved_config_path,
            export_dir=resolved_export_dir,
        )
        self.mcp_page = McpPage(
            inventory=resolved_inventory,
            export_dir=resolved_export_dir,
        )
        self.log_page = LogPage(log_dir=resolved_log_dir, export_dir=resolved_export_dir)

        for page in (
            self.overview_page,
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
        top_bar_widget.setLayout(top_bar)

        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(14, 14, 14, 14)
        central_layout.setSpacing(12)
        central_layout.addWidget(top_bar_widget)
        central_layout.addWidget(splitter, 1)

        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        for page in (
            self.overview_page,
            self.task_page,
            self.config_page,
            self.mcp_page,
            self.log_page,
        ):
            page.setObjectName("contentPage")

        apply_theme(self)
        self._set_top_task_status(self.task_status)
        self._set_workflow_enabled(cleanup_enabled=False, detail_enabled=False)
        self.overview_page.set_lifetime_stats(self._stats_payload())

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

    def _run_refresh(self) -> dict[str, object]:
        config = load_config(runtime_path=self.config_path)
        snapshot = build_system_snapshot()
        analysis = analyze_snapshot(snapshot, config=config)
        recognition = validate_parent_recognition(snapshot, analysis, config)
        inventory = build_inventory(
            configured=list(snapshot.configured_mcps),
            running=list(analysis.running_mcps),
            drift={
                "configured_not_running": list(analysis.configured_not_running),
                "running_not_configured": list(analysis.running_not_configured),
            },
        )
        log_path = write_refresh_log(
            snapshot=snapshot,
            analysis=analysis,
            recognition=recognition,
            log_dir=self.log_dir,
        )
        self._latest_snapshot = snapshot
        self._latest_analysis = analysis
        preview_payload = {"summary": {"target_count": 0}, "targets": []}
        if recognition.trusted:
            preview = build_cleanup_preview(analysis)
            self._latest_preview = preview
            preview_payload = json.loads(json.dumps(asdict(preview), ensure_ascii=False, default=str))
        else:
            self._latest_preview = None
        self._latest_recognition = {
            "status": recognition.status,
            "reason": recognition.reason,
        }
        return {
            **json.loads(log_path.read_text(encoding="utf-8")),
            "inventory": inventory,
            "preview": preview_payload,
            "log_path": str(log_path),
        }

    def _run_cleanup(self) -> dict[str, object]:
        if self._latest_preview is None:
            raise RuntimeError("请先刷新并确认存在 orphan 清理目标。")
        if not self._recognition_trusted():
            raise RuntimeError(self._recognition_reason())
        result = execute_cleanup_preview(
            self._latest_preview,
            kill_runner=self._run_taskkill,
        )
        log_path = write_cleanup_log(result=result, log_dir=self.log_dir)
        return {
            **json.loads(log_path.read_text(encoding="utf-8")),
            "log_path": str(log_path),
        }

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
        if command == "refresh":
            self.task_runner.run_task(command, self._run_refresh)
            return
        if command == "cleanup":
            self.task_runner.run_task(command, self._cleanup_or_report)
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
        self._run_refresh()
        if self._latest_preview is not None:
            self._run_cleanup()
        return self._refresh_task_status()

    def _cleanup_or_report(self, *, dry_run: bool | None = None) -> dict[str, object]:
        if self._latest_preview is None:
            raise RuntimeError("请先刷新并确认存在 orphan 清理目标。")
        if is_user_admin():
            return self._run_cleanup()
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
        if command == "cleanup":
            self.cleanup_page.set_busy("执行中...")
        elif command.startswith("task-"):
            self.task_page.set_busy("执行中...")
        elif command == "refresh":
            self.mcp_page.set_busy("刷新中...")
            self.cleanup_page.set_summary("刷新中...")

    def _handle_succeeded(self, command: str, result: object) -> None:
        self._set_top_activity(f"{command} 成功")
        if command == "refresh" and isinstance(result, dict):
            inventory = result.get("inventory") or {"configured": [], "running": [], "drift": {}}
            if isinstance(inventory, dict):
                self.mcp_page.set_inventory(inventory)
                self.overview_page.set_inventory_summary(inventory)
            self.overview_page.set_refresh_summary(result)
            preview_payload = result.get("preview") or {"summary": {"target_count": 0}, "targets": []}
            if isinstance(preview_payload, dict):
                self.overview_page.set_preview_summary(preview_payload)
                self.cleanup_page.set_preview(preview_payload)
            if self._recognition_trusted_from_payload(result):
                target_count = int((((preview_payload or {}).get("summary") or {}).get("target_count") or 0))
                if target_count > 0:
                    self.cleanup_page.set_summary(f"父进程识别校验已通过，发现 {target_count} 个 orphan 目标，可执行清理。")
                    self._set_workflow_enabled(cleanup_enabled=True, detail_enabled=True)
                else:
                    self.cleanup_page.set_summary("父进程识别校验已通过，当前未发现 orphan 目标。")
                    self._set_workflow_enabled(cleanup_enabled=False, detail_enabled=True)
            else:
                self.cleanup_page.set_summary(self._recognition_reason_from_payload(result))
                self._set_workflow_enabled(cleanup_enabled=False, detail_enabled=False)
            self.overview_page.set_cleanup_summary(result)
            self.overview_page.set_lifetime_stats(self._stats_payload())
            self.log_page.refresh_logs()
            return
        if command == "cleanup" and isinstance(result, dict):
            self.overview_page.set_cleanup_result(result)
            self.overview_page.set_lifetime_stats(self._stats_payload())
            summary = result.get("summary") or {}
            self.cleanup_page.set_summary(f"清理完成：失败 {(summary.get('failed_target_count') or 0)} 个")
            self.overview_page.set_cleanup_summary(result)
            self.log_page.refresh_logs()
            if (summary.get("success") and hasattr(self.task_runner, "run_task")):
                self.task_runner.run_task("refresh", self._run_refresh)
            return
        if command.startswith("task-") and isinstance(result, TaskStatus):
            self.task_status = result
            self.task_page.set_task_status(result)
            self.overview_page.set_task_status(result)
            self._set_top_task_status(result)
            return

    def _handle_failed(self, command: str, message: str) -> None:
        self._set_top_activity(f"{command} 失败")
        if command == "cleanup":
            self.cleanup_page.set_summary(message)
        elif command.startswith("task-"):
            self.task_page.set_error(message)
        elif command == "refresh":
            self.mcp_page.set_busy(message)
            self._set_workflow_enabled(cleanup_enabled=False, detail_enabled=False)

    def _handle_navigation_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        item = self.nav_list.item(index)
        if item is None:
            return
        self.top_page_label.setText(f"页面：{item.text()}")

    def _set_top_task_status(self, task_status: TaskStatus) -> None:
        self.top_status_label.setText(f"计划任务：{_task_shell_summary(task_status)}")

    def _set_top_activity(self, message: str) -> None:
        self.top_activity_label.setText(f"活动：{message}")

    def _set_workflow_enabled(self, *, cleanup_enabled: bool, detail_enabled: bool) -> None:
        self.overview_page.set_workflow_enabled(cleanup_enabled=cleanup_enabled)
        self.cleanup_page.set_actions_enabled(
            detail_enabled=detail_enabled,
        )

    def _recognition_trusted(self) -> bool:
        if not isinstance(self._latest_recognition, dict):
            return False
        return str(self._latest_recognition.get("status") or "") == "trusted"

    def _recognition_reason(self) -> str:
        if not isinstance(self._latest_recognition, dict):
            return "父进程识别校验未执行。"
        return str(self._latest_recognition.get("reason") or "父进程识别校验未通过。")

    def _recognition_trusted_from_payload(self, payload: dict[str, object]) -> bool:
        recognition = payload.get("recognition")
        self._latest_recognition = dict(recognition) if isinstance(recognition, dict) else None
        return self._recognition_trusted()

    def _recognition_reason_from_payload(self, payload: dict[str, object]) -> str:
        recognition = payload.get("recognition")
        self._latest_recognition = dict(recognition) if isinstance(recognition, dict) else None
        return self._recognition_reason()

    def _stats_payload(self) -> dict[str, object]:
        stats = load_lifetime_stats(log_dir=self.log_dir)
        return {
            "total_refresh_count": stats.total_refresh_count,
            "total_preview_count": stats.total_preview_count,
            "total_cleanup_count": stats.total_cleanup_count,
            "total_closed_suite_count": stats.total_closed_suite_count,
            "total_killed_mcp_instance_count": stats.total_killed_mcp_instance_count,
            "total_killed_process_count": stats.total_killed_process_count,
            "last_cleanup_at": stats.last_cleanup_at.isoformat() if stats.last_cleanup_at else None,
        }
