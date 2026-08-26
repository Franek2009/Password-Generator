from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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

    def copy_password(self):
        password = self.password_field.text()

        if password:
            QApplication.clipboard().setText(password)

    def generate_password(self):
        config = PasswordConfig(
            mode=self.mode_combo.currentData(),
            length=self.length_slider.value(),
            uppercase=self.uppercase_checkbox.isChecked(),
            lowercase=self.lowercase_checkbox.isChecked(),
            numbers=self.numbers_checkbox.isChecked(),
            special=self.special_checkbox.isChecked(),
        )

        password = generate_password_from_config(config)

        self.password_field.setText(password)


def run_app():
    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
