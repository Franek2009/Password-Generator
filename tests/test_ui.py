import pytest

from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import PasswordMode
from app.generator import RANDOM_SEPARATORS
from app.ui import MainWindow
from app.presentation import Preferences
from PySide6.QtCore import QSettings


@pytest.fixture
def window(qtbot, tmp_path):
    preferences = Preferences(
        QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    )
    preferences.set("language", "en")
    window = MainWindow(preferences)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_manager_mode_is_selected_by_default(window):
    assert window.mode_combo.currentData() == PasswordMode.MANAGER


def test_manager_mode_is_visible_by_default(window):
    assert window.manager_settings.isVisible()
    assert not window.human_settings.isVisible()
    assert window.manager_numbers_checkbox.isVisible()
    assert window.manager_special_checkbox.isVisible()
    assert not window.human_numbers_checkbox.isVisible()
    assert not window.human_special_checkbox.isVisible()


def test_switching_to_human_mode(window):
    window.mode_combo.setCurrentIndex(1)

    assert window.mode_combo.currentData() == PasswordMode.HUMAN
    assert not window.manager_settings.isVisible()
    assert window.human_settings.isVisible()
    assert not window.manager_numbers_checkbox.isVisible()
    assert not window.manager_special_checkbox.isVisible()
    assert window.human_numbers_checkbox.isVisible()
    assert window.human_special_checkbox.isVisible()


def test_switching_back_to_manager_mode(window):
    window.mode_combo.setCurrentIndex(1)
    window.mode_combo.setCurrentIndex(0)

    assert window.mode_combo.currentData() == PasswordMode.MANAGER
    assert window.manager_settings.isVisible()
    assert not window.human_settings.isVisible()


def test_manager_and_human_options_are_independent(window, monkeypatch):
    generated_configs = []

    def fake_generate(config):
        generated_configs.append(config)
        return "generated-password"

    monkeypatch.setattr("app.ui.generate_password_from_config", fake_generate)

    window.manager_numbers_checkbox.setChecked(False)
    window.manager_special_checkbox.setChecked(False)

    window.mode_combo.setCurrentIndex(1)
    window.human_numbers_checkbox.setChecked(True)
    window.human_special_checkbox.setChecked(False)
    window.generate_button.click()

    human_config = generated_configs[-1]
    assert human_config.mode == PasswordMode.HUMAN
    assert human_config.numbers is True
    assert human_config.special is False

    window.mode_combo.setCurrentIndex(0)

    assert not window.manager_numbers_checkbox.isChecked()
    assert not window.manager_special_checkbox.isChecked()

    window.generate_button.click()

    manager_config = generated_configs[-1]
    assert manager_config.mode == PasswordMode.MANAGER
    assert manager_config.numbers is False
    assert manager_config.special is False
    assert window.human_numbers_checkbox.isChecked()
    assert not window.human_special_checkbox.isChecked()


def test_manager_length_slider_updates_label(window):
    window.length_slider.setValue(32)

    assert window.length_value.text() == "32"


def test_manager_length_slider_has_expected_range(window):
    assert window.length_slider.minimum() == 8
    assert window.length_slider.maximum() == 64


def test_manager_length_slider_has_expected_default(window):
    assert window.length_slider.value() == 20


def test_human_words_slider_updates_label(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(6)

    assert window.words_value.text() == "6"


def test_human_words_slider_has_expected_range(window):
    assert window.words_slider.minimum() == 2
    assert window.words_slider.maximum() == 8


def test_human_words_slider_has_expected_default(window):
    assert window.words_slider.value() == 3


def test_separator_combo_contains_supported_separators(window):
    separators = [
        window.separator_combo.itemData(index)
        for index in range(window.separator_combo.count())
    ]

    assert "-" in separators
    assert "_" in separators
    assert "." in separators
    assert " " in separators
    assert "/" in separators
    assert "|" in separators
    assert "Random" in separators


def test_separator_default_is_dash(window):
    assert window.separator_combo.currentText() == "-"


def test_wordlist_combo_has_builtin_and_custom_options(window):
    options = [
        window.wordlist_combo.itemText(index)
        for index in range(window.wordlist_combo.count())
    ]

    assert "Built-in Polish" in options
    assert "Choose file…" in options


def test_generate_button_exists(window):
    assert window.generate_button.text() == "Generate password"


def test_copy_button_exists(window):
    assert window.copy_button.accessibleName() == "Copy password"


def test_generate_manager_password(window):
    window.length_slider.setValue(24)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert len(password) == 24


def test_manager_mode_generates_password_with_lowercase_only(window):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(True)
    window.manager_numbers_checkbox.setChecked(False)
    window.manager_special_checkbox.setChecked(False)

    window.length_slider.setValue(20)
    window.generate_button.click()

    password = window.password_field.text()

    assert len(password) == 20
    assert password.islower()
    assert password.isalpha()


def test_manager_mode_generates_password_with_numbers_only(window):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(False)
    window.manager_numbers_checkbox.setChecked(True)
    window.manager_special_checkbox.setChecked(False)

    window.length_slider.setValue(20)
    window.generate_button.click()

    password = window.password_field.text()

    assert len(password) == 20
    assert password.isdigit()


def test_manager_mode_rejects_no_character_sets(window, monkeypatch):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(False)
    window.manager_numbers_checkbox.setChecked(False)
    window.manager_special_checkbox.setChecked(False)

    window.generate_button.click()
    assert window.password_field.text() == ""
    assert window.status.isVisible()
    assert window.status.text() == "Select at least one character set."


def test_human_mode_generates_password(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.human_numbers_checkbox.setChecked(False)
    window.human_special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert len(password.split("-")) == 3


def test_human_mode_uses_selected_separator(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(4)
    window.separator_combo.setCurrentText("_")
    window.human_numbers_checkbox.setChecked(False)
    window.human_special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert "_" in password
    assert "-" not in password


def test_human_mode_can_use_random_separator(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(5)
    window.separator_combo.setCurrentText("Random")
    window.human_numbers_checkbox.setChecked(False)
    window.human_special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    separators = [char for char in password if char in RANDOM_SEPARATORS]

    assert separators
    assert len(set(separators)) == 1


def test_human_mode_can_include_numbers(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.human_numbers_checkbox.setChecked(True)
    window.human_special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert any(char.isdigit() for char in password)


def test_human_mode_can_include_special_characters(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.human_numbers_checkbox.setChecked(False)
    window.human_special_checkbox.setChecked(True)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert any(char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" for char in password)


def test_copy_button_copies_password_to_clipboard(window):
    password = "TestPassword123!"

    window.password_field.setText(password)
    window.copy_button.click()

    assert QApplication.clipboard().text() == password


def test_copy_button_does_nothing_when_password_is_empty(window):
    QApplication.clipboard().clear()

    window.password_field.clear()
    window.copy_button.click()

    assert QApplication.clipboard().text() == ""


def test_generate_button_updates_password_field(window):
    window.generate_button.click()

    assert window.password_field.text()


def test_switching_mode_does_not_clear_settings(window):
    window.length_slider.setValue(32)

    window.mode_combo.setCurrentIndex(1)
    window.mode_combo.setCurrentIndex(0)

    assert window.length_slider.value() == 32


def test_separator_selection_is_preserved(window):
    window.mode_combo.setCurrentIndex(1)
    window.separator_combo.setCurrentText("|")

    assert window.separator_combo.currentText() == "|"


def test_wordlist_defaults_to_built_in(window):
    window.mode_combo.setCurrentIndex(1)

    assert window.wordlist_combo.currentIndex() == 0
    assert window.custom_wordlist_path is None


def test_password_field_is_read_only(window):
    assert window.password_field.isReadOnly()


def test_generate_button_has_correct_text(window):
    assert window.generate_button.text() == "Generate password"


def test_copy_button_has_correct_text(window):
    assert window.copy_button.accessibleName() == "Copy password"


def test_number_field_and_slider_stay_synchronized(window):
    window.length_spin.setValue(48)
    assert window.length_slider.value() == 48
    window.words_slider.setValue(7)
    assert window.words_spin.value() == 7


def test_copy_disabled_until_password_exists(window):
    assert not window.copy_button.isEnabled()
    window.generate_button.click()
    assert window.copy_button.isEnabled()
    window.password_field.clear()
    assert not window.copy_button.isEnabled()


def test_automatic_copy_is_optional(window):
    QApplication.clipboard().clear()
    window.generate_button.click()
    assert QApplication.clipboard().text() == ""
    window.set_preference("auto_copy", True)
    window.generate_button.click()
    assert QApplication.clipboard().text() == window.password_field.text()


def test_language_and_theme_changes_preserve_result_and_configuration(window):
    window.length_spin.setValue(35)
    window.generate_button.click()
    password = window.password_field.text()
    window.open_settings()
    window.set_preference("language", "pl")
    window.set_preference("theme", "dark")
    assert window.tabs.tabText(0) == "Losowe hasło"
    assert window.generate_button.text() == "Generuj hasło"
    assert window._settings_dialog.windowTitle() == "Ustawienia"
    assert window.password_field.text() == password
    assert window.length_spin.value() == 35
    assert window.colors["background"] == "#101819"
    window.set_preference("theme", "light")
    assert window.colors["background"] == "#F5F6F3"


def test_preferences_restart_without_password_history(window, qtbot):
    window.length_spin.setValue(42)
    window.set_preference("auto_copy", True)
    window.set_preference("language", "pl")
    window.generate_button.click()
    replacement = MainWindow(Preferences(window.preferences.store))
    qtbot.addWidget(replacement)
    assert replacement.length_spin.value() == 42
    assert replacement.preferences.values["auto_copy"]
    assert replacement.generate_button.text() == "Generuj hasło"
    assert replacement.password_field.text() == ""
    assert "password" not in window.preferences.store.allKeys()


def test_cancelled_or_invalid_wordlist_keeps_previous_selection(
    window, tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QFileDialog

    words = tmp_path / "words.txt"
    words.write_text("kot\npies\n", encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(words), ""))
    window.wordlist_combo.setCurrentIndex(window.wordlist_combo.count() - 1)
    assert window.custom_wordlist_path == str(words)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    window.wordlist_combo.setCurrentIndex(window.wordlist_combo.count() - 1)
    assert window.custom_wordlist_path == str(words)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args: (str(tmp_path / "missing.txt"), ""),
    )
    window.wordlist_combo.setCurrentIndex(window.wordlist_combo.count() - 1)
    assert window.custom_wordlist_path == str(words)
