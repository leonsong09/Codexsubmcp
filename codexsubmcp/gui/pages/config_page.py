from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from codexsubmcp.core.config import DEFAULT_CONFIG, validate_config


def _format_config(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _patterns_to_text(patterns: object) -> str:
    if not isinstance(patterns, list):
        return ""
    return "\n".join(str(item) for item in patterns)


def _text_to_patterns(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


class ConfigPage(QWidget):
    def __init__(
        self,
        *,
        config: dict[str, object],
        config_path: Path,
        export_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config_path = config_path
        self.export_dir = export_dir or (config_path.parent / "exports")
        self.mode_tabs = QTabWidget()
        self.editor = QPlainTextEdit()
        self.error_label = QLabel("")
        self.validate_button = QPushButton("校验配置")
        self.reset_button = QPushButton("恢复默认")
        self.import_button = QPushButton("导入配置")
        self.export_button = QPushButton("导出配置")
        self.save_button = QPushButton("保存配置")
        self.validate_button.setProperty("accent", True)
        self.save_button.setProperty("accent", True)

        self.task_name_input = QLineEdit()
        self.interval_minutes_input = QSpinBox()
        self.interval_minutes_input.setRange(1, 1440)
        self.max_suites_input = QSpinBox()
        self.max_suites_input.setRange(1, 999)
        self.suite_window_seconds_input = QSpinBox()
        self.suite_window_seconds_input.setRange(1, 3600)
        self.codex_patterns_input = QPlainTextEdit()
        self.candidate_patterns_input = QPlainTextEdit()

        self.mode_tabs.currentChanged.connect(self._sync_views_for_mode)
        self.validate_button.clicked.connect(self.validate_current_config)
        self.reset_button.clicked.connect(self.reset_to_default)
        self.import_button.clicked.connect(self.import_config)
        self.export_button.clicked.connect(self.export_config)
        self.save_button.clicked.connect(self.save_current_config)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.validate_button)
        actions.addWidget(self.reset_button)
        actions.addWidget(self.import_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.save_button)

        form_page = QWidget()
        form_layout = QFormLayout()
        form_layout.addRow("任务名", self.task_name_input)
        form_layout.addRow("巡检间隔（分钟）", self.interval_minutes_input)
        form_layout.addRow("最大套件数", self.max_suites_input)
        form_layout.addRow("聚类窗口（秒）", self.suite_window_seconds_input)
        form_layout.addRow("Codex Patterns", self.codex_patterns_input)
        form_layout.addRow("Candidate Patterns", self.candidate_patterns_input)
        form_page.setLayout(form_layout)

        json_page = QWidget()
        json_layout = QVBoxLayout()
        json_layout.addWidget(self.editor)
        json_page.setLayout(json_layout)

        self.mode_tabs.addTab(form_page, "表单")
        self.mode_tabs.addTab(json_page, "JSON")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("配置"))
        layout.addLayout(actions)
        layout.addWidget(self.mode_tabs)
        layout.addWidget(self.error_label)
        self.setLayout(layout)

        self._set_payload({**DEFAULT_CONFIG, **config})

    def validate_current_config(self) -> dict[str, object] | None:
        validated = self._validated_payload()
        if validated is None:
            return None
        self._set_payload(validated)
        self.error_label.setText("配置有效。")
        return validated

    def reset_to_default(self) -> None:
        self._set_payload(DEFAULT_CONFIG)
        self.error_label.setText("已恢复默认配置。")

    def import_config(self) -> Path | None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            str(self.config_path.parent),
            "JSON Files (*.json)",
        )
        if not selected_path:
            return None
        path = Path(selected_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validated = validate_config(payload)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.error_label.setText(str(exc))
            return None
        self._set_payload(validated)
        self.error_label.setText(f"已导入：{path}")
        return path

    def export_config(self) -> Path | None:
        validated = self._validated_payload()
        if validated is None:
            return None
        self.export_dir.mkdir(parents=True, exist_ok=True)
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            str(self.export_dir / self.config_path.name),
            "JSON Files (*.json)",
        )
        if not selected_path:
            return None
        path = Path(selected_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_format_config(validated) + "\n", encoding="utf-8")
        self.error_label.setText(f"已导出：{path}")
        return path

    def save_current_config(self) -> None:
        validated = self._validated_payload()
        if validated is None:
            return
        self._set_payload(validated)
        self.config_path.write_text(_format_config(validated) + "\n", encoding="utf-8")
        self.error_label.setText("已保存配置。")

    def _sync_views_for_mode(self, index: int) -> None:
        if index == 1:
            try:
                validated = validate_config(self._form_payload())
            except ValueError as exc:
                self.error_label.setText(str(exc))
                return
            self.editor.setPlainText(_format_config(validated))
            return
        payload = self._payload_from_editor()
        if payload is None:
            return
        self._populate_form(payload)

    def _set_payload(self, payload: dict[str, object]) -> None:
        validated = validate_config(payload)
        self._populate_form(validated)
        self.editor.setPlainText(_format_config(validated))

    def _populate_form(self, payload: dict[str, object]) -> None:
        self.task_name_input.setText(str(payload.get("task_name") or ""))
        self.interval_minutes_input.setValue(int(payload.get("interval_minutes") or 10))
        self.max_suites_input.setValue(int(payload.get("max_suites") or 6))
        self.suite_window_seconds_input.setValue(int(payload.get("suite_window_seconds") or 15))
        self.codex_patterns_input.setPlainText(_patterns_to_text(payload.get("codex_patterns")))
        self.candidate_patterns_input.setPlainText(_patterns_to_text(payload.get("candidate_patterns")))

    def _form_payload(self) -> dict[str, object]:
        return {
            "task_name": self.task_name_input.text().strip() or DEFAULT_CONFIG["task_name"],
            "interval_minutes": self.interval_minutes_input.value(),
            "max_suites": self.max_suites_input.value(),
            "suite_window_seconds": self.suite_window_seconds_input.value(),
            "codex_patterns": _text_to_patterns(self.codex_patterns_input.toPlainText()),
            "candidate_patterns": _text_to_patterns(self.candidate_patterns_input.toPlainText()),
        }

    def _payload_from_editor(self) -> dict[str, object] | None:
        try:
            payload = json.loads(self.editor.toPlainText())
            return validate_config(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self.error_label.setText(str(exc))
            return None

    def _validated_payload(self) -> dict[str, object] | None:
        if self.mode_tabs.currentIndex() == 0:
            try:
                return validate_config(self._form_payload())
            except ValueError as exc:
                self.error_label.setText(str(exc))
                return None
        return self._payload_from_editor()
