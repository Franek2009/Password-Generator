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
        self.resize(500, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Mode
        mode_label = QLabel("Mode")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Password Manager", PasswordMode.MANAGER)
        self.mode_combo.addItem("Human", PasswordMode.HUMAN)

        layout.addWidget(mode_label)
        layout.addWidget(self.mode_combo)

        # Length
        length_label = QLabel("Length")
        layout.addWidget(length_label)

        self.length_value = QLabel("20")
        layout.addWidget(self.length_value)

        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setMinimum(8)
        self.length_slider.setMaximum(64)
        self.length_slider.setValue(20)

        layout.addWidget(self.length_slider)

        self.length_slider.valueChanged.connect(
            lambda value: self.length_value.setText(str(value))
        )

        # Character sets
        self.uppercase_checkbox = QCheckBox("Uppercase")
        self.uppercase_checkbox.setChecked(True)

        self.lowercase_checkbox = QCheckBox("Lowercase")
        self.lowercase_checkbox.setChecked(True)

        self.numbers_checkbox = QCheckBox("Numbers")
        self.numbers_checkbox.setChecked(True)

        self.special_checkbox = QCheckBox("Special characters")
        self.special_checkbox.setChecked(True)

        layout.addWidget(self.uppercase_checkbox)
        layout.addWidget(self.lowercase_checkbox)
        layout.addWidget(self.numbers_checkbox)
        layout.addWidget(self.special_checkbox)

        # Human mode settings
        self.words_label = QLabel("Words")

        self.words_slider = QSlider(Qt.Horizontal)
        self.words_slider.setMinimum(2)
        self.words_slider.setMaximum(8)
        self.words_slider.setValue(3)

        self.words_value = QLabel("3")

        self.separator_label = QLabel("Separator")

        self.separator_combo = QComboBox()
        self.separator_combo.addItems(["-", "_", ".", " ", "/", "|", "Random"])

        self.wordlist_label = QLabel("Word list")

        self.wordlist_combo = QComboBox()
        self.wordlist_combo.addItem("Built-in Polish")
        self.wordlist_combo.addItem("Custom...")

        self.custom_wordlist_path = None

        self.words_slider.valueChanged.connect(
            lambda value: self.words_value.setText(str(value))
        )

        self.wordlist_combo.currentIndexChanged.connect(
            self.select_wordlist
        )

        layout.addWidget(self.words_label)
        layout.addWidget(self.words_value)
        layout.addWidget(self.words_slider)

        layout.addWidget(self.separator_label)
        layout.addWidget(self.separator_combo)

        layout.addWidget(self.wordlist_label)
        layout.addWidget(self.wordlist_combo)

        # Password
        self.password_field = QLineEdit()
        self.password_field.setReadOnly(True)

        layout.addWidget(self.password_field)

        # Buttons
        button_layout = QHBoxLayout()

        self.generate_button = QPushButton("Generate Password")
        self.generate_button.clicked.connect(self.generate_password)

        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_password)

        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.copy_button)

        layout.addLayout(button_layout)

    def select_wordlist(self, index):
        if index != 1:
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
