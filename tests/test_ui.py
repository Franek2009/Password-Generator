import pytest

from PySide6.QtWidgets import QApplication

from app.config import PasswordMode
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


def test_manager_length_slider_updates_value_label(window):
    window.length_slider.setValue(32)

    assert window.length_value.text() == "32"


def test_manager_length_slider_has_expected_range(window):
    assert window.length_slider.minimum() == 8
    assert window.length_slider.maximum() == 64


def test_manager_length_slider_has_expected_default(window):
    assert window.length_slider.value() == 20


def test_human_words_slider_updates_value_label(window):
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
    window.generate_button.click()

    password = window.password_field.text()

    assert password
    assert len(password) == window.length_slider.value()


def test_generate_human_password(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(4)
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()
    words = password.split(window.separator_combo.currentText())

    assert len(words) == 4


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


def test_human_mode_can_use_random_separator(window):
    window.mode_combo.setCurrentIndex(1)
    window.words_slider.setValue(5)
    window.separator_combo.setCurrentText("Random")
    window.numbers_checkbox.setChecked(False)
    window.special_checkbox.setChecked(False)

    window.generate_button.click()

    password = window.password_field.text()

    assert password

    separators = [
        char
        for char in password
        if char in "-_. "
    ]

    assert separators
    assert len(set(separators)) == 1
