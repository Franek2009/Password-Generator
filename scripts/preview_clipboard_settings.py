"""Capture running clipboard settings without changing the system clipboard."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.presentation import Preferences
from app.ui import MainWindow


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/v1.5.0/preview")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="clipboard-settings-preview-") as directory:
        prefs = Preferences(
            QSettings(str(Path(directory) / "settings.ini"), QSettings.IniFormat)
        )
        prefs.set("language", "pl")
        prefs.set("clipboard_clear_seconds", 60)
        window = MainWindow(prefs)
        window.show()
        window.open_settings()
        dialog = window._settings_dialog
        for theme in ("light", "dark"):
            window.set_preference("theme", theme)
            app.processEvents()
            assert dialog.controls["clipboard_clear_seconds"].currentData() == 60
            assert dialog.grab().save(str(output / f"desktop-{theme}-clipboard.png"))
        dialog.close()
        window.close()
    print(output.resolve())


if __name__ == "__main__":
    main()
