"""Capture preset editing with isolated settings and a public generated example."""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app.advanced_rules import AdvancedRules, CharacterType
from app.presentation import Preferences
from app.ui import MainWindow


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/v1.4.0/preview")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="preset-editing-preview-") as directory:
        prefs = Preferences(
            QSettings(str(Path(directory) / "settings.ini"), QSettings.IniFormat)
        )
        prefs.set("language", "en")
        window = MainWindow(prefs)
        window.resize(560, 800)
        window.show()
        window.length_spin.setValue(8)
        window.rules_panel.restore(
            AdvancedRules(
                enabled=True,
                custom_alphabet_enabled=True,
                custom_alphabet="a1",
                first_type=CharacterType.LOWER,
                max_identical_run=1,
            )
        )
        window.rules_changed()
        window.generate_password()
        while window.working:
            app.processEvents()
            time.sleep(0.01)
        assert window.password_field.text() == "a1a1a1a1"
        window.save_preset("Example")
        while window.working:
            app.processEvents()
            time.sleep(0.01)
        window.length_spin.setValue(10)
        assert window.update_preset_action.isEnabled()
        for theme in ("light", "dark"):
            window.set_preference("theme", theme)
            app.processEvents()
            assert window.grab().save(str(output / f"desktop-{theme}-preset-edit.png"))

            def capture_dialog(theme=theme):
                dialog = app.activeModalWidget()
                assert isinstance(dialog, QMessageBox)
                assert "Example" in dialog.text()
                assert dialog.grab().save(
                    str(output / f"desktop-{theme}-preset-confirm.png")
                )
                dialog.done(QMessageBox.No)

            QTimer.singleShot(150, capture_dialog)
            window.prompt_update_preset()
        assert window.presets.custom[0].config["length"] == 8
        window.close()
    print(output.resolve())


if __name__ == "__main__":
    main()
