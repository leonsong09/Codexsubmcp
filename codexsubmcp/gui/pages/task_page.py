from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from codexsubmcp.platform.windows.tasks import TaskStatus


def _status_summary(task_status: TaskStatus) -> str:
    if not task_status.installed:
        return f"{task_status.task_name}：未安装"
    enabled_text = "已启用" if task_status.enabled else "已禁用"
    return f"{task_status.task_name}：已安装 / {enabled_text}"


class TaskPage(QWidget):
    def __init__(self, task_status: TaskStatus, task_runner=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel(_status_summary(task_status))
        self.install_button = QPushButton("安装")
        self.uninstall_button = QPushButton("卸载")
        self.enable_button = QPushButton("启用")
        self.disable_button = QPushButton("禁用")
        self.refresh_button = QPushButton("刷新")

        if task_runner is not None:
            self.install_button.clicked.connect(lambda: task_runner.dispatch("task-install"))
            self.uninstall_button.clicked.connect(lambda: task_runner.dispatch("task-uninstall"))
            self.enable_button.clicked.connect(lambda: task_runner.dispatch("task-enable"))
            self.disable_button.clicked.connect(lambda: task_runner.dispatch("task-disable"))
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("task-status"))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("计划任务"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.install_button)
        layout.addWidget(self.uninstall_button)
        layout.addWidget(self.enable_button)
        layout.addWidget(self.disable_button)
        layout.addWidget(self.refresh_button)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_task_status(self, task_status: TaskStatus) -> None:
        self.status_label.setText(_status_summary(task_status))
