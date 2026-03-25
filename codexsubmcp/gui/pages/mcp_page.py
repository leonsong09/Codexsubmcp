from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QHBoxLayout, QVBoxLayout, QWidget


class McpPage(QWidget):
    def __init__(self, *, inventory: dict[str, list[dict[str, object]]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.configured_list = QListWidget()
        self.installed_list = QListWidget()

        for record in inventory.get("configured", []):
            self.configured_list.addItem(str(record.get("name") or ""))
        for record in inventory.get("installed_candidates", []):
            self.installed_list.addItem(str(record.get("name") or ""))

        configured_layout = QVBoxLayout()
        configured_layout.addWidget(QLabel("已配置"))
        configured_layout.addWidget(self.configured_list)

        installed_layout = QVBoxLayout()
        installed_layout.addWidget(QLabel("候选安装"))
        installed_layout.addWidget(self.installed_list)

        layout = QHBoxLayout()
        layout.addLayout(configured_layout)
        layout.addLayout(installed_layout)
        self.setLayout(layout)
