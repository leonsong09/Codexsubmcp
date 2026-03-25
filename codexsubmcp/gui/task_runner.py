from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class TaskRunner(QObject):
    requested = Signal(str, dict)

    def dispatch(self, command: str, **payload: object) -> None:
        self.requested.emit(command, payload)
