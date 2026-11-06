"""Best-effort expiry of this process's clipboard entry; no persistent secrets."""

import hashlib
import secrets
import sys
import time
from dataclasses import dataclass

from PySide6.QtCore import QMimeData, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication

CLEAR_SECONDS = (0, 30, 60, 120)
TOKEN_MIME = "application/x-password-generator-copy-token"


def elapsed_ms():
    if sys.platform == "win32":
        import ctypes

        clock = ctypes.windll.kernel32.GetTickCount64
        clock.restype = ctypes.c_ulonglong
        return clock()
    if hasattr(time, "CLOCK_BOOTTIME"):
        return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
    return int(time.monotonic() * 1000)


@dataclass(frozen=True)
class PendingCopy:
    token: str
    digest: bytes
    deadline: int


class ClipboardGuard:
    """Adapter matches returns True/False, or None when access is unavailable."""

    def __init__(
        self, port, clock=elapsed_ms, token_factory=lambda: secrets.token_hex(16)
    ):
        self.port = port
        self.clock = clock
        self.token_factory = token_factory
        self.seconds = 0
        self.pending = None
        self.generation = 0

    def set_policy(self, seconds):
        self.seconds = (
            seconds if type(seconds) is int and seconds in CLEAR_SECONDS else 0
        )
        if not self.seconds:
            self.cancel()

    def cancel(self):
        self.generation += 1
        self.pending = None

    def copy(self, text):
        if not text:
            return False
        self.cancel()
        token = self.token_factory() if self.seconds else None
        generation = self.generation
        if not self.port.write(text, token):
            return False
        if token is not None and self.generation == generation:
            self.pending = PendingCopy(
                token,
                hashlib.sha256(text.encode("utf-8")).digest(),
                self.clock() + self.seconds * 1000,
            )
        return True

    def changed(self):
        pending = self.pending
        if (
            pending
            and self.port.matches(pending, content=False) is False
            and self.pending is pending
        ):
            self.cancel()

    def tick(self):
        pending = self.pending
        if pending is None:
            return None
        remaining = pending.deadline - self.clock()
        if remaining > 0:
            return remaining
        matches = self.port.matches(pending, content=True)
        if self.pending is not pending:
            return None
        if matches is False:
            self.cancel()
        elif matches is True:
            # clear() may synchronously emit clipboard-change callbacks.
            generation = self.generation
            self.pending = None
            if not self.port.clear() and self.generation == generation:
                self.pending = pending
        # No polling while unavailable: retry on a focus/change event instead.
        return None


class QtClipboardPort:
    def __init__(self, clipboard=None):
        self.clipboard = (
            clipboard if clipboard is not None else QApplication.clipboard()
        )

    def write(self, text, token):
        data = QMimeData()
        data.setText(text)
        if token is not None:
            data.setData(TOKEN_MIME, token.encode("ascii"))
        try:
            self.clipboard.setMimeData(data)
            return True
        except RuntimeError:
            return False

    def matches(self, pending, *, content):
        app = QApplication.instance()
        if (
            app.platformName().startswith("wayland")
            and app.applicationState() != Qt.ApplicationActive
        ):
            return None
        try:
            if not self.clipboard.ownsClipboard():
                return False
            data = self.clipboard.mimeData()
            if data is None or bytes(data.data(TOKEN_MIME)) != pending.token.encode(
                "ascii"
            ):
                return False
            if not content:
                return True
            return (
                data.hasText()
                and hashlib.sha256(data.text().encode("utf-8")).digest()
                == pending.digest
            )
        except RuntimeError:
            return None

    def clear(self):
        try:
            self.clipboard.clear()
            return True
        except RuntimeError:
            return False


class ClipboardController(QObject):
    def __init__(self, seconds=0, parent=None, port=None, clock=elapsed_ms):
        super().__init__(parent)
        self.guard = ClipboardGuard(port or QtClipboardPort(), clock)
        self.guard.set_policy(seconds)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.check)
        self.alive = True
        QApplication.clipboard().dataChanged.connect(self.changed)
        QApplication.instance().applicationStateChanged.connect(self.focus_changed)

    def set_policy(self, seconds):
        self.guard.set_policy(seconds)
        self.check()

    def copy(self, text):
        copied = self.guard.copy(text)
        self.check()
        return copied

    def check(self):
        self.timer.stop()
        if self.alive:
            remaining = self.guard.tick()
            if remaining is not None:
                # Qt's timer clock may exclude suspend; bound the next elapsed-time
                # check after wake without polling clipboard contents before expiry.
                self.timer.start(max(1, min(1000, remaining)))

    def changed(self):
        if self.alive:
            self.guard.changed()
            self.check()

    def focus_changed(self, state):
        if state == Qt.ApplicationActive:
            self.check()

    def dispose(self):
        if not self.alive:
            return
        self.alive = False
        self.timer.stop()
        self.guard.cancel()
        QApplication.clipboard().dataChanged.disconnect(self.changed)
        QApplication.instance().applicationStateChanged.disconnect(self.focus_changed)
