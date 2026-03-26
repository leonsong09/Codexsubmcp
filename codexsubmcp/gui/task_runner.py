from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _TaskRunnable(QRunnable):
    def __init__(
        self,
        *,
        command: str,
        callback: Callable[[], object],
        succeeded,
        failed,
    ) -> None:
        super().__init__()
        self.command = command
        self.callback = callback
        self.succeeded = succeeded
        self.failed = failed

    def run(self) -> None:
        try:
            result = self.callback()
        except Exception as exc:  # noqa: BLE001
            try:
                self.failed.emit(self.command, str(exc))
            except RuntimeError:
                return
            return
        try:
            self.succeeded.emit(self.command, result)
        except RuntimeError:
            return


class TaskRunner(QObject):
    requested = Signal(str, dict)
    started = Signal(str)
    succeeded = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.pool = QThreadPool.globalInstance()

    def dispatch(self, command: str, **payload: object) -> None:
        self.requested.emit(command, payload)

    def run_task(self, command: str, callback: Callable[[], object]) -> None:
        self.started.emit(command)
        self.pool.start(
            _TaskRunnable(
                command=command,
                callback=callback,
                succeeded=self.succeeded,
                failed=self.failed,
            )
        )
