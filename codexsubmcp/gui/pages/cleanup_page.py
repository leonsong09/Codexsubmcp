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


def _classification_reason(suite: dict[str, object]) -> str:
    explicit = str(suite.get("reason") or "").strip()
    if explicit:
        return explicit
    classification = str(suite.get("classification") or "")
    if classification == "orphaned_after_codex_exit":
        return "未找到仍存活的 Codex 父进程，判定为孤儿套件。"
    if classification == "attached_to_live_codex":
        return "检测到仍存活的 Codex 父进程，该套件仍附着在活动会话上。"
    return "暂无判定原因。"


def _risk_hint(suite: dict[str, object]) -> str:
    explicit = str(suite.get("risk_hint") or "").strip()
    if explicit:
        return explicit
    if str(suite.get("action_marker") or "") == "会被清理":
        return "该套件会被清理，请确认没有仍在使用的终端会话。"
    return "该套件当前会被保留，不会执行终止操作。"


def _command_summaries(suite: dict[str, object]) -> list[str]:
    explicit = suite.get("command_summaries")
    if isinstance(explicit, list) and explicit:
        return [str(item) for item in explicit]
    processes = suite.get("processes")
    if not isinstance(processes, list):
        return []
    return [
        str(process.get("command_line") or "")
        for process in processes
        if str(process.get("command_line") or "").strip()
    ]


def _render_process_tree(processes: object) -> list[str]:
    if not isinstance(processes, list) or not processes:
        return ["- 无进程明细"]
    process_map = {int(process["pid"]): process for process in processes if process.get("pid") is not None}
    children: dict[int, list[dict[str, object]]] = {}
    for process in process_map.values():
        parent_pid = int(process.get("ppid") or -1)
        children.setdefault(parent_pid, []).append(process)
    for members in children.values():
        members.sort(key=lambda item: int(item.get("pid") or 0))

    roots = [
        process
        for process in process_map.values()
        if int(process.get("ppid") or -1) not in process_map
    ]
    roots.sort(key=lambda item: int(item.get("pid") or 0))

    lines: list[str] = []

    def walk(process: dict[str, object], prefix: str) -> None:
        pid = process.get("pid")
        name = process.get("name")
        lines.append(f"{prefix}- {pid} {name}")
        for child in children.get(int(pid), []):
            walk(child, prefix + "  ")

    for root in roots:
        walk(root, "")
    return lines or ["- 无进程明细"]


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
        self.suite_table = QTableWidget(0, 6)
        self.suite_table.setHorizontalHeaderLabels(["Suite", "分类", "Root PID", "进程数", "创建时间", "动作"])
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self._suites: list[dict[str, object]] = []

        if task_runner is not None:
            self.preview_button.clicked.connect(lambda: task_runner.dispatch("dry-run", headless=False))
            self.cleanup_button.clicked.connect(lambda: task_runner.dispatch("cleanup", headless=False, yes=True))
        self.copy_table_button.clicked.connect(self.copy_table)
        self.export_table_button.clicked.connect(self.export_table)
        self.suite_table.currentCellChanged.connect(self._render_selected_suite)

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
        layout.addWidget(self.suite_table)
        layout.addWidget(self.detail_view)
        layout.addStretch(1)
        self.setLayout(layout)

    def set_summary(self, text: str) -> None:
        self.summary_label.setText(text)

    def set_busy(self, text: str = "执行中...") -> None:
        self.summary_label.setText(text)

    def set_report(self, payload: dict[str, object]) -> None:
        suites = payload.get("suites") or []
        cleanup_targets = set(payload.get("cleanup_targets") or [])
        self._suites = []
        self.suite_table.setRowCount(len(suites))
        for row, raw_suite in enumerate(suites):
            suite = dict(raw_suite)
            suite_id = str(suite.get("suite_id") or "")
            marker = "会被清理" if suite_id in cleanup_targets else "保留"
            suite["action_marker"] = marker
            self._suites.append(suite)
            values = [
                suite_id,
                str(suite.get("classification") or ""),
                str(suite.get("root_pid") or ""),
                str(suite.get("process_count") or ""),
                str(suite.get("created_at") or ""),
                marker,
            ]
            for column, value in enumerate(values):
                self.suite_table.setItem(row, column, QTableWidgetItem(value))
        actions = payload.get("actions") or []
        self.summary_label.setText("\n".join(str(action) for action in actions) if actions else "未发现需要处理的套件。")
        if self._suites:
            self.suite_table.setCurrentCell(0, 0)
        else:
            self.detail_view.clear()

    def copy_table(self) -> str:
        text = self._table_text()
        QGuiApplication.clipboard().setText(text)
        self.summary_label.setText("已复制清理结果。")
        return text

    def export_table(self) -> Path:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = self.export_dir / "cleanup-suites.tsv"
        path.write_text(self._table_text(), encoding="utf-8")
        self.summary_label.setText(f"已导出：{path}")
        return path

    def _table_text(self) -> str:
        headers = [
            self.suite_table.horizontalHeaderItem(index).text()
            for index in range(self.suite_table.columnCount())
        ]
        rows = ["\t".join(headers)]
        for row in range(self.suite_table.rowCount()):
            rows.append(
                "\t".join(
                    self.suite_table.item(row, column).text() if self.suite_table.item(row, column) else ""
                    for column in range(self.suite_table.columnCount())
                )
            )
        return "\n".join(rows)

    def _render_selected_suite(self, row: int, _column: int, *_args: int) -> None:
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
            "",
            "判定原因：",
            _classification_reason(suite),
            "",
            "风险提示：",
            _risk_hint(suite),
            "",
            "进程树：",
            *_render_process_tree(suite.get("processes")),
            "",
            "命令摘要：",
            *([f"- {item}" for item in _command_summaries(suite)] or ["- 无命令摘要"]),
        ]
        self.detail_view.setPlainText("\n".join(lines))
