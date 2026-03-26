from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ALL_ACTIONS = "全部动作"
_ALL_STATUSES = "全部状态"


@dataclass(frozen=True)
class _LogRecord:
    path: Path
    action: str
    status: str
    content: str

    @property
    def label(self) -> str:
        return f"{self.action} | {self.status} | {self.path.name}"


def _infer_action(path: Path, payload: object) -> str:
    if isinstance(payload, dict):
        command = str(payload.get("command") or "").strip()
        if command:
            return command
    stem = path.stem
    for known_command in ("dry-run", "run-once", "cleanup"):
        if stem.startswith(known_command):
            return known_command
    return stem.split("-", 1)[0] if "-" in stem else stem


def _infer_status(payload: object) -> str:
    if not isinstance(payload, dict):
        return "unknown"
    explicit = str(payload.get("status") or "").strip()
    if explicit:
        return explicit
    if payload.get("error") or payload.get("ok") is False:
        return "failure"
    return "success"


def _build_record(path: Path) -> _LogRecord:
    content = path.read_text(encoding="utf-8")
    payload: object = None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = None
    return _LogRecord(
        path=path,
        action=_infer_action(path, payload),
        status=_infer_status(payload),
        content=content,
    )


class LogPage(QWidget):
    def __init__(
        self,
        *,
        log_dir: Path,
        export_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.log_dir = log_dir
        self.export_dir = export_dir or (log_dir.parent / "exports")
        self._records: list[_LogRecord] = []
        self._filtered_records: list[_LogRecord] = []

        self.refresh_button = QPushButton("刷新日志")
        self.action_filter = QComboBox()
        self.status_filter = QComboBox()
        self.export_button = QPushButton("导出当前日志")
        self.open_dir_button = QPushButton("打开日志目录")
        self.refresh_button.setProperty("accent", True)
        self.status_label = QLabel("尚未加载日志。")
        self.log_list = QListWidget()
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)

        self.refresh_button.clicked.connect(self.refresh_logs)
        self.action_filter.currentTextChanged.connect(self._apply_filters)
        self.status_filter.currentTextChanged.connect(self._apply_filters)
        self.export_button.clicked.connect(self.export_selected_log)
        self.open_dir_button.clicked.connect(self.open_log_directory)
        self.log_list.currentRowChanged.connect(self._show_selected_log)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.action_filter)
        toolbar.addWidget(self.status_filter)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.open_dir_button)

        list_layout = QVBoxLayout()
        list_layout.addLayout(toolbar)
        list_layout.addWidget(self.status_label)
        list_layout.addWidget(self.log_list)

        detail_layout = QVBoxLayout()
        detail_layout.addWidget(self.detail_view)

        layout = QHBoxLayout()
        layout.addLayout(list_layout, 1)
        layout.addLayout(detail_layout, 2)
        self.setLayout(layout)

        self.refresh_logs()

    def refresh_logs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._records = [
            _build_record(path)
            for path in sorted(self.log_dir.glob("*"), reverse=True)
            if path.is_file()
        ]
        self._reset_filter_options(
            self.action_filter,
            _ALL_ACTIONS,
            sorted({record.action for record in self._records}),
        )
        self._reset_filter_options(
            self.status_filter,
            _ALL_STATUSES,
            sorted({record.status for record in self._records}),
        )
        self._apply_filters()

    def export_selected_log(self) -> Path | None:
        record = self._selected_record()
        if record is None:
            self.status_label.setText("请先选择一条日志。")
            return None
        self.export_dir.mkdir(parents=True, exist_ok=True)
        target = self.export_dir / record.path.name
        shutil.copy2(record.path, target)
        self.status_label.setText(f"已导出：{target}")
        return target

    def open_log_directory(self) -> bool:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_dir)))
        self.status_label.setText("已打开日志目录。" if opened else "打开日志目录失败。")
        return opened

    def _reset_filter_options(self, combo: QComboBox, all_label: str, values: list[str]) -> None:
        current = combo.currentText() or all_label
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label)
        for value in values:
            combo.addItem(value)
        combo.setCurrentText(current if combo.findText(current) >= 0 else all_label)
        combo.blockSignals(False)

    def _apply_filters(self) -> None:
        action_filter = self.action_filter.currentText() or _ALL_ACTIONS
        status_filter = self.status_filter.currentText() or _ALL_STATUSES
        self._filtered_records = [
            record
            for record in self._records
            if (action_filter == _ALL_ACTIONS or record.action == action_filter)
            and (status_filter == _ALL_STATUSES or record.status == status_filter)
        ]
        self.log_list.blockSignals(True)
        self.log_list.clear()
        for record in self._filtered_records:
            self.log_list.addItem(record.label)
        self.log_list.blockSignals(False)
        self.status_label.setText(f"显示 {len(self._filtered_records)} / {len(self._records)} 条日志")
        if self._filtered_records:
            self.log_list.setCurrentRow(0)
            return
        self.detail_view.clear()

    def _selected_record(self) -> _LogRecord | None:
        row = self.log_list.currentRow()
        if row < 0 or row >= len(self._filtered_records):
            return None
        return self._filtered_records[row]

    def _show_selected_log(self, row: int) -> None:
        if row < 0 or row >= len(self._filtered_records):
            self.detail_view.clear()
            return
        self.detail_view.setPlainText(self._filtered_records[row].content)
