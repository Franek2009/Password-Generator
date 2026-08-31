from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.resources import resource_path
from app.versioning import get_application_version


APP_NAME = "Password Generator"


def configure_application(application: QApplication) -> None:
    application.setApplicationName(APP_NAME)
    application.setApplicationDisplayName(APP_NAME)
    application.setApplicationVersion(get_application_version())

    icon_path = resource_path("assets", "icon.png")
    if icon_path.is_file():
        application.setWindowIcon(QIcon(str(icon_path)))
