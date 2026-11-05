"""Native desktop integration: validation, atomic presets and stale-job handling."""

import json
import time

import pytest
from PySide6.QtCore import QPoint, QSettings
from PySide6.QtWidgets import QApplication

from app.advanced_rules import AdvancedRules, CharacterType
from app.config import PasswordConfig
from app.presentation import Preferences
from app.presets import Preset, parameters
from app.ui import MainWindow


@pytest.fixture
def window(qtbot, tmp_path):
    prefs = Preferences(QSettings(str(tmp_path / "advanced.ini"), QSettings.IniFormat))
    prefs.set("language", "en")
    w = MainWindow(prefs)
    qtbot.addWidget(w)
    w.show()
    return w


def wait(qtbot, window):
    qtbot.waitUntil(lambda: not window.working, timeout=15000)


def restore(window, rules):
    window.rules_panel.restore(rules)
    window.rules_changed()


def test_collapsed_section_does_not_enable_rules(window):
    panel = window.rules_panel
    assert not panel.body.isVisible()
    assert not panel.rules().enabled
    panel.toggle.click()
    assert panel.body.isVisible()
    assert not panel.rules().enabled
    assert not panel.fields.isEnabled()
    panel.enabled.click()
    assert panel.fields.isEnabled()
    assert panel.controls["min_digits"].accessibleName() == "Minimum digits"


def test_exact_generation_transcription_copy_and_restart(window, qtbot):
    rules = AdvancedRules(
        enabled=True,
        custom_alphabet_enabled=True,
        custom_alphabet="a1",
        first_type=CharacterType.LOWER,
        max_identical_run=1,
    )
    window.length_spin.setValue(8)
    restore(window, rules)
    window.generate_password()
    wait(qtbot, window)
    assert window.password_field.text() == "a1a1a1a1"
    assert "only one" in window.rules_error.text()
    window.transcription_checkbox.setChecked(True)
    window.copy_password()
    assert QApplication.clipboard().text() == "a1a1a1a1"
    window.save_preset("Advanced example")
    wait(qtbot, window)
    raw = window.preferences.store.value("presets_v2")
    assert "a1a1a1a1" not in raw
    assert "a1a1a1a1" not in window.preferences.store.value("advanced_rules_v1")
    reopened = MainWindow(Preferences(window.preferences.store))
    qtbot.addWidget(reopened)
    assert reopened.rules_panel.rules().to_data() == rules.to_data()
    assert reopened.password_field.text() == ""
    restore(window, AdvancedRules())
    window.apply_preset(window.presets.custom[0])
    wait(qtbot, window)
    assert window.rules_panel.rules().to_data() == rules.to_data()
    assert window.length_spin.value() == 8
    assert window.password_field.text() == ""


def test_invalid_draft_is_visible_and_can_be_switched_off(window, qtbot):
    panel = window.rules_panel
    panel.enabled.setChecked(True)
    panel.controls["forbidden_characters"].setText("ą ")
    assert window.rules_error.isVisible()
    window.generate_password()
    wait(qtbot, window)
    assert window.password_field.text() == ""
    assert window.rules_error.isVisible()
    panel.enabled.setChecked(False)
    assert not window.preferences.advanced.enabled
    window.generate_password()
    assert len(window.password_field.text()) == 20
    stored = json.loads(window.preferences.store.value("advanced_rules_v1"))
    assert stored["enabled"] is False
    assert "ą" not in stored["forbidden_characters"]


def test_impossible_preset_does_not_change_controls(window, qtbot):
    config = PasswordConfig(
        length=8,
        advanced=AdvancedRules(
            enabled=True,
            custom_alphabet_enabled=True,
            custom_alphabet="a",
            max_identical_run=1,
        ),
    )
    preset = Preset("custom-test", "Impossible", parameters(config))
    before = window.current_config()
    window.password_field.setText("PUBLIC-MEMORY-ONLY")
    window.apply_preset(preset)
    wait(qtbot, window)
    assert window.current_config() == before
    assert window.password_field.text() == "PUBLIC-MEMORY-ONLY"
    assert window.rules_error.isVisible()


def test_edit_cancels_pending_generation_without_stale_result(
    window, qtbot, monkeypatch
):
    from app.advanced import CompletionCounter, GenerationCancelled

    original = CompletionCounter.total

    def slow(counter):
        # A deterministic gate makes cancellation test independent of CPU speed.
        for _ in range(100):
            if counter.cancelled():
                raise GenerationCancelled()
            time.sleep(0.002)
        return original(counter)

    monkeypatch.setattr(CompletionCounter, "total", slow)
    restore(window, AdvancedRules(enabled=True))
    window.generate_password()
    window.tabs.setCurrentIndex(1)
    wait(qtbot, window)
    assert window.password_field.text() == ""


def test_advanced_minima_and_endpoints_restore_all_controls(window, qtbot):
    rules = AdvancedRules(
        enabled=True,
        min_uppercase=2,
        min_lowercase=4,
        min_digits=3,
        min_symbols=2,
        forbidden_characters='"\\',
        first_type=CharacterType.LETTER,
        last_type=CharacterType.DIGIT,
        max_identical_run=2,
    )
    restore(window, rules)
    window.save_preset("Website")
    wait(qtbot, window)
    restore(window, AdvancedRules())
    window.apply_preset(window.presets.custom[0])
    wait(qtbot, window)
    assert window.rules_panel.rules().to_data() == rules.to_data()
    assert window.preferences.advanced.to_data() == rules.to_data()
    window.generate_password()
    wait(qtbot, window)
    result = window.password_field.text()
    assert len(result) == 20
    assert result[0].isalpha() and result[-1].isdigit()
    assert sum(c.isupper() for c in result) >= 2
    assert sum(c.islower() for c in result) >= 4
    assert sum(c.isdigit() for c in result) >= 3
    assert sum(not c.isalnum() for c in result) >= 2
    assert not set(result) & set(rules.forbidden_characters)


def test_generate_action_fits_default_window_without_scrolling(window, qtbot):
    qtbot.waitUntil(lambda: window.isVisible())
    viewport = window.centralWidget().viewport()
    bottom = window.generate_button.mapTo(
        viewport, QPoint(0, window.generate_button.height() - 1)
    )
    assert viewport.rect().contains(bottom)
