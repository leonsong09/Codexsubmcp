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
    summary = " | ".join(
        part
        for part in [
            str(record.get("name") or ""),
            str(record.get("source") or ""),
            str(record.get("version") or ""),
            str(record.get("confidence") or ""),
        ]
        if part
    )
    location = str(record.get("path") or record.get("command") or record.get("notes") or "").strip()
    if not location:
        return summary
    return f"{summary}\n{location}"


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
        self.installed_list = QListWidget()
        self.result_tabs = QTabWidget()
        self.refresh_button = QPushButton("刷新 MCP")
        self.copy_button = QPushButton("复制结果")
        self.export_button = QPushButton("导出结果")
        self.refresh_button.setProperty("accent", True)
        self.status_label = QLabel("")
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self._configured_records: list[dict[str, object]] = []
        self._installed_records: list[dict[str, object]] = []

        if task_runner is not None:
            self.refresh_button.clicked.connect(lambda: task_runner.dispatch("scan-mcp"))
        self.copy_button.clicked.connect(self.copy_current_results)
        self.export_button.clicked.connect(self.export_current_results)
        self.configured_list.currentRowChanged.connect(self._show_configured_detail)
        self.installed_list.currentRowChanged.connect(self._show_installed_detail)

        configured_tab = QWidget()
        configured_layout = QVBoxLayout()
        configured_layout.addWidget(self.configured_list)
        configured_tab.setLayout(configured_layout)

        installed_tab = QWidget()
        installed_layout = QVBoxLayout()
        installed_layout.addWidget(self.installed_list)
        installed_tab.setLayout(installed_layout)

        self.result_tabs.addTab(configured_tab, "已配置可用")
        self.result_tabs.addTab(installed_tab, "疑似已安装")

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
        layout.addLayout(body_layout)
        self.setLayout(layout)

        self.set_inventory(inventory)

    def set_inventory(self, inventory: dict[str, list[dict[str, object]]]) -> None:
        self._configured_records = list(inventory.get("configured", []))
        self._installed_records = list(inventory.get("installed_candidates", []))
        self.configured_list.clear()
        self.installed_list.clear()
        for record in self._configured_records:
            self.configured_list.addItem(_build_list_label(record))
        for record in self._installed_records:
            self.installed_list.addItem(_build_list_label(record))
        self.status_label.setText(
            f"扫描完成：已配置 {len(self._configured_records)} 项，候选 {len(self._installed_records)} 项"
        )
        self.detail_view.clear()
        if self._configured_records:
            self.result_tabs.setCurrentIndex(0)
            self.configured_list.setCurrentRow(0)
        elif self._installed_records:
            self.result_tabs.setCurrentIndex(1)
            self.installed_list.setCurrentRow(0)

    def set_busy(self, text: str = "扫描中...") -> None:
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

    def _inventory_payload(self) -> dict[str, list[dict[str, object]]]:
        return {
            "configured": self._configured_records,
            "installed_candidates": self._installed_records,
        }

    def _render_detail(self, record: dict[str, object]) -> None:
        lines = [
            f"name={record.get('name')}",
            f"source={record.get('source')}",
            f"version={record.get('version')}",
            f"confidence={record.get('confidence')}",
            f"command={record.get('command')}",
            f"path={record.get('path')}",
            f"notes={record.get('notes')}",
        ]
        self.detail_view.setPlainText("\n".join(lines))

    def _show_configured_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._configured_records):
            return
        self.result_tabs.setCurrentIndex(0)
        self._render_detail(self._configured_records[row])

    def _show_installed_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._installed_records):
            return
        self.result_tabs.setCurrentIndex(1)
        self._render_detail(self._installed_records[row])
