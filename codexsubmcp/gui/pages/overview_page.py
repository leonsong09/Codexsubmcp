from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.preview_button = QPushButton("立即预览")
        self.cleanup_button = QPushButton("立即清理（管理员）")
        self.task_button = QPushButton("")
        self.scan_button = QPushButton("扫描 MCP")
        self.preview_button.setProperty("accent", True)
        self.cleanup_button.setProperty("destructive", True)
        self.task_button.setProperty("accent", True)
        self.scan_button.setProperty("accent", True)

        self.task_summary_label = QLabel("")
        self.config_summary_label = QLabel("")
        self.cleanup_summary_label = QLabel("最近尚未执行清理。")
        self.mcp_summary_label = QLabel("")

        self.preview_button.clicked.connect(lambda: task_runner.dispatch("dry-run", headless=False))
        self.cleanup_button.clicked.connect(lambda: task_runner.dispatch("cleanup", headless=False, yes=True))
        self.task_button.clicked.connect(
            lambda: task_runner.dispatch("task-install", interval=int(config.get("interval_minutes") or 10))
        )
        self.scan_button.clicked.connect(lambda: task_runner.dispatch("scan-mcp"))

        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)
        actions.addWidget(self.preview_button, 0, 0)
        actions.addWidget(self.cleanup_button, 0, 1)
        actions.addWidget(self.task_button, 1, 0)
        actions.addWidget(self.scan_button, 1, 1)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("总览"))
        layout.addWidget(self.task_summary_label)
        layout.addWidget(self.config_summary_label)
        layout.addWidget(self.cleanup_summary_label)
        layout.addWidget(self.mcp_summary_label)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.setLayout(layout)

        self.set_task_status(task_status)
        self.set_config_summary(config)
        self.set_inventory_summary(inventory)

    def set_task_status(self, task_status: TaskStatus) -> None:
        self.task_summary_label.setText(f"计划任务：{_task_text(task_status)}")
        self.task_button.setText("重装任务（管理员）" if task_status.installed else "安装任务（管理员）")

    def set_config_summary(self, config: dict[str, object]) -> None:
        self.config_summary_label.setText(
            "配置摘要："
            f"max_suites={config.get('max_suites')} | "
            f"interval_minutes={config.get('interval_minutes')} | "
            f"suite_window_seconds={config.get('suite_window_seconds')}"
        )

    def set_cleanup_summary(self, report: dict[str, object]) -> None:
        suite_count = len(report.get("suites", []))
        cleanup_target_count = len(report.get("cleanup_targets", []))
        action_count = len(report.get("actions", []))
        self.cleanup_summary_label.setText(
            f"最近清理：候选 {suite_count} 套 | 目标 {cleanup_target_count} 套 | 动作 {action_count} 条"
        )

    def set_inventory_summary(self, inventory: dict[str, list[dict[str, object]]]) -> None:
        configured = len(inventory.get("configured", []))
        installed = len(inventory.get("installed_candidates", []))
        self.mcp_summary_label.setText(f"MCP 摘要：已配置 {configured} 项 | 候选 {installed} 项")
