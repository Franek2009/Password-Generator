from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.resources import resource_path


APP_NAME = "Password Generator"
APP_VERSION = "1.0.0"


def configure_application(application: QApplication) -> None:
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setApplicationVersion(APP_VERSION)

    icon_path = resource_path("assets", "icon.png")
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
