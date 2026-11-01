"""Desktop presentation of the shared Password Generator interface."""

from pathlib import Path

from PySide6.QtCore import Qt, QTemporaryDir, QTimer
from PySide6.QtGui import QAction, QColor, QFontDatabase, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.application import APP_NAME, configure_application
from app.config import PasswordConfig, PasswordMode
from app.generator import generate_password as generate_password_from_config
from app.presentation import UI, Preferences
from app.presets import PresetStore, validate_parameters
from app.result_view import ResultView
from app.versioning import get_application_version
from app.wordlist import WordlistError, load_wordlist


def icon(name, color):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="{UI["icons"][name]}" stroke="{color}" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    pixmap = QPixmap()
    pixmap.loadFromData(svg.encode(), "SVG")
    return QIcon(pixmap)


class ModeTabs(QTabBar):
    def currentData(self):
        return [PasswordMode.MANAGER, PasswordMode.HUMAN][self.currentIndex()]


class SettingsDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setMinimumSize(580, 360)
        layout = QHBoxLayout(self)
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(150)
        self.navigation.addItems(["", ""])
        layout.addWidget(self.navigation)
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.labels = {}
        self.controls = {}
        for keys in [("auto_copy",), ("theme", "language")]:
            page = QWidget()
            rows = QVBoxLayout(page)
            rows.setContentsMargins(24, 20, 16, 20)
            heading = QLabel()
            heading.setObjectName("settings_heading")
            self.labels["general" if keys == ("auto_copy",) else "appearance"] = heading
            rows.addWidget(heading)
            rows.setSpacing(16)
            for key in keys:
                row = QHBoxLayout()
                label = QLabel()
                row.addWidget(label, 1)
                self.labels[key] = label
                if key == "auto_copy":
                    control = QCheckBox()
                    control.setChecked(owner.preferences.values[key])
                    control.toggled.connect(
                        lambda value, k=key: owner.set_preference(k, value)
                    )
                else:
                    control = QComboBox()
                    choices = (
                        ["system", "light", "dark"]
                        if key == "theme"
                        else ["system", "pl", "en"]
                    )
                    for value in choices:
                        control.addItem(value, value)
                    control.setCurrentIndex(
                        control.findData(owner.preferences.values[key])
                    )
                    control.currentIndexChanged.connect(
                        lambda index, k=key, c=control: owner.set_preference(
                            k, c.itemData(index)
                        )
                    )
                self.controls[key] = control
                label.setBuddy(control)
                row.addWidget(control)
                rows.addLayout(row)
            rows.addStretch()
            self.pages.addWidget(page)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        self.retranslate()

    def retranslate(self):
        t = self.owner.t
        self.setWindowTitle(t("settings"))
        for index, key in enumerate(["general", "appearance"]):
            self.navigation.item(index).setText(t(key))
        for key, label in self.labels.items():
            label.setText(t(key))
            if key in self.controls:
                self.controls[key].setAccessibleName(t(key))
        for key in ["theme", "language"]:
            combo = self.controls[key]
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(self.owner.preferences.values[key]))
            for index in range(combo.count()):
                value = combo.itemData(index)
                combo.setItemText(
                    index, {"pl": "Polski", "en": "English"}.get(value, t(value))
                )
            combo.blockSignals(False)


class MainWindow(QMainWindow):
    def __init__(self, preferences=None):
        super().__init__()
        self.preferences = preferences if preferences is not None else Preferences()
        self.t = self.preferences.text
        self.presets = PresetStore(self.preferences.store)
        self._applying_preset = False
        self._selected_preset = ""
        self._settings_dialog = None
        self._icon_directory = QTemporaryDir()
        self.custom_wordlist_path = self.preferences.values["wordlist"] or None
        self.setWindowTitle(APP_NAME)
        self.resize(760, 560)
        self.setMinimumWidth(560)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        central = QWidget()
        scroll.setWidget(central)
        self.setCentralWidget(scroll)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 22, 26, 24)
        layout.setSpacing(20)
        header = QHBoxLayout()
        self.tabs = ModeTabs()
        self.mode_combo = self.tabs
        self.tabs.addTab("")
        self.tabs.addTab("")
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setCurrentIndex(self.preferences.values["mode"])
        header.addWidget(self.tabs, 1)
        self.settings_button = QToolButton()
        self.settings_button.clicked.connect(self.open_settings)
        self.more_button = QToolButton()
        self.menu = QMenu(self)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self.show_about)
        self.quit_action = QAction(self)
        self.quit_action.triggered.connect(self.close)
        self.menu.addAction(self.about_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.more_button.setMenu(self.menu)
        self.more_button.setPopupMode(QToolButton.InstantPopup)
        header.addWidget(self.settings_button)
        header.addWidget(self.more_button)
        layout.addLayout(header)
        result = QFrame()
        result.setObjectName("result")
        result.setMinimumHeight(110)
        result_layout = QHBoxLayout(result)
        result_layout.setContentsMargins(16, 10, 12, 10)
        self.password_field = ResultView()
        self.password_field.setObjectName("password")
        self.password_field.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(20)
        self.password_field.setFont(font)
        self.copy_button = QToolButton()
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_password)
        self.password_field.textChanged.connect(
            lambda: self.copy_button.setEnabled(bool(self.password_field.text()))
        )
        result_layout.addWidget(self.password_field, 1)
        result_layout.addWidget(self.copy_button)
        layout.addWidget(result)
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.activated.connect(self.select_preset)
        preset_row.addWidget(self.preset_combo, 1)
        self.transcription_checkbox = self.option(preset_row, "transcription")
        self.transcription_checkbox.toggled.connect(self.update_result_view)
        layout.addLayout(preset_row)
        self.save_preset_action = QAction(self)
        self.menu.insertAction(self.about_action, self.save_preset_action)
        self.save_preset_action.triggered.connect(self.prompt_save_preset)
        self.delete_preset_action = QAction(self)
        self.menu.insertAction(self.about_action, self.delete_preset_action)
        self.delete_preset_action.triggered.connect(self.prompt_delete_preset)
        self.manager_settings = QWidget()
        manager = QVBoxLayout(self.manager_settings)
        manager.setContentsMargins(0, 0, 0, 0)
        manager.setSpacing(16)
        self.length_label, self.length_slider, self.length_spin = self.number_row(
            manager, "length", 8, 64
        )
        self.length_value = self.length_spin
        options = QHBoxLayout()
        self.uppercase_checkbox = self.option(options, "uppercase")
        self.lowercase_checkbox = self.option(options, "lowercase")
        self.manager_numbers_checkbox = self.option(options, "manager_numbers")
        self.manager_special_checkbox = self.option(options, "manager_special")
        manager.addLayout(options)
        self.exclude_similar_checkbox = self.option(manager, "exclude_similar")
        layout.addWidget(self.manager_settings)
        self.human_settings = QWidget()
        human = QVBoxLayout(self.human_settings)
        human.setContentsMargins(0, 0, 0, 0)
        human.setSpacing(16)
        self.words_label, self.words_slider, self.words_spin = self.number_row(
            human, "words", 2, 8
        )
        self.words_value = self.words_spin
        phrase_options = QHBoxLayout()
        self.separator_label = QLabel()
        self.separator_combo = QComboBox()
        for value in ["-", "_", ".", " ", "/", "|", "Random"]:
            self.separator_combo.addItem(value, value)
        self.separator_combo.setCurrentIndex(
            self.separator_combo.findData(self.preferences.values["separator"])
        )
        self.separator_combo.currentIndexChanged.connect(
            lambda index: self.preferences.set(
                "separator", self.separator_combo.itemData(index)
            )
        )
        self.separator_label.setBuddy(self.separator_combo)
        phrase_options.addWidget(self.separator_label)
        phrase_options.addWidget(self.separator_combo, 1)
        self.wordlist_label = QLabel()
        self.wordlist_combo = QComboBox()
        self.wordlist_combo.addItem("", "builtin")
        if self.custom_wordlist_path:
            self.wordlist_combo.addItem(
                Path(self.custom_wordlist_path).name, "selected"
            )
        self.wordlist_combo.addItem("", "custom")
        if self.custom_wordlist_path:
            self.wordlist_combo.setCurrentIndex(1)
        self.wordlist_combo.currentIndexChanged.connect(self.select_wordlist)
        self.wordlist_label.setBuddy(self.wordlist_combo)
        phrase_options.addWidget(self.wordlist_label)
        phrase_options.addWidget(self.wordlist_combo, 1)
        human.addLayout(phrase_options)
        options = QHBoxLayout()
        self.human_numbers_checkbox = self.option(options, "human_numbers")
        self.human_special_checkbox = self.option(options, "human_special")
        options.addStretch()
        human.addLayout(options)
        layout.addWidget(self.human_settings)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("divider")
        layout.addWidget(line)
        self.generate_button = QPushButton()
        self.generate_button.setObjectName("generate")
        self.generate_button.setMinimumHeight(48)
        self.generate_button.clicked.connect(self.generate_password)
        layout.addWidget(self.generate_button)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.hide()
        layout.addWidget(self.status)
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.status.hide)
        self.tabs.currentChanged.connect(self.update_mode)
        QApplication.styleHints().colorSchemeChanged.connect(self.apply_appearance)
        self.update_mode()
        self.retranslate()
        self.apply_appearance()
        if self.custom_wordlist_path:
            try:
                load_wordlist(self.custom_wordlist_path)
            except WordlistError:
                QTimer.singleShot(0, lambda: self.notify(self.t("wordlist_missing")))

        self.update_result_view()
        if self.presets.invalid:
            QTimer.singleShot(0, lambda: self.notify(self.t("preset_invalid")))
        # Any manual generator edit resets the selection; saving remains explicit.
        for control in [self.length_spin, self.words_spin]:
            control.valueChanged.connect(self.mark_custom)
        for control in [
            self.uppercase_checkbox,
            self.lowercase_checkbox,
            self.manager_numbers_checkbox,
            self.manager_special_checkbox,
            self.human_numbers_checkbox,
            self.human_special_checkbox,
            self.exclude_similar_checkbox,
        ]:
            control.toggled.connect(self.mark_custom)
        self.separator_combo.currentIndexChanged.connect(self.mark_custom)

    def mark_custom(self, *_):
        if not self._applying_preset:
            self._selected_preset = ""
            self.preset_combo.setCurrentIndex(0)
            self.delete_preset_action.setEnabled(False)

    def refresh_presets(self, identity=None):
        identity = self._selected_preset if identity is None else identity
        self.preset_combo.clear()
        self.preset_combo.addItem(self.t("preset_custom"), "")
        for p in self.presets.all:
            self.preset_combo.addItem(self.t(p.name) if p.builtin else p.name, p.id)
        self.preset_combo.setCurrentIndex(max(0, self.preset_combo.findData(identity)))
        self._selected_preset = self.preset_combo.currentData()
        self.delete_preset_action.setEnabled(
            identity in {p.id for p in self.presets.custom}
        )

    def current_config(self):
        human = self.tabs.currentIndex() == 1
        return PasswordConfig(
            mode=self.tabs.currentData(),
            length=self.length_spin.value(),
            uppercase=self.uppercase_checkbox.isChecked(),
            lowercase=self.lowercase_checkbox.isChecked(),
            numbers=(
                self.human_numbers_checkbox if human else self.manager_numbers_checkbox
            ).isChecked(),
            special=(
                self.human_special_checkbox if human else self.manager_special_checkbox
            ).isChecked(),
            words=self.words_spin.value(),
            separator=self.separator_combo.currentData(),
            wordlist_path=self.custom_wordlist_path if human else None,
            exclude_similar=self.exclude_similar_checkbox.isChecked(),
        )

    def select_preset(self, index):
        identity = self.preset_combo.itemData(index)
        preset = next((p for p in self.presets.all if p.id == identity), None)
        if preset:
            self.apply_preset(preset)

    def apply_preset(self, preset):
        try:
            data = validate_parameters(preset.config)
        except ValueError:
            self.notify(self.t("preset_invalid"))
            self.refresh_presets()
            return False
        if data["mode"] == "human" and data["wordlist"]:
            try:
                load_wordlist(data["wordlist"])
            except WordlistError as error:
                self.notify(self.t(error.code))
                self.refresh_presets()
                return False
        self._applying_preset = True
        try:
            if data["mode"] == "manager":
                self.tabs.setCurrentIndex(0)
                self.length_spin.setValue(data["length"])
                for key, widget in [
                    ("uppercase", self.uppercase_checkbox),
                    ("lowercase", self.lowercase_checkbox),
                    ("numbers", self.manager_numbers_checkbox),
                    ("special", self.manager_special_checkbox),
                    ("exclude_similar", self.exclude_similar_checkbox),
                ]:
                    widget.setChecked(data[key])
            else:
                self.tabs.setCurrentIndex(1)
                self.words_spin.setValue(data["words"])
                self.separator_combo.setCurrentIndex(
                    self.separator_combo.findData(data["separator"])
                )
                self.human_numbers_checkbox.setChecked(data["numbers"])
                self.human_special_checkbox.setChecked(data["special"])
                self.reset_wordlist()
                if data["wordlist"]:
                    self.custom_wordlist_path = data["wordlist"]
                    self.preferences.set("wordlist", self.custom_wordlist_path)
                    self.wordlist_combo.blockSignals(True)
                    self.wordlist_combo.insertItem(
                        1, Path(self.custom_wordlist_path).name, "selected"
                    )
                    self.wordlist_combo.setCurrentIndex(1)
                    self.wordlist_combo.blockSignals(False)
            self.password_field.clear()
            self.refresh_presets(preset.id)
            self.update_result_view()
        finally:
            self._applying_preset = False
        return True

    def save_preset(self, name):
        preset = self.presets.save(name, self.current_config())
        self.refresh_presets(preset.id)
        return preset

    def prompt_save_preset(self):
        name, ok = QInputDialog.getText(
            self, self.t("preset_save"), self.t("preset_name")
        )
        if ok:
            try:
                self.save_preset(name)
            except ValueError as error:
                self.notify(self.t(str(error)))

    def prompt_delete_preset(self):
        identity = self.preset_combo.currentData()
        if identity not in {p.id for p in self.presets.custom}:
            return
        if (
            QMessageBox.question(
                self, self.t("preset_delete"), self.t("preset_confirm_delete")
            )
            == QMessageBox.Yes
        ):
            self.presets.delete(identity)
            self.refresh_presets()

    def update_result_view(self, *_):
        self.password_field.transcription = self.transcription_checkbox.isChecked()
        self.password_field.human = self.tabs.currentIndex() == 1
        self.password_field.format_result()
        self.password_field.setAccessibleName(
            self.t("placeholder")
            + (
                " — " + self.t("transcription")
                if self.password_field.transcription
                else ""
            )
        )

    def option(self, layout, key):
        box = QCheckBox()
        box.setChecked(self.preferences.values[key])
        box.toggled.connect(lambda value: self.preferences.set(key, value))
        layout.addWidget(box)
        return box

    def number_row(self, layout, key, low, high):
        row = QHBoxLayout()
        label = QLabel()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(self.preferences.values[key])
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setValue(slider.value())
        spin.setMinimumWidth(78)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        spin.valueChanged.connect(lambda value: self.preferences.set(key, value))
        row.addWidget(label)
        row.addSpacing(16)
        row.addWidget(slider, 1)
        row.addSpacing(12)
        row.addWidget(spin)
        label.setBuddy(spin)
        layout.addLayout(row)
        return label, slider, spin

    def update_mode(self, *_):
        self.password_field.clear()
        self.mark_custom()
        self.update_result_view()
        manager = self.tabs.currentIndex() == 0
        self.manager_settings.setVisible(manager)
        self.human_settings.setVisible(not manager)
        self.preferences.set("mode", self.tabs.currentIndex())

    def set_preference(self, key, value):
        self.preferences.set(key, value)
        if key == "language":
            self.status.hide()
        if key in ["language", "theme"]:
            self.retranslate()
        self.apply_appearance()

    def retranslate(self):
        t = self.t
        self.tabs.setTabText(0, t("random"))
        self.tabs.setTabText(1, t("phrase"))
        self.password_field.setPlaceholderText(t("placeholder"))
        self.password_field.setAccessibleName(t("placeholder"))
        self.password_field.setAccessibleDescription(t("copy"))
        self.preset_combo.setAccessibleName(t("presets"))
        self.transcription_checkbox.setText(t("transcription"))
        self.exclude_similar_checkbox.setText(t("exclude_similar"))
        self.save_preset_action.setText(t("preset_save"))
        self.delete_preset_action.setText(t("preset_delete"))
        self.refresh_presets()
        self.generate_button.setText(t("generate"))
        for button, key in [
            (self.copy_button, "copy"),
            (self.settings_button, "settings"),
            (self.more_button, "more"),
        ]:
            button.setAccessibleName(t(key))
            button.setToolTip(t(key))
        for box, key in [
            (self.uppercase_checkbox, "uppercase"),
            (self.lowercase_checkbox, "lowercase"),
            (self.manager_numbers_checkbox, "numbers"),
            (self.manager_special_checkbox, "symbols"),
            (self.human_numbers_checkbox, "numbers"),
            (self.human_special_checkbox, "symbols"),
        ]:
            box.setText(t(key))
        for label, widget, key in [
            (self.length_label, self.length_slider, "length"),
            (self.words_label, self.words_slider, "words"),
            (self.separator_label, self.separator_combo, "separator"),
            (self.wordlist_label, self.wordlist_combo, "wordlist"),
        ]:
            label.setText(t(key))
            widget.setAccessibleName(t(key))
        self.length_spin.setAccessibleName(t("length"))
        self.words_spin.setAccessibleName(t("words"))
        self.separator_combo.blockSignals(True)
        for index in range(self.separator_combo.count()):
            value = self.separator_combo.itemData(index)
            self.separator_combo.setItemText(
                index,
                t("space")
                if value == " "
                else t("random_separator")
                if value == "Random"
                else value,
            )
        self.separator_combo.blockSignals(False)
        self.wordlist_combo.setItemText(0, t("builtin"))
        self.wordlist_combo.setItemText(self.wordlist_combo.count() - 1, t("custom"))
        self.about_action.setText(t("about"))
        self.quit_action.setText(t("quit"))
        if self._settings_dialog:
            self._settings_dialog.retranslate()

    def apply_appearance(self, *_):
        theme = self.preferences.values["theme"]
        dark = theme == "dark" or (
            theme == "system"
            and QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )
        c = UI["palettes"]["dark" if dark else "light"]
        self.colors = c
        palette = QPalette()
        for role, key in [
            (QPalette.Window, "background"),
            (QPalette.WindowText, "text"),
            (QPalette.Base, "surface"),
            (QPalette.Text, "text"),
            (QPalette.Button, "surface"),
            (QPalette.ButtonText, "text"),
            (QPalette.Highlight, "accent"),
            (QPalette.HighlightedText, "background"),
            (QPalette.PlaceholderText, "muted"),
        ]:
            palette.setColor(role, QColor(c[key]))
        self.setPalette(palette)
        icon_paths = {}
        for name, path, stroke in [
            ("check", "M5 12 L10 17 L20 7", "#101819"),
            ("up", "M6 15 L12 9 L18 15", c["text"]),
            ("down", UI["icons"]["chevron"], c["text"]),
        ]:
            target = Path(self._icon_directory.path()) / f"{name}.svg"
            target.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{path}" fill="none" stroke="{stroke}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )
            icon_paths[name] = target.as_posix()
        self.setStyleSheet(f"""
            QWidget {{ color: {c["text"]}; font-size: 14px; }}
            QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c["background"]}; }}
            QToolButton, QComboBox, QSpinBox {{ background: {c["surface"]}; border: 1px solid {c["border"]}; border-radius: 6px; padding: 8px; }}
            QComboBox {{ padding-right: 36px; }}
            QComboBox::drop-down {{ subcontrol-origin: border; subcontrol-position: top right; width: 30px; border: none; background: transparent; }}
            QComboBox::down-arrow {{ image: url({icon_paths["down"]}); width: 16px; height: 16px; }}
            QComboBox:hover {{ border-color: {c["accent"]}; }}
            QToolButton {{ min-width: 24px; min-height: 24px; }}
            QToolButton:disabled {{ color: {c["muted"]}; }}
            QFrame#result {{ background: {c["surface"]}; border: 1px solid {c["border"]}; border-radius: 8px; }}
            QTextEdit#password {{ background: transparent; border: none; padding: 6px 0; }}
            QTabBar::tab {{ padding: 12px 22px; border-bottom: 1px solid {c["border"]}; }}
            QTabBar::tab:selected {{ border-bottom: 3px solid {c["accent"]}; font-weight: 600; }}
            QSlider::groove:horizontal {{ height: 6px; background: {c["border"]}; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: {c["accent"]}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ width: 18px; margin: -6px 0; background: {c["text"]}; border: 2px solid {c["background"]}; border-radius: 9px; }}
            QCheckBox {{ spacing: 10px; min-height: 32px; }}
            QCheckBox::indicator {{ width: 22px; height: 22px; border: 1px solid {c["border"]}; border-radius: 4px; background: {c["surface"]}; }}
            QCheckBox::indicator:checked {{ background: {c["accent"]}; border-color: {c["accent"]}; image: url({icon_paths["check"]}); }}
            QCheckBox:focus {{ outline: 1px solid {c["accent"]}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; border-left: 1px solid {c["border"]}; }}
            QSpinBox::up-arrow {{ image: url({icon_paths["up"]}); width: 14px; height: 14px; }}
            QSpinBox::down-arrow {{ image: url({icon_paths["down"]}); width: 14px; height: 14px; }}
            QToolButton::menu-indicator {{ image: none; }}
            QFrame#divider {{ border: none; background: {c["border"]}; max-height: 1px; }}
            QLabel#settings_heading {{ font-size: 20px; font-weight: 600; }}
            QPushButton#generate {{ color: {c["button_text"]}; background: {c["button"]}; border: 1px solid {c["accent"]}; border-radius: 7px; font-size: 17px; font-weight: 600; }}
            QPushButton#generate:hover {{ background: {c["accent"]}; }}
            QMenu, QListWidget, QComboBox QAbstractItemView {{ background: {c["surface"]}; color: {c["text"]}; selection-background-color: {c["button"]}; }}
            QMenu::item {{ padding: 10px 24px; }}
            QToolButton:focus, QComboBox:focus, QSpinBox:focus, QPushButton:focus {{ border: 2px solid {c["accent"]}; }}
        """)
        for button, name in [
            (self.copy_button, "copy"),
            (self.settings_button, "settings"),
            (self.more_button, "more"),
        ]:
            button.setIcon(icon(name, c["text"]))
        if self._settings_dialog:
            self._settings_dialog.setPalette(palette)

    def notify(self, message):
        self.status.setText(message)
        self.status.show()
        self.status_timer.start(3500)

    def open_settings(self):
        if not self._settings_dialog:
            self._settings_dialog = SettingsDialog(self)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def show_about(self):
        QMessageBox.information(
            self,
            self.t("about"),
            f"{APP_NAME} {get_application_version()}\n\n{self.t('about_text')}",
        )

    def reset_wordlist(self):
        self.mark_custom()
        self.custom_wordlist_path = None
        self.preferences.set("wordlist", "")
        self.wordlist_combo.blockSignals(True)
        while self.wordlist_combo.count() > 2:
            self.wordlist_combo.removeItem(1)
        self.wordlist_combo.setCurrentIndex(0)
        self.wordlist_combo.blockSignals(False)

    def select_wordlist(self, index):
        self.mark_custom()
        choice = self.wordlist_combo.itemData(index)
        if choice == "builtin":
            self.reset_wordlist()
            return
        if choice != "custom":
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self.t("custom"), "", self.t("text_files")
        )
        if path:
            try:
                load_wordlist(path)
            except WordlistError as error:
                self.notify(self.t(error.code))
            else:
                self.reset_wordlist()
                self.custom_wordlist_path = path
                self.preferences.set("wordlist", path)
                self.wordlist_combo.blockSignals(True)
                self.wordlist_combo.insertItem(1, Path(path).name, "selected")
                self.wordlist_combo.blockSignals(False)
        self.wordlist_combo.blockSignals(True)
        self.wordlist_combo.setCurrentIndex(1 if self.custom_wordlist_path else 0)
        self.wordlist_combo.blockSignals(False)

    def copy_password(self):
        if self.password_field.text():
            QApplication.clipboard().setText(self.password_field.text())
            self.notify(self.t("copied"))

    def generate_password(self):
        config = self.current_config()
        try:
            password = generate_password_from_config(config)
        except (WordlistError, ValueError) as error:
            self.notify(self.t(getattr(error, "code", "unknown_error")))
            return
        self.status.hide()
        self.password_field.setText(password)
        self.password_field.setCursorPosition(0)
        if self.preferences.values["auto_copy"]:
            self.copy_password()


def run_app():
    app = QApplication([])
    app.setStyle("Fusion")
    configure_application(app)
    window = MainWindow()
    window.show()
    app.exec()
