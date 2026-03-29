from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from codexsubmcp.gui.pages.cleanup_page import CleanupPage
from codexsubmcp.platform.windows.tasks import TaskStatus


def _task_text(task_status: TaskStatus) -> str:
    if not task_status.installed:
        return f"{task_status.task_name}：未安装"
    enabled_text = "已启用" if task_status.enabled else "已禁用"
    return f"{task_status.task_name}：已安装 / {enabled_text}"


class OverviewPage(QWidget):
    def __init__(
        self,
        task_runner,
        *,
        task_status: TaskStatus,
        config: dict[str, object],
        inventory: dict[str, list[dict[str, object]]],
        export_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.refresh_button = QPushButton("刷新")
        self.cleanup_button = QPushButton("执行清理（管理员）")
        self.task_button = QPushButton("")
        self.cleanup_button.setProperty("destructive", True)
        self.refresh_button.setProperty("accent", True)
        self.task_button.setProperty("accent", True)

        self.task_summary_label = QLabel("")
        self.config_summary_label = QLabel("")
        self.cleanup_summary_label = QLabel("请先刷新以载入当前状态。")
        self.mcp_summary_label = QLabel("")
        self.state_summary_label = QLabel("当前态：尚未刷新")
        self.recognition_label = QLabel("识别校验：尚未执行")
        self.latest_result_label = QLabel("最近清理：尚无结果")
        self.lifetime_stats_label = QLabel("累计统计：尚无数据")
        self.refresh_status_label = QLabel("最近刷新：尚未刷新")
        self.cleanup_panel = CleanupPage(export_dir=export_dir, parent=self)
        self._runtime_summary: dict[str, object] = {}
        self._recognition: dict[str, object] = {}
        self._cleanable_target_count = 0

        self.refresh_button.clicked.connect(lambda: task_runner.dispatch("refresh", headless=False))
        self.cleanup_button.clicked.connect(lambda: task_runner.dispatch("cleanup", headless=False, yes=True))

        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)
        actions.addWidget(self.refresh_button, 0, 0)
        actions.addWidget(self.cleanup_button, 0, 1)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("总览"))
        layout.addWidget(self.task_summary_label)
        layout.addWidget(self.config_summary_label)
        layout.addWidget(self.refresh_status_label)
        layout.addWidget(self.recognition_label)
        layout.addWidget(self.state_summary_label)
        layout.addWidget(self.cleanup_summary_label)
        layout.addWidget(self.latest_result_label)
        layout.addWidget(self.lifetime_stats_label)
        layout.addWidget(self.mcp_summary_label)
        layout.addLayout(actions)
        layout.addWidget(self.cleanup_panel)
        layout.addStretch(1)
        self.setLayout(layout)

        self.set_task_status(task_status)
        self.set_config_summary(config)
        self.set_inventory_summary(inventory)
        self.set_workflow_enabled(cleanup_enabled=False)

    def set_task_status(self, task_status: TaskStatus) -> None:
        self.task_summary_label.setText(f"计划任务：{_task_text(task_status)}")

    def set_config_summary(self, config: dict[str, object]) -> None:
        self.config_summary_label.setText(
            "配置摘要："
            f"max_suites={config.get('max_suites')} | "
            f"interval_minutes={config.get('interval_minutes')} | "
            f"suite_window_seconds={config.get('suite_window_seconds')}"
        )

    def set_cleanup_summary(self, report: dict[str, object]) -> None:
        summary = report.get("summary") or {}
        if isinstance(summary, dict) and "target_count" in summary:
            self.cleanup_summary_label.setText(
                f"最近结果：目标 {summary.get('target_count', 0)} 个 | "
                f"失败 {summary.get('failed_target_count', 0)} 个"
            )
            return
        suite_count = len(report.get("suites", []))
        cleanup_target_count = len(report.get("cleanup_targets", []))
        action_count = len(report.get("actions", []))
        self.cleanup_summary_label.setText(
            f"最近清理：候选 {suite_count} 套 | 目标 {cleanup_target_count} 套 | 动作 {action_count} 条"
        )

    def set_inventory_summary(self, inventory: dict[str, list[dict[str, object]]]) -> None:
        configured = len(inventory.get("configured", []))
        running = len(inventory.get("running", []))
        if "running" in inventory:
            self.mcp_summary_label.setText(f"MCP 摘要：已配置 {configured} 项 | 运行中 {running} 类")
            return
        installed = len(inventory.get("installed_candidates", []))
        self.mcp_summary_label.setText(f"MCP 摘要：已配置 {configured} 项 | 候选 {installed} 项")

    def set_workflow_enabled(self, *, cleanup_enabled: bool) -> None:
        self.cleanup_button.setEnabled(cleanup_enabled)

    def set_refresh_summary(self, payload: dict[str, object]) -> None:
        self._runtime_summary = dict(payload.get("summary") or {})
        recognition = payload.get("recognition") or {}
        self._recognition = dict(recognition) if isinstance(recognition, dict) else {}
        self.refresh_status_label.setText(
            f"最近刷新：snapshot={payload.get('snapshot_id') or '-'} | captured_at={payload.get('captured_at') or '-'}"
        )
        self._render_recognition_summary()
        self._render_state_summary()

    def set_preview_summary(self, payload: dict[str, object]) -> None:
        summary = payload.get("summary") or {}
        self._cleanable_target_count = int(summary.get("target_count") or 0) if isinstance(summary, dict) else 0
        self._render_state_summary()

    def set_cleanup_result(self, payload: dict[str, object]) -> None:
        summary = payload.get("summary") or {}
        if not isinstance(summary, dict):
            self.latest_result_label.setText("最近清理：无有效结果")
            return
        state = "成功" if summary.get("success") else "失败"
        self.latest_result_label.setText(
            f"最近清理{state}：+suite {summary.get('closed_suite_count', 0)} | "
            f"+process {summary.get('killed_process_count', 0)}"
        )

    def set_lifetime_stats(self, stats: dict[str, object]) -> None:
        self.lifetime_stats_label.setText(
            f"累计 cleanup {stats.get('total_cleanup_count', 0)} | "
            f"suite {stats.get('total_closed_suite_count', 0)} | "
            f"MCP {stats.get('total_killed_mcp_instance_count', 0)} | "
            f"process {stats.get('total_killed_process_count', 0)} | "
            f"last={stats.get('last_cleanup_at') or '-'}"
        )

    def _render_recognition_summary(self) -> None:
        status = str(self._recognition.get("status") or "unknown")
        reason = str(self._recognition.get("reason") or "尚未执行校验。")
        status_text = "已通过" if status == "trusted" else "未通过"
        self.recognition_label.setText(f"识别校验：{status_text} | {reason}")

    def _render_state_summary(self) -> None:
        self.state_summary_label.setText(
            f"当前态：运行中子代理 {self._runtime_summary.get('open_subagent_count', 0)} | "
            f"运行中 suite {self._runtime_summary.get('live_suite_count', 0)} | "
            f"运行中 MCP 实例 {self._runtime_summary.get('running_mcp_instance_count', 0)} | "
            f"已配置 MCP {self._runtime_summary.get('configured_mcp_count', 0)} | "
            f"可清理目标 {self._cleanable_target_count}"
        )
