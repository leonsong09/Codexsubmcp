from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QListWidget, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget


class LogPage(QWidget):
    def __init__(self, *, log_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.log_dir = log_dir
        self.log_list = QListWidget()
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)

        self.log_list.currentRowChanged.connect(self._show_selected_log)

        list_layout = QVBoxLayout()
        list_layout.addWidget(self.log_list)

        detail_layout = QVBoxLayout()
        detail_layout.addWidget(self.detail_view)

        layout = QHBoxLayout()
        layout.addLayout(list_layout)
        layout.addLayout(detail_layout)
        self.setLayout(layout)

        self.refresh_logs()

    def refresh_logs(self) -> None:
        self.log_list.clear()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.log_dir.glob("*")):
            if path.is_file():
                self.log_list.addItem(path.name)

    def _show_selected_log(self, row: int) -> None:
        if row < 0:
            self.detail_view.clear()
            return
        name = self.log_list.item(row).text()
        self.detail_view.setPlainText((self.log_dir / name).read_text(encoding="utf-8"))
