from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _build_list_label(record: dict[str, object]) -> str:
    if "tool_signature" in record:
        return f"{record.get('tool_signature')} | instances={record.get('instance_count')} | live_codex={record.get('live_codex_pid_count')}"
    summary = " | ".join(
        part
        for part in [
            str(record.get("name") or ""),
            str(record.get("source") or ""),
            str(record.get("type") or ""),
        ]
        if part
    )
    command = " ".join([str(record.get("command") or ""), *[str(item) for item in record.get("args") or []]]).strip()
    return f"{summary}\n{command}".strip()


class McpPage(QWidget):
    def __init__(
        self,
        *,
        inventory: dict[str, list[dict[str, object]]],
        task_runner=None,
        export_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.export_dir = export_dir or Path.cwd()
        self.configured_list = QListWidget()
        self.running_list = QListWidget()
        self.result_tabs = QTabWidget()
        self.refresh_button = QPushButton("刷新 MCP")
        self.copy_button = QPushButton("复制结果")
        self.export_button = QPushButton("导出结果")
        self.refresh_button.setProperty("accent", True)
        self.status_label = QLabel("")
        self.drift_label = QLabel("")
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self._configured_records: list[dict[str, object]] = []
        self._running_records: list[dict[str, object]] = []
        self._drift: dict[str, object] = {}

        if task_runner is not None:
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("refresh"))
        self.copy_button.clicked.connect(self.copy_current_results)
        self.export_button.clicked.connect(self.export_current_results)
        self.configured_list.currentRowChanged.connect(self._show_configured_detail)
        self.running_list.currentRowChanged.connect(self._show_running_detail)

        configured_tab = QWidget()
        configured_layout = QVBoxLayout()
        configured_layout.addWidget(self.configured_list)
        configured_tab.setLayout(configured_layout)

        running_tab = QWidget()
        running_layout = QVBoxLayout()
        running_layout.addWidget(self.running_list)
        running_tab.setLayout(running_layout)

        self.result_tabs.addTab(configured_tab, "已配置")
        self.result_tabs.addTab(running_tab, "运行中")

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.copy_button)
        toolbar.addWidget(self.export_button)

        body_layout = QHBoxLayout()
        body_layout.addWidget(self.result_tabs, 2)
        body_layout.addWidget(self.detail_view, 3)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.drift_label)
        layout.addLayout(body_layout)
        self.setLayout(layout)

        self.set_inventory(inventory)

    def set_inventory(self, inventory: dict[str, list[dict[str, object]]]) -> None:
        self._configured_records = list(inventory.get("configured", []))
        self._running_records = list(inventory.get("running", []))
        self._drift = dict(inventory.get("drift") or {})
        self.configured_list.clear()
        self.running_list.clear()
        for record in self._configured_records:
            self.configured_list.addItem(_build_list_label(record))
        for record in self._running_records:
            self.running_list.addItem(_build_list_label(record))
        drift_total = len(self._drift.get("configured_not_running", [])) + len(
            self._drift.get("running_not_configured", [])
        )
        self.status_label.setText(
            f"已刷新：已配置 {len(self._configured_records)} 项，运行中 {len(self._running_records)} 类，drift {drift_total} 项"
        )
        self.drift_label.setText(
            f"configured_not_running={self._drift.get('configured_not_running', [])} | "
            f"running_not_configured={self._drift.get('running_not_configured', [])}"
        )
        self.detail_view.clear()
        if self._configured_records:
            self.result_tabs.setCurrentIndex(0)
            self.configured_list.setCurrentRow(0)
        elif self._running_records:
            self.result_tabs.setCurrentIndex(1)
            self.running_list.setCurrentRow(0)

    def set_busy(self, text: str = "刷新中...") -> None:
        self.status_label.setText(text)

    def copy_current_results(self) -> str:
        text = json.dumps(self._inventory_payload(), ensure_ascii=False, indent=2)
        QGuiApplication.clipboard().setText(text)
        self.status_label.setText("已复制 MCP 结果。")
        return text

    def export_current_results(self) -> Path:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = self.export_dir / "mcp-inventory.json"
        path.write_text(json.dumps(self._inventory_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.status_label.setText(f"已导出：{path}")
        return path

    def _inventory_payload(self) -> dict[str, object]:
        return {
            "configured": self._configured_records,
            "running": self._running_records,
            "drift": self._drift,
        }

    def _render_detail(self, record: dict[str, object]) -> None:
        if "tool_signature" in record:
            lines = [
                f"tool_signature={record.get('tool_signature')}",
                f"instance_count={record.get('instance_count')}",
                f"live_codex_pid_count={record.get('live_codex_pid_count')}",
            ]
        else:
            lines = [
                f"name={record.get('name')}",
                f"source={record.get('source')}",
                f"type={record.get('type')}",
                f"command={record.get('command')}",
                f"args={record.get('args')}",
                f"env_keys={record.get('env_keys')}",
                f"startup_timeout_ms={record.get('startup_timeout_ms')}",
                f"tool_timeout_sec={record.get('tool_timeout_sec')}",
                f"path={record.get('path')}",
            ]
        self.detail_view.setPlainText("\n".join(lines))

    def _show_configured_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._configured_records):
            return
        self.result_tabs.setCurrentIndex(0)
        self._render_detail(self._configured_records[row])

    def _show_running_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._running_records):
            return
        self.result_tabs.setCurrentIndex(1)
        self._render_detail(self._running_records[row])
