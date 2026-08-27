import pytest

from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import PasswordMode
from app.generator import RANDOM_SEPARATORS
from app.ui import MainWindow


@pytest.fixture
def window(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_manager_mode_is_selected_by_default(window):
    assert window.mode_combo.currentData() == PasswordMode.MANAGER


def test_manager_mode_is_visible_by_default(window):
    assert window.manager_settings.isVisible()
    assert not window.human_settings.isVisible()


def test_switching_to_human_mode(window):
    window.mode_combo.setCurrentIndex(1)

    assert window.mode_combo.currentData() == PasswordMode.HUMAN
    assert not window.manager_settings.isVisible()
    assert window.human_settings.isVisible()


def test_switching_back_to_manager_mode(window):
    window.mode_combo.setCurrentIndex(1)
    window.mode_combo.setCurrentIndex(0)

    assert window.mode_combo.currentData() == PasswordMode.MANAGER
    assert window.manager_settings.isVisible()
    assert not window.human_settings.isVisible()


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
        window.separator_combo.itemText(index)
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
    assert "Custom..." in options


def test_generate_button_exists(window):
    assert window.generate_button.text() == "Generate"


def test_copy_button_exists(window):
    assert window.copy_button.text() == "Copy"


def test_generate_manager_password(window):
    window.length_slider.setValue(24)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert len(password) == 24


def test_manager_mode_generates_password_with_lowercase_only(window):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(True)
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.length_slider.setValue(20)
    window.generate_button.click()

    password = window.password_field.text()

    assert len(password) == 20
    assert password.islower()
    assert password.isalpha()


def test_manager_mode_generates_password_with_numbers_only(window):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(False)
    window.numbers_checkbox.setChecked(True)
    window.special_checkbox.setChecked(False)

    window.length_slider.setValue(20)
    window.generate_button.click()

    password = window.password_field.text()

    assert len(password) == 20
    assert password.isdigit()


def test_manager_mode_rejects_no_character_sets(window, monkeypatch):
    window.uppercase_checkbox.setChecked(False)
    window.lowercase_checkbox.setChecked(False)
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    messages = []

    def fake_warning(*args):
        messages.append(args)

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)

    window.generate_button.click()

    assert window.password_field.text() == ""
    assert len(messages) == 1
    assert messages[0][1] == "Invalid configuration"
    assert messages[0][2] == "At least one character set must be enabled."


def test_human_mode_generates_password(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert len(password.split("-")) == 3


def test_human_mode_uses_selected_separator(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(4)
    window.separator_combo.setCurrentText("_")
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert "_" in password
    assert "-" not in password


def test_human_mode_can_use_random_separator(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(5)
    window.separator_combo.setCurrentText("Random")
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    separators = [
        char
        for char in password
        if char in RANDOM_SEPARATORS
    ]

    assert separators
    assert len(set(separators)) == 1


def test_human_mode_can_include_numbers(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.numbers_checkbox.setChecked(True)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert any(char.isdigit() for char in password)


def test_human_mode_can_include_special_characters(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(3)
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(True)

    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert any(
        char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        for char in password
    )


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
    assert window.generate_button.text() == "Generate"


def test_copy_button_has_correct_text(window):
    assert window.copy_button.text() == "Copy"
