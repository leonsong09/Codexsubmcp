from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

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
        self.next_run_label = QLabel("下次运行：未知")
        self.path_label = QLabel("")
        self.arguments_label = QLabel("")
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 1440)
        self.interval_input.setValue(10)
        self.install_button = QPushButton("安装（管理员）")
        self.reinstall_button = QPushButton("重装（管理员）")
        self.uninstall_button = QPushButton("卸载（管理员）")
        self.enable_button = QPushButton("启用（管理员）")
        self.disable_button = QPushButton("禁用（管理员）")
        self.run_once_button = QPushButton("立即执行一次")
        self.refresh_button = QPushButton("刷新")
        self.install_button.setProperty("accent", True)
        self.reinstall_button.setProperty("accent", True)
        self.uninstall_button.setProperty("destructive", True)
        self.enable_button.setProperty("accent", True)
        self.disable_button.setProperty("destructive", True)
        self.run_once_button.setProperty("accent", True)

        if task_runner is not None:
            self.install_button.clicked.connect(
                lambda: task_runner.dispatch("task-install", interval=self.interval_input.value())
            )
            self.reinstall_button.clicked.connect(
                lambda: task_runner.dispatch("task-install", interval=self.interval_input.value())
            )
            self.uninstall_button.clicked.connect(lambda: task_runner.dispatch("task-uninstall"))
            self.enable_button.clicked.connect(lambda: task_runner.dispatch("task-enable"))
            self.disable_button.clicked.connect(lambda: task_runner.dispatch("task-disable"))
            self.run_once_button.clicked.connect(lambda: task_runner.dispatch("task-run-once"))
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("task-status"))

        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)
        actions.addWidget(self.install_button, 0, 0)
        actions.addWidget(self.reinstall_button, 0, 1)
        actions.addWidget(self.uninstall_button, 0, 2)
        actions.addWidget(self.enable_button, 1, 0)
        actions.addWidget(self.disable_button, 1, 1)
        actions.addWidget(self.run_once_button, 1, 2)
        actions.addWidget(self.refresh_button, 2, 0, 1, 3)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("计划任务"))
        layout.addWidget(self.status_label)
        layout.addWidget(self.activity_label)
        layout.addWidget(self.interval_label)
        layout.addWidget(self.next_run_label)
        layout.addWidget(self.interval_input)
        layout.addWidget(self.path_label)
        layout.addWidget(self.arguments_label)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.setLayout(layout)
        self.set_task_status(task_status)

    def set_task_status(self, task_status: TaskStatus) -> None:
        self.status_label.setText(_status_summary(task_status))
        if task_status.interval_minutes is not None:
            self.interval_input.setValue(task_status.interval_minutes)
        executable = str(task_status.executable_path) if task_status.executable_path else "未设置可执行路径"
        arguments = task_status.arguments or "未设置参数"
        next_run = task_status.next_run_time or "未知"
        self.path_label.setText(f"稳定安装路径：{executable}")
        self.arguments_label.setText(f"参数：{arguments}")
        self.interval_label.setText(f"巡检间隔：{self.interval_input.value()} 分钟")
        self.next_run_label.setText(f"下次运行：{next_run}")
        self.activity_label.setText("")

    def set_busy(self, text: str = "执行中...") -> None:
        self.activity_label.setText(text)

    def set_error(self, text: str) -> None:
        self.activity_label.setText(text)
