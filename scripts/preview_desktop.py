"""Generate review screenshots using isolated settings and non-secret example data."""

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.presentation import Preferences
from app.ui import MainWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/v1.2.0-preview"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="password-preview-") as directory:
        preferences = Preferences(
            QSettings(str(Path(directory) / "preview.ini"), QSettings.IniFormat)
        )
        preferences.set("language", "pl")
        window = MainWindow(preferences)
        window.show()
        window.transcription_checkbox.setChecked(True)
        window.exclude_similar_checkbox.setChecked(True)
        for theme in ["dark", "light"]:
            window.set_preference("theme", theme)
            for mode, name, password in [
                (0, "random", "k8Z!rQ4#mP9vL2@t"),
                (1, "phrase", "Rower-Las-Zamek-Polana-Dom"),
            ]:
                window.tabs.setCurrentIndex(mode)
                window.apply_preset(window.presets.all[0 if mode == 0 else 2])
                window.transcription_checkbox.setChecked(True)
                if mode == 0:
                    window.exclude_similar_checkbox.setChecked(True)
                    existing = next(
                        (p for p in window.presets.custom if p.name == "Przepisywanie"),
                        None,
                    )
                    if existing:
                        window.apply_preset(existing)
                    else:
                        window.save_preset("Przepisywanie")
                window.password_field.setText(password)
                app.processEvents()
                window.grab().save(str(args.output / f"desktop-{theme}-{name}.png"))
                if mode == 0:
                    window.apply_preset(window.presets.all[1])
                    window.password_field.setText("k8Z!rQ4#mP9vL2@tX7#qM3!v")
                    app.processEvents()
                    window.grab().save(str(args.output / f"desktop-{theme}-strong.png"))
            window.open_settings()
            window._settings_dialog.navigation.setCurrentRow(
                0 if theme == "dark" else 1
            )
            app.processEvents()
            window._settings_dialog.grab().save(
                str(args.output / f"desktop-{theme}-settings.png")
            )
            window._settings_dialog.hide()
        window.set_preference("language", "en")
        window.resize(560, 500)
        app.processEvents()
        window.grab().save(str(args.output / "desktop-english-narrow.png"))
        window.close()
    print(args.output.resolve())


if __name__ == "__main__":
    main()
