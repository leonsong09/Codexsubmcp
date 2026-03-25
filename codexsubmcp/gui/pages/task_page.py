from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from codexsubmcp.platform.windows.tasks import TaskStatus


def _status_summary(task_status: TaskStatus) -> str:
    if not task_status.installed:
        return f"{task_status.task_name}：未安装"
    enabled_text = "已启用" if task_status.enabled else "已禁用"
    return f"{task_status.task_name}：已安装 / {enabled_text}"


class TaskPage(QWidget):
    def __init__(self, task_status: TaskStatus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel(_status_summary(task_status))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("计划任务"))
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        self.setLayout(layout)
