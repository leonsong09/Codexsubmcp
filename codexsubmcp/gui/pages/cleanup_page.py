from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _reason(target: dict[str, object]) -> str:
    return str(target.get("reason") or "暂无判定原因。")


def _risk_hint(target: dict[str, object]) -> str:
    return str(target.get("risk_hint") or "暂无风险提示。")


class CleanupPage(QWidget):
    def __init__(
        self,
        task_runner=None,
        *,
        export_dir: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.export_dir = export_dir or Path.cwd()
        self.preview_button = QPushButton("立即预览")
        self.cleanup_button = QPushButton("立即清理（管理员）")
        self.copy_table_button = QPushButton("复制结果")
        self.export_table_button = QPushButton("导出结果")
        self.preview_button.setProperty("accent", True)
        self.cleanup_button.setProperty("destructive", True)
        self.summary_label = QLabel("尚未执行清理。")
        self.target_table = QTableWidget(0, 6)
        self.target_table.setHorizontalHeaderLabels(["Target", "类型", "Kill PID", "进程数", "创建时间", "动作"])
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self._targets: list[dict[str, object]] = []

        if task_runner is not None:
            self.preview_button.clicked.connect(lambda: task_runner.dispatch("preview", headless=False))
            self.cleanup_button.clicked.connect(lambda: task_runner.dispatch("cleanup", headless=False, yes=True))
        self.copy_table_button.clicked.connect(self.copy_table)
        self.export_table_button.clicked.connect(self.export_table)
        self.target_table.currentCellChanged.connect(self._render_selected_target)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.preview_button)
        actions.addWidget(self.cleanup_button)
        actions.addWidget(self.copy_table_button)
        actions.addWidget(self.export_table_button)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("清理"))
        layout.addLayout(actions)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.target_table)
        layout.addWidget(self.detail_view)
        layout.addStretch(1)
        self.setLayout(layout)
        self.set_actions_enabled(preview_enabled=False, cleanup_enabled=False)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def set_busy(self, text: str = "执行中...") -> None:
        self.summary_label.setText(text)

    def set_actions_enabled(self, *, preview_enabled: bool, cleanup_enabled: bool) -> None:
        self.preview_button.setEnabled(preview_enabled)
        self.cleanup_button.setEnabled(cleanup_enabled)

    def set_preview(self, payload: dict[str, object]) -> None:
        targets = list(payload.get("targets") or [])
        self._targets = [dict(item) for item in targets]
        self.target_table.setRowCount(len(self._targets))
        for row, target in enumerate(self._targets):
            values = [
                str(target.get("target_id") or ""),
                str(target.get("target_type") or ""),
                str(target.get("kill_pid") or ""),
                str(len(target.get("process_ids") or [])),
                str(target.get("created_at") or ""),
                "待清理",
            ]
            for column, value in enumerate(values):
                self.target_table.setItem(row, column, QTableWidgetItem(value))
        summary = payload.get("summary") or {}
        if isinstance(summary, dict):
            self.summary_label.setText(f"预览完成：orphan 目标 {summary.get('target_count', 0)} 个")
        else:
            self.summary_label.setText("预览完成。")
        if self._targets:
            self.target_table.setCurrentCell(0, 0)
        else:
            self.detail_view.clear()

    def set_report(self, payload: dict[str, object]) -> None:
        self.set_preview(payload)

    def copy_table(self) -> str:
        text = self._table_text()
        QGuiApplication.clipboard().setText(text)
        self.summary_label.setText("已复制清理结果。")
        return text

    def export_table(self) -> Path:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = self.export_dir / "cleanup-targets.tsv"
        path.write_text(self._table_text(), encoding="utf-8")
        self.summary_label.setText(f"已导出：{path}")
        return path

    def _table_text(self) -> str:
        headers = [
            self.target_table.horizontalHeaderItem(index).text()
            for index in range(self.target_table.columnCount())
        ]
        rows = ["\t".join(headers)]
        for row in range(self.target_table.rowCount()):
            rows.append(
                "\t".join(
                    self.target_table.item(row, column).text() if self.target_table.item(row, column) else ""
                    for column in range(self.target_table.columnCount())
                )
            )
        return "\n".join(rows)

    def _render_selected_target(self, row: int, _column: int, *_args: int) -> None:
        if row < 0 or row >= len(self._targets):
            self.detail_view.clear()
            return
        target = self._targets[row]
        lines = [
            f"target_id={target.get('target_id')}",
            f"target_type={target.get('target_type')}",
            f"kill_pid={target.get('kill_pid')}",
            f"process_ids={target.get('process_ids')}",
            f"created_at={target.get('created_at')}",
            "",
            "判定原因：",
            _reason(target),
            "",
            "风险提示：",
            _risk_hint(target),
        ]
        self.detail_view.setPlainText("\n".join(lines))
