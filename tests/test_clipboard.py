"""State-machine contract shared with Kotlin; all strings are public examples."""

import hashlib
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from app.clipboard import (
    TOKEN_MIME,
    ClipboardGuard,
    QtClipboardPort,
)
from app.presentation import Preferences
from app.ui import MainWindow


class FakePort:
    def __init__(self):
        self.text = None
        self.token = None
        self.available = True
        self.fail_clear = False
        self.fail_write = False
        self.clears = 0
        self.on_clear = None
        self.on_match = None

    def write(self, text, token):
        if self.fail_write:
            return False
        self.text, self.token = text, token
        return True

    def matches(self, pending, *, content):
        if not self.available:
            return None
        result = self.token == pending.token
        if content and result:
            result = hashlib.sha256(self.text.encode()).digest() == pending.digest
        if self.on_match:
            callback, self.on_match = self.on_match, None
            callback()
        return result

    def clear(self):
        if self.fail_clear:
            return False
        self.text = self.token = None
        self.clears += 1
        if self.on_clear:
            self.on_clear()
        return True


CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/clipboard_contract.json").read_text()
)


@pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
def test_shared_contract(case):
    port = FakePort()
    now = [0]
    guard = ClipboardGuard(port, lambda: now[0])
    for step in case["steps"]:
        action, value = step["action"], step["value"]
        if action == "policy":
            guard.set_policy(value)
        elif action == "copy":
            guard.copy(value)
        elif action == "advance":
            now[0] += value
        elif action == "tick":
            guard.tick()
        elif action == "changed":
            guard.changed()
        elif action == "foreign":
            port.text, port.token = value, None
        elif action == "mutate":
            port.text = value
        elif action == "unavailable":
            port.available = not value
        elif action == "fail_clear":
            port.fail_clear = value
        else:
            raise AssertionError(action)
    assert port.text == case["text"]
    assert (guard.pending is not None) == case["pending"]
    assert port.clears == case["clears"]


def test_reentrant_clear_and_stale_read_do_not_destroy_new_copy():
    port = FakePort()
    now = [0]
    guard = ClipboardGuard(port, lambda: now[0])
    guard.set_policy(30)
    guard.copy("Alpha")
    now[0] = 30000
    port.on_clear = lambda: (guard.changed(), guard.tick())
    guard.tick()
    assert port.clears == 1 and guard.pending is None
    guard.copy("Alpha")
    now[0] += 30000
    port.on_match = lambda: guard.copy("Beta")
    guard.tick()
    assert port.text == "Beta" and guard.pending is not None
    assert port.clears == 1
    now[0] += 30000
    port.on_clear = lambda: guard.copy("Gamma")
    guard.tick()
    assert port.text == "Gamma" and guard.pending is not None


def test_write_failure_and_disposal_keep_no_pending_secret():
    port = FakePort()
    guard = ClipboardGuard(port, lambda: 0)
    guard.set_policy(30)
    guard.copy("Alpha")
    assert "Alpha" not in repr(guard.pending)
    port.fail_write = True
    assert not guard.copy("Beta") and guard.pending is None
    port.fail_write = False
    guard.copy("Gamma")
    guard.cancel()
    assert guard.pending is None


def test_qt_adapter_checks_owner_token_and_exact_content(qapp, monkeypatch):
    clipboard = QApplication.clipboard()
    port = QtClipboardPort(clipboard)
    guard = ClipboardGuard(port, lambda: 0)
    guard.set_policy(30)
    guard.copy("Żółw\u00a0Las")
    assert clipboard.text() == "Żółw\u00a0Las"
    monkeypatch.setattr(clipboard, "ownsClipboard", lambda: True)
    assert port.matches(guard.pending, content=True)
    other = QMimeData()
    other.setText("Other")
    other.setData(TOKEN_MIME, guard.pending.token.encode())
    clipboard.setMimeData(other)
    assert port.matches(guard.pending, content=False)
    assert not port.matches(guard.pending, content=True)
    monkeypatch.setattr(clipboard, "ownsClipboard", lambda: False)
    assert not port.matches(guard.pending, content=False)
    clipboard.clear()


def test_ui_copy_routes_schedule_and_cancel_without_changing_result(
    qtbot, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    prefs = Preferences(QSettings(str(tmp_path / "clip.ini"), QSettings.IniFormat))
    prefs.set("language", "en")
    window = MainWindow(prefs)
    qtbot.addWidget(window)
    window.show()
    now = [0]
    window.clipboard_controller.guard.clock = lambda: now[0]
    clipboard = QApplication.clipboard()
    monkeypatch.setattr(clipboard, "ownsClipboard", lambda: True)
    window.set_preference("clipboard_clear_seconds", 30)
    raw = "Żółw\u00a0Las-MemoryOnly"
    window.password_field.setText(raw)
    for action in [
        window.copy_button.click,
        window.password_field.copy,
        lambda: qtbot.keySequence(window.password_field, QKeySequence.Copy),
    ]:
        action()
        assert clipboard.text() == raw
        assert window.clipboard_controller.guard.pending is not None
        now[0] += 30000
        window.clipboard_controller.check()
        assert clipboard.text() == ""
        assert window.password_field.text() == raw
    window.copy_password()
    window.set_preference("clipboard_clear_seconds", 0)
    now[0] += 30000
    window.clipboard_controller.check()
    assert clipboard.text() == raw
    assert window.clipboard_controller.guard.pending is None
    window.set_preference("clipboard_clear_seconds", 60)
    window.open_settings()
    control = window._settings_dialog.controls["clipboard_clear_seconds"]
    assert control.currentData() == 60
    assert control.accessibleName() == "Clear copied password"
    restarted = Preferences(prefs.store)
    assert restarted.values["clipboard_clear_seconds"] == 60
    assert raw not in str(prefs.store.allKeys())
    assert raw not in str([prefs.store.value(key) for key in prefs.store.allKeys()])
    window._settings_dialog.close()
    window.copy_password()
    assert window.clipboard_controller.guard.pending is not None
    window.close()
    assert not window.clipboard_controller.alive
    assert window.clipboard_controller.guard.pending is None
    assert not window.clipboard_controller.timer.isActive()
    assert clipboard.text() == raw


@pytest.mark.parametrize("value", [-1, 15, "invalid", 999])
def test_invalid_saved_setting_defaults_off(tmp_path, value):
    from PySide6.QtCore import QSettings

    settings = QSettings(str(tmp_path / "invalid.ini"), QSettings.IniFormat)
    settings.setValue("clipboard_clear_seconds", value)
    assert Preferences(settings).values["clipboard_clear_seconds"] == 0


def test_auto_copy_and_mode_changes_keep_original_clipboard_deadline(
    qtbot, tmp_path, monkeypatch
):
    from PySide6.QtCore import QSettings

    prefs = Preferences(QSettings(str(tmp_path / "auto.ini"), QSettings.IniFormat))
    window = MainWindow(prefs)
    qtbot.addWidget(window)
    monkeypatch.setattr(QApplication.clipboard(), "ownsClipboard", lambda: True)
    now = [1000]
    window.clipboard_controller.guard.clock = lambda: now[0]
    window.set_preference("clipboard_clear_seconds", 30)
    window.set_preference("auto_copy", True)
    window.generate_password()
    result = window.password_field.text()
    assert QApplication.clipboard().text() == result
    entry = window.clipboard_controller.guard.pending
    assert entry.deadline == 31000
    window.set_preference("auto_copy", False)
    window.generate_password()
    assert window.clipboard_controller.guard.pending is entry
    window.tabs.setCurrentIndex(1)
    assert window.password_field.text() == ""
    assert window.clipboard_controller.guard.pending is entry
    assert QApplication.clipboard().text() == result
    now[0] = 31000
    window.clipboard_controller.check()
    assert QApplication.clipboard().text() == ""


def test_wayland_without_focus_does_not_inspect_clipboard(monkeypatch):
    from types import SimpleNamespace

    from PySide6.QtCore import Qt

    import app.clipboard as module

    class ForbiddenClipboard:
        def ownsClipboard(self):
            raise AssertionError("No clipboard access without focus")

    application = SimpleNamespace(
        platformName=lambda: "wayland", applicationState=lambda: Qt.ApplicationInactive
    )
    monkeypatch.setattr(
        module, "QApplication", SimpleNamespace(instance=lambda: application)
    )
    port = QtClipboardPort(ForbiddenClipboard())
    entry = module.PendingCopy("example", b"digest", 0)
    assert port.matches(entry, content=True) is None


def test_suspend_aware_linux_clock(monkeypatch):
    from types import SimpleNamespace

    import app.clipboard as module

    observed = []
    monkeypatch.setattr(module.time, "CLOCK_BOOTTIME", 12345, raising=False)
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(
        module.time, "clock_gettime", lambda clock: observed.append(clock) or 123.5
    )
    assert module.elapsed_ms() == 123500
    assert observed == [module.time.CLOCK_BOOTTIME]


def test_windows_clock_uses_full_64_bit_uptime(monkeypatch):
    import ctypes
    from types import SimpleNamespace

    import app.clipboard as module

    def clock():
        return (1 << 40) + 123

    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(kernel32=SimpleNamespace(GetTickCount64=clock)),
        raising=False,
    )
    assert module.elapsed_ms() == (1 << 40) + 123
    assert clock.restype == ctypes.c_ulonglong


def test_qt_timer_checks_deadline_without_manual_focus_event(qtbot):
    from app.clipboard import ClipboardController

    port = FakePort()
    now = [0]
    controller = ClipboardController(30, port=port, clock=lambda: now[0])
    try:
        assert controller.copy("Public-foreground-example")
        assert controller.timer.isActive()
        assert controller.timer.interval() <= 1000
        now[0] = 30000
        qtbot.waitUntil(lambda: port.text is None, timeout=3000)
        assert controller.guard.pending is None
        assert port.clears == 1
    finally:
        controller.dispose()
