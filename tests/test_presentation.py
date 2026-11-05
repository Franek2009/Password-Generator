from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from app.config import PasswordConfig
from app.errors import GenerationError
from app.presentation import UI, Preferences


def test_android_and_desktop_share_identical_design_and_translation_data():
    assert (
        Path("data/ui.json").read_bytes()
        == Path("android/app/src/main/assets/ui.json").read_bytes()
    )
    assert UI["strings"]["pl"].keys() == UI["strings"]["en"].keys()
    assert all(UI["strings"][language].values() for language in ("en", "pl"))


def test_invalid_preferences_fall_back_to_supported_defaults(tmp_path):
    store = QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)
    for key, value in {
        "language": "fr",
        "theme": "purple",
        "length": "broken",
        "words": 999,
        "separator": "?",
        "uppercase": "garbage",
    }.items():
        store.setValue(key, value)
    values = Preferences(store).values
    assert values["language"] == "system"
    assert values["theme"] == "system"
    assert values["length"] == 20
    assert values["words"] == 3
    assert values["separator"] == "-"
    assert values["uppercase"] is True


def test_validation_has_stable_translation_code_and_valueerror_compatibility():
    with pytest.raises(ValueError) as result:
        PasswordConfig(
            uppercase=False, lowercase=False, numbers=False, special=False
        ).validate()
    assert isinstance(result.value, GenerationError)
    assert result.value.code == "no_sets"
    assert result.value.code in UI["strings"]["pl"]


def test_advanced_preferences_roundtrip_and_invalid_read(tmp_path):
    import json

    from app.advanced_rules import AdvancedRules

    store = QSettings(str(tmp_path / "advanced.ini"), QSettings.IniFormat)
    prefs = Preferences(store)
    rules = AdvancedRules(
        enabled=True, min_digits=3, custom_alphabet_enabled=True, custom_alphabet="aA2!"
    )
    prefs.set_advanced(rules)
    assert Preferences(store).advanced.to_data() == rules.to_data()
    store.setValue("advanced_rules_v1", json.dumps({"password": "never-used"}))
    read = Preferences(store)
    assert read.rules_invalid and not read.advanced.enabled
    assert store.value("advanced_rules_v1") == json.dumps({"password": "never-used"})
