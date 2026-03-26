from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class CleanupPage(QWidget):
    def __init__(self, task_runner=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview_button = QPushButton("立即预览")
        self.cleanup_button = QPushButton("立即清理")
        self.summary_label = QLabel("尚未执行清理。")

        if task_runner is not None:
            self.preview_button.clicked.connect(
                lambda: task_runner.dispatch("dry-run", headless=False)
            )
            self.cleanup_button.clicked.connect(
                lambda: task_runner.dispatch("cleanup", headless=False, yes=True)
            )

        layout = QVBoxLayout()
        layout.addWidget(QLabel("清理"))
        layout.addWidget(self.preview_button)
        layout.addWidget(self.cleanup_button)
        layout.addWidget(self.summary_label)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)
