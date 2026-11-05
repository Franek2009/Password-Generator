"""Capture the running advanced UI using a deliberately forced public example."""

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.advanced_rules import AdvancedRules, CharacterType
from app.presentation import Preferences
from app.ui import MainWindow


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/v1.3.0/preview")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="advanced-preview-") as directory:
        prefs = Preferences(
            QSettings(str(Path(directory) / "settings.ini"), QSettings.IniFormat)
        )
        prefs.set("language", "pl")
        window = MainWindow(prefs)
        window.resize(760, 1400)
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
        window.transcription_checkbox.setChecked(True)
        for theme in ("light", "dark"):
            window.set_preference("theme", theme)
            window.rules_panel.toggle.setChecked(True)
            app.processEvents()
            assert window.rules_panel.body.isVisible()
            assert window.grab().save(str(output / f"desktop-{theme}-rules.png"))
            window.rules_panel.toggle.setChecked(False)
            window.resize(560, 800)
            app.processEvents()
            assert window.grab().save(str(output / f"desktop-{theme}-narrow.png"))
            window.resize(760, 1400)
        window.close()
    print(output.resolve())


if __name__ == "__main__":
    main()
