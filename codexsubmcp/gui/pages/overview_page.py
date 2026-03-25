from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class OverviewPage(QWidget):
    def __init__(self, task_runner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview_button = QPushButton("立即预览")
        self.preview_button.clicked.connect(lambda: task_runner.dispatch("dry-run", headless=False))

        layout = QVBoxLayout()
        layout.addWidget(QLabel("总览"))
        layout.addWidget(self.preview_button)
        layout.addStretch(1)
        self.setLayout(layout)
