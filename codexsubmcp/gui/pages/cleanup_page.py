from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget


class CleanupPage(QWidget):
    def __init__(self, task_runner=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview_button = QPushButton("立即预览")
        self.cleanup_button = QPushButton("立即清理")
        self.summary_label = QLabel("尚未执行清理。")
        self.suite_list = QListWidget()
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self._suites: list[dict[str, object]] = []

        if task_runner is not None:
            self.preview_button.clicked.connect(
                lambda: task_runner.dispatch("dry-run", headless=False)
            )
            self.cleanup_button.clicked.connect(
                lambda: task_runner.dispatch("cleanup", headless=False, yes=True)
            )
        self.suite_list.currentRowChanged.connect(self._render_selected_suite)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("清理"))
        layout.addWidget(self.preview_button)
        layout.addWidget(self.cleanup_button)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.suite_list)
        layout.addWidget(self.detail_view)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def set_busy(self, text: str = "执行中...") -> None:
        self.summary_label.setText(text)

    def set_report(self, payload: dict[str, object]) -> None:
        suites = payload.get("suites") or []
        self._suites = list(suites)
        cleanup_targets = set(payload.get("cleanup_targets") or [])
        self.suite_list.clear()
        for suite in self._suites:
            suite_id = str(suite.get("suite_id") or "")
            marker = "会被清理" if suite_id in cleanup_targets else "保留"
            self.suite_list.addItem(f"{suite_id} | {marker}")
        actions = payload.get("actions") or []
        self.summary_label.setText("\n".join(str(action) for action in actions) if actions else "未发现需要处理的套件。")
        if self._suites:
            self.suite_list.setCurrentRow(0)
        else:
            self.detail_view.clear()

    def _render_selected_suite(self, row: int) -> None:
        if row < 0 or row >= len(self._suites):
            self.detail_view.clear()
            return
        suite = self._suites[row]
        lines = [
            f"suite_id={suite.get('suite_id')}",
            f"classification={suite.get('classification')}",
            f"root_pid={suite.get('root_pid')}",
            f"process_count={suite.get('process_count')}",
            f"created_at={suite.get('created_at')}",
            f"process_ids={suite.get('process_ids')}",
        ]
        self.detail_view.setPlainText("\n".join(lines))
