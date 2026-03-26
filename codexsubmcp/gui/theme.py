from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

APP_STYLESHEET = """
#shellRoot {
  background-color: #0f172a;
  color: #e2e8f0;
}

QWidget {
  color: #e2e8f0;
  font-size: 13px;
}

QWidget#shellCentral,
QWidget#topBar,
QWidget#activityDrawer {
  background-color: #0f172a;
}

QWidget#activityDrawer {
  border-top: 1px solid #334155;
  padding-top: 8px;
}

QLabel#pageTitle {
  font-size: 18px;
  font-weight: 700;
  color: #f8fafc;
}

QLabel#statusPill,
QLabel#activityPill {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 6px 10px;
  color: #cbd5e1;
}

QLabel#pathLabel {
  color: #94a3b8;
}

QListWidget#navList,
QListWidget,
QTableWidget,
QPlainTextEdit,
QLineEdit,
QSpinBox,
QTabWidget::pane {
  background-color: #111827;
  border: 1px solid #334155;
  border-radius: 12px;
  selection-background-color: #1d4ed8;
  selection-color: #eff6ff;
}

QListWidget#navList {
  min-width: 180px;
  padding: 8px;
}

QListWidget#navList::item {
  padding: 10px 12px;
  margin: 4px 0;
  border-radius: 10px;
}

QListWidget#navList::item:selected {
  background-color: #1d4ed8;
  color: #eff6ff;
  font-weight: 600;
}

QHeaderView::section {
  background-color: #172033;
  color: #cbd5e1;
  border: none;
  border-bottom: 1px solid #334155;
  padding: 8px;
  font-weight: 600;
}

QPushButton {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 8px 12px;
  color: #e2e8f0;
}

QPushButton:hover {
  background-color: #26354d;
  border-color: #475569;
}

QPushButton:pressed {
  background-color: #172033;
}

QPushButton[accent="true"] {
  background-color: #1d4ed8;
  border-color: #2563eb;
  color: #eff6ff;
}

QPushButton[accent="true"]:hover {
  background-color: #2563eb;
}

QPushButton[destructive="true"] {
  background-color: #7f1d1d;
  border-color: #b91c1c;
  color: #fee2e2;
}

QPushButton[destructive="true"]:hover {
  background-color: #991b1b;
}

QTabBar::tab {
  background-color: #172033;
  border: 1px solid #334155;
  border-bottom: none;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  padding: 8px 14px;
  margin-right: 4px;
}

QTabBar::tab:selected {
  background-color: #1d4ed8;
  color: #eff6ff;
}
"""


def apply_theme(window: QMainWindow) -> None:
    app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(APP_STYLESHEET)
    window.setObjectName("shellRoot")
    central = window.centralWidget()
    if isinstance(central, QWidget):
        central.setObjectName("shellCentral")
