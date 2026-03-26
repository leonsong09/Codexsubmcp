from __future__ import annotations

from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QHBoxLayout, QVBoxLayout, QWidget


class McpPage(QWidget):
    def __init__(
        self,
        *,
        inventory: dict[str, list[dict[str, object]]],
        task_runner=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.configured_list = QListWidget()
        self.installed_list = QListWidget()
        self.refresh_button = QPushButton("刷新 MCP")
        self.status_label = QLabel("")

        if task_runner is not None:
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("scan-mcp"))

        configured_layout = QVBoxLayout()
        configured_layout.addWidget(QLabel("已配置"))
        configured_layout.addWidget(self.configured_list)

        installed_layout = QVBoxLayout()
        installed_layout.addWidget(QLabel("候选安装"))
        installed_layout.addWidget(self.installed_list)

        body_layout = QHBoxLayout()
        body_layout.addLayout(configured_layout)
        body_layout.addLayout(installed_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.status_label)
        layout.addLayout(body_layout)
        self.setLayout(layout)

        self.set_inventory(inventory)

    def set_inventory(self, inventory: dict[str, list[dict[str, object]]]) -> None:
        self.configured_list.clear()
        self.installed_list.clear()
        for record in inventory.get("configured", []):
            label = " | ".join(
                part
                for part in [
                    str(record.get("name") or ""),
                    str(record.get("source") or ""),
                    str(record.get("version") or ""),
                    str(record.get("confidence") or ""),
                ]
                if part
            )
            self.configured_list.addItem(label)
        for record in inventory.get("installed_candidates", []):
            label = " | ".join(
                part
                for part in [
                    str(record.get("name") or ""),
                    str(record.get("source") or ""),
                    str(record.get("version") or ""),
                    str(record.get("confidence") or ""),
                ]
                if part
            )
            self.installed_list.addItem(label)
        self.status_label.setText("扫描完成")

    def set_busy(self, text: str = "扫描中...") -> None:
        self.status_label.setText(text)
