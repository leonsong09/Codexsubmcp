from __future__ import annotations

from PySide6.QtWidgets import QApplication

from codexsubmcp.gui.main_window import MainWindow


def create_application() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def launch_gui() -> int:
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
