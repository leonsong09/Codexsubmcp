from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

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
        self.activity_label = QLabel("")
        self.interval_label = QLabel("巡检间隔：10 分钟")
        self.path_label = QLabel("")
        self.arguments_label = QLabel("")
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 1440)
        self.interval_input.setValue(10)
        self.install_button = QPushButton("安装")
        self.uninstall_button = QPushButton("卸载")
        self.enable_button = QPushButton("启用")
        self.disable_button = QPushButton("禁用")
        self.run_once_button = QPushButton("立即执行一次")
        self.refresh_button = QPushButton("刷新")

        if task_runner is not None:
            self.install_button.clicked.connect(
                lambda: task_runner.dispatch("task-install", interval=self.interval_input.value())
            )
            self.uninstall_button.clicked.connect(lambda: task_runner.dispatch("task-uninstall"))
            self.enable_button.clicked.connect(lambda: task_runner.dispatch("task-enable"))
            self.disable_button.clicked.connect(lambda: task_runner.dispatch("task-disable"))
            self.run_once_button.clicked.connect(lambda: task_runner.dispatch("task-run-once"))
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("task-status"))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("计划任务"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.activity_label)
        layout.addWidget(self.interval_label)
        layout.addWidget(self.interval_input)
        layout.addWidget(self.path_label)
        layout.addWidget(self.arguments_label)
        layout.addWidget(self.install_button)
        layout.addWidget(self.uninstall_button)
        layout.addWidget(self.enable_button)
        layout.addWidget(self.disable_button)
        layout.addWidget(self.run_once_button)
        layout.addWidget(self.refresh_button)
        layout.addStretch(1)
        self.setLayout(layout)
        self.set_task_status(task_status)

    def set_task_status(self, task_status: TaskStatus) -> None:
        self.status_label.setText(_status_summary(task_status))
        executable = str(task_status.executable_path) if task_status.executable_path else "未设置可执行路径"
        arguments = task_status.arguments or "未设置参数"
        self.path_label.setText(f"可执行文件：{executable}")
        self.arguments_label.setText(f"参数：{arguments}")
        self.interval_label.setText(f"巡检间隔：{self.interval_input.value()} 分钟")
        self.activity_label.setText("")

    def set_busy(self, text: str = "执行中...") -> None:
        self.activity_label.setText(text)

    def set_error(self, text: str) -> None:
        self.activity_label.setText(text)
