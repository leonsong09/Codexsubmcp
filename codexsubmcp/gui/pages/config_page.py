from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QLabel, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget

from codexsubmcp.core.config import validate_config


class ConfigPage(QWidget):
    def __init__(self, *, config: dict[str, object], config_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_path = config_path
        self.editor = QPlainTextEdit(json.dumps(config, indent=2, ensure_ascii=False))
        self.error_label = QLabel("")
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_current_config)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("配置"))
        layout.addWidget(self.editor)
        layout.addWidget(self.error_label)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def save_current_config(self) -> None:
        try:
            payload = json.loads(self.editor.toPlainText())
            validated = validate_config(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self.error_label.setText(str(exc))
            return

        self.config_path.write_text(json.dumps(validated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.error_label.setText("")
