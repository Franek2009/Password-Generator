from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.config import PasswordConfig, PasswordMode
from app.generator import generate_password as generate_password_from_config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Password Generator")
        self.resize(520, 460)

        self.custom_wordlist_path = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(16)

        # Title
        title = QLabel("Password Generator")
        title.setObjectName("title")

        subtitle = QLabel("Generate secure passwords with ease")
        subtitle.setObjectName("subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Mode
        mode_layout = QHBoxLayout()

        mode_label = QLabel("Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Password Manager", PasswordMode.MANAGER)
        self.mode_combo.addItem("Human", PasswordMode.HUMAN)

        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()
        mode_layout.addWidget(self.mode_combo)

        main_layout.addLayout(mode_layout)

        # Manager settings
        self.manager_settings = QWidget()
        manager_layout = QVBoxLayout(self.manager_settings)
        manager_layout.setContentsMargins(0, 0, 0, 0)
        manager_layout.setSpacing(10)

        length_header = QHBoxLayout()

        length_label = QLabel("Length")
        self.length_value = QLabel("20")

        length_header.addWidget(length_label)
        length_header.addStretch()
        length_header.addWidget(self.length_value)

        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setMinimum(8)
        self.length_slider.setMaximum(64)
        self.length_slider.setValue(20)

        manager_layout.addLayout(length_header)
        manager_layout.addWidget(self.length_slider)

        self.uppercase_checkbox = QCheckBox("Uppercase")
        self.uppercase_checkbox.setChecked(True)

        self.lowercase_checkbox = QCheckBox("Lowercase")
        self.lowercase_checkbox.setChecked(True)

        self.numbers_checkbox = QCheckBox("Numbers")
        self.numbers_checkbox.setChecked(True)

        self.special_checkbox = QCheckBox("Special characters")
        self.special_checkbox.setChecked(True)

        manager_layout.addWidget(self.uppercase_checkbox)
        manager_layout.addWidget(self.lowercase_checkbox)
        manager_layout.addWidget(self.numbers_checkbox)
        manager_layout.addWidget(self.special_checkbox)

        main_layout.addWidget(self.manager_settings)

        # Human settings
        self.human_settings = QWidget()
        human_layout = QVBoxLayout(self.human_settings)
        human_layout.setContentsMargins(0, 0, 0, 0)
        human_layout.setSpacing(10)

        words_header = QHBoxLayout()

        words_label = QLabel("Words")
        self.words_value = QLabel("3")

        words_header.addWidget(words_label)
        words_header.addStretch()
        words_header.addWidget(self.words_value)

        self.words_slider = QSlider(Qt.Horizontal)
        self.words_slider.setMinimum(2)
        self.words_slider.setMaximum(8)
        self.words_slider.setValue(3)

        human_layout.addLayout(words_header)
        human_layout.addWidget(self.words_slider)

        separator_layout = QHBoxLayout()

        separator_label = QLabel("Separator")
        self.separator_combo = QComboBox()
        self.separator_combo.addItems(
            ["-", "_", ".", " ", "/", "|", "Random"]
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

        # Password
        password_label = QLabel("Generated password")

        self.password_field = QLineEdit()
        self.password_field.setReadOnly(True)
        self.password_field.setMinimumHeight(42)

        main_layout.addWidget(password_label)
        main_layout.addWidget(self.password_field)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setMinimumHeight(42)

        self.copy_button = QPushButton("Copy")
        self.copy_button.setMinimumHeight(42)

        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.copy_button)

        main_layout.addLayout(button_layout)

        # Connections
        self.mode_combo.currentIndexChanged.connect(self.update_mode)

        self.length_slider.valueChanged.connect(
            lambda value: self.length_value.setText(str(value))
        )

        self.words_slider.valueChanged.connect(
            lambda value: self.words_value.setText(str(value))
        )

        self.wordlist_combo.currentIndexChanged.connect(
            self.select_wordlist
        )

        self.generate_button.clicked.connect(self.generate_password)
        self.copy_button.clicked.connect(self.copy_password)

        # Initial state
        self.update_mode()

        self.setStyleSheet(
            """
            QWidget {
                font-size: 14px;
            }

            QLabel#title {
                font-size: 24px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #777777;
                margin-bottom: 8px;
            }

            QComboBox,
            QLineEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 6px;
            }

            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }

            QLineEdit {
                font-size: 16px;
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

        if path:
            self.custom_wordlist_path = path
        else:
            self.wordlist_combo.setCurrentIndex(0)

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

        password = generate_password_from_config(config)

        self.password_field.setText(password)


def run_app():
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
