from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.application import APP_NAME, configure_application
from app.config import PasswordConfig, PasswordMode
from app.generator import generate_password as generate_password_from_config
from app.wordlist import WordlistError, load_wordlist


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.resize(560, 560)

        self.custom_wordlist_path = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(20)

        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------

        title = QLabel("Password Generator")
        title.setObjectName("title")

        subtitle = QLabel("Generate secure passwords with ease")
        subtitle.setObjectName("subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # ---------------------------------------------------------
        # Mode
        # ---------------------------------------------------------

        mode_label = QLabel("MODE")
        mode_label.setObjectName("section_label")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(
            "Password Manager",
            PasswordMode.MANAGER,
        )
        self.mode_combo.addItem(
            "Human",
            PasswordMode.HUMAN,
        )

        main_layout.addWidget(mode_label)
        main_layout.addWidget(self.mode_combo)

        # ---------------------------------------------------------
        # Manager settings
        # ---------------------------------------------------------

        self.manager_settings = QWidget()
        manager_layout = QVBoxLayout(self.manager_settings)
        manager_layout.setContentsMargins(0, 0, 0, 0)
        manager_layout.setSpacing(14)

        length_header = QHBoxLayout()

        length_label = QLabel("Length")

        self.length_value = QLabel("20")
        self.length_value.setObjectName("value_label")

        length_header.addWidget(length_label)
        length_header.addStretch()
        length_header.addWidget(self.length_value)

        manager_layout.addLayout(length_header)

        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setMinimum(8)
        self.length_slider.setMaximum(64)
        self.length_slider.setValue(20)

        manager_layout.addWidget(self.length_slider)

        character_label = QLabel("Character set")
        character_label.setObjectName("subsection_label")

        manager_layout.addWidget(character_label)

        character_grid = QGridLayout()
        character_grid.setHorizontalSpacing(30)
        character_grid.setVerticalSpacing(10)

        self.uppercase_checkbox = QCheckBox("Uppercase")
        self.uppercase_checkbox.setChecked(True)

        self.lowercase_checkbox = QCheckBox("Lowercase")
        self.lowercase_checkbox.setChecked(True)

        self.numbers_checkbox = QCheckBox("Numbers")
        self.numbers_checkbox.setChecked(True)

        self.special_checkbox = QCheckBox("Special characters")
        self.special_checkbox.setChecked(True)

        character_grid.addWidget(
            self.uppercase_checkbox,
            0,
            0,
        )
        character_grid.addWidget(
            self.lowercase_checkbox,
            0,
            1,
        )
        character_grid.addWidget(
            self.numbers_checkbox,
            1,
            0,
        )
        character_grid.addWidget(
            self.special_checkbox,
            1,
            1,
        )

        manager_layout.addLayout(character_grid)

        main_layout.addWidget(self.manager_settings)

        # ---------------------------------------------------------
        # Human settings
        # ---------------------------------------------------------

        self.human_settings = QWidget()
        human_layout = QVBoxLayout(self.human_settings)
        human_layout.setContentsMargins(0, 0, 0, 0)
        human_layout.setSpacing(14)

        words_header = QHBoxLayout()

        words_label = QLabel("Words")

        self.words_value = QLabel("3")
        self.words_value.setObjectName("value_label")

        words_header.addWidget(words_label)
        words_header.addStretch()
        words_header.addWidget(self.words_value)

        human_layout.addLayout(words_header)

        self.words_slider = QSlider(Qt.Horizontal)
        self.words_slider.setMinimum(2)
        self.words_slider.setMaximum(8)
        self.words_slider.setValue(3)

        human_layout.addWidget(self.words_slider)

        separator_layout = QHBoxLayout()

        separator_label = QLabel("Separator")

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(
            [
                "-",
                "_",
                ".",
                " ",
                "/",
                "|",
                "Random",
            ]
        )

        separator_layout.addWidget(separator_label)
        separator_layout.addStretch()
        separator_layout.addWidget(self.separator_combo)

        human_layout.addLayout(separator_layout)

        wordlist_layout = QHBoxLayout()

        wordlist_label = QLabel("Word list")

        self.wordlist_combo = QComboBox()
        self.wordlist_combo.addItem("Built-in Polish")
        self.wordlist_combo.addItem("Custom...")

        wordlist_layout.addWidget(wordlist_label)
        wordlist_layout.addStretch()
        wordlist_layout.addWidget(self.wordlist_combo)

        human_layout.addLayout(wordlist_layout)

        main_layout.addWidget(self.human_settings)

        # ---------------------------------------------------------
        # Password output
        # ---------------------------------------------------------

        password_label = QLabel("GENERATED PASSWORD")
        password_label.setObjectName("section_label")

        self.password_field = QLineEdit()
        self.password_field.setReadOnly(True)
        self.password_field.setMinimumHeight(48)
        self.password_field.setPlaceholderText(
            "Your password will appear here"
        )

        main_layout.addWidget(password_label)
        main_layout.addWidget(self.password_field)

        # ---------------------------------------------------------
        # Buttons
        # ---------------------------------------------------------

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setObjectName("generate_button")
        self.generate_button.setMinimumHeight(46)

        self.copy_button = QPushButton("Copy")
        self.copy_button.setObjectName("copy_button")
        self.copy_button.setMinimumHeight(46)

        button_layout.addWidget(
            self.generate_button,
            2,
        )
        button_layout.addWidget(
            self.copy_button,
            1,
        )

        main_layout.addLayout(button_layout)

        # ---------------------------------------------------------
        # Connections
        # ---------------------------------------------------------

        self.mode_combo.currentIndexChanged.connect(
            self.update_mode
        )

        self.length_slider.valueChanged.connect(
            lambda value: self.length_value.setText(str(value))
        )

        self.words_slider.valueChanged.connect(
            lambda value: self.words_value.setText(str(value))
        )

        self.wordlist_combo.currentIndexChanged.connect(
            self.select_wordlist
        )

        self.generate_button.clicked.connect(
            self.generate_password
        )

        self.copy_button.clicked.connect(
            self.copy_password
        )

        # ---------------------------------------------------------
        # Initial state
        # ---------------------------------------------------------

        self.update_mode()

        # ---------------------------------------------------------
        # Styling
        # ---------------------------------------------------------

        self.setStyleSheet(
            """
            QWidget {
                background-color: #18181b;
                color: #f4f4f5;
                font-size: 14px;
            }

            QLabel#title {
                font-size: 27px;
                font-weight: 700;
                color: #fafafa;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #a1a1aa;
                margin-bottom: 4px;
            }

            QLabel#section_label {
                font-size: 11px;
                font-weight: 700;
                color: #a1a1aa;
                letter-spacing: 1px;
            }

            QLabel#subsection_label {
                font-size: 13px;
                font-weight: 600;
                color: #d4d4d8;
            }

            QLabel#value_label {
                min-width: 30px;
                font-size: 15px;
                font-weight: 600;
                color: #fafafa;
            }

            QComboBox {
                min-height: 38px;
                padding: 0 12px;
                border: 1px solid #3f3f46;
                border-radius: 7px;
                background-color: #27272a;
                color: #fafafa;
            }

            QComboBox:hover {
                border-color: #52525b;
            }

            QComboBox:focus {
                border-color: #71717a;
            }

            QComboBox QAbstractItemView {
                background-color: #27272a;
                color: #fafafa;
                border: 1px solid #3f3f46;
                selection-background-color: #3f3f46;
            }

            QSlider::groove:horizontal {
                height: 5px;
                background: #3f3f46;
                border-radius: 2px;
            }

            QSlider::handle:horizontal {
                width: 17px;
                height: 17px;
                margin: -6px 0;
                border-radius: 8px;
                background: #f4f4f5;
            }

            QSlider::handle:horizontal:hover {
                background: #ffffff;
            }

            QCheckBox {
                spacing: 8px;
                color: #d4d4d8;
            }

            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid #52525b;
                background-color: #27272a;
            }

            QCheckBox::indicator:hover {
                border-color: #71717a;
            }

            QCheckBox::indicator:checked {
                background-color: #f4f4f5;
                border-color: #f4f4f5;
            }

            QLineEdit {
                padding: 0 14px;
                border: 1px solid #3f3f46;
                border-radius: 8px;
                background-color: #09090b;
                color: #fafafa;
                font-size: 16px;
            }

            QLineEdit:focus {
                border-color: #71717a;
            }

            QPushButton {
                border: 1px solid #3f3f46;
                border-radius: 8px;
                background-color: #27272a;
                color: #f4f4f5;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #3f3f46;
            }

            QPushButton:pressed {
                background-color: #52525b;
            }

            QPushButton#generate_button {
                background-color: #f4f4f5;
                color: #18181b;
                border: none;
            }

            QPushButton#generate_button:hover {
                background-color: #e4e4e7;
            }

            QPushButton#generate_button:pressed {
                background-color: #d4d4d8;
            }

            QPushButton#copy_button {
                background-color: #27272a;
            }

            QMessageBox {
                background-color: #18181b;
            }
            """
        )

    def update_mode(self):
        mode = self.mode_combo.currentData()

        is_manager = mode == PasswordMode.MANAGER

        self.manager_settings.setVisible(is_manager)
        self.human_settings.setVisible(not is_manager)

    def select_wordlist(self, index):
        if index == 0:
            self.custom_wordlist_path = None
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose word list",
            "",
            "Text files (*.txt);;All files (*)",
        )

        if not path:
            self.wordlist_combo.setCurrentIndex(0)
            return

        try:
            load_wordlist(path)
        except WordlistError as error:
            QMessageBox.warning(
                self,
                "Invalid word list",
                str(error),
            )
            self.custom_wordlist_path = None
            self.wordlist_combo.setCurrentIndex(0)
            return

        self.custom_wordlist_path = path

    def copy_password(self):
        password = self.password_field.text()

        if password:
            QApplication.clipboard().setText(password)

    def generate_password(self):
        wordlist_path = None

        if self.mode_combo.currentData() == PasswordMode.HUMAN:
            wordlist_path = self.custom_wordlist_path

        config = PasswordConfig(
            mode=self.mode_combo.currentData(),
            length=self.length_slider.value(),
            uppercase=self.uppercase_checkbox.isChecked(),
            lowercase=self.lowercase_checkbox.isChecked(),
            numbers=self.numbers_checkbox.isChecked(),
            special=self.special_checkbox.isChecked(),
            words=self.words_slider.value(),
            separator=self.separator_combo.currentText(),
            wordlist_path=wordlist_path,
        )

        try:
            password = generate_password_from_config(config)
        except WordlistError as error:
            QMessageBox.warning(
                self,
                "Word list error",
                str(error),
            )
            return
        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid configuration",
                str(error),
            )
            return

        self.password_field.setText(password)


def run_app():
    app = QApplication([])
    configure_application(app)

    window = MainWindow()
    window.show()

    app.exec()
