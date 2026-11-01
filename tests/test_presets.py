import json

import pytest
from PySide6.QtCore import QSettings

from app.config import PasswordConfig, PasswordMode
from app.presets import PresetStore, builtins


def test_builtin_contract():
    standard, strong, phrase = builtins()
    assert [standard.config["length"], strong.config["length"]] == [16, 24]
    assert phrase.config == {
        "mode": "human",
        "words": 5,
        "separator": "-",
        "numbers": False,
        "special": False,
        "wordlist": "",
    }


def test_roundtrip_and_delete(tmp_path):
    settings = QSettings(str(tmp_path / "presets.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    preset = store.save("  Travel  ", PasswordConfig(length=32, exclude_similar=True))
    assert preset.name == "Travel"
    assert PresetStore(settings).custom == [preset]
    assert set(preset.config) == {
        "mode",
        "length",
        "uppercase",
        "lowercase",
        "numbers",
        "special",
        "exclude_similar",
    }
    with pytest.raises(ValueError):
        store.save("TRAVEL", PasswordConfig())
    with pytest.raises(ValueError):
        store.save("Standard", PasswordConfig())
    with pytest.raises(ValueError):
        store.delete("standard")
    store.delete(preset.id)
    assert not PresetStore(settings).custom


@pytest.mark.parametrize(
    "raw",
    ["null", "[]", "{", '{"version":true,"presets":[]}', '{"version":2,"presets":[]}'],
)
def test_corrupt_root_is_not_overwritten(tmp_path, raw):
    settings = QSettings(str(tmp_path / "presets.ini"), QSettings.IniFormat)
    settings.setValue("presets", raw)
    store = PresetStore(settings)
    assert store.invalid and not store.custom
    assert settings.value("presets") == raw


@pytest.mark.parametrize(
    "change",
    [
        {"length": True},
        {"length": 65},
        {"uppercase": "false"},
        {"password": "secret"},
        {"exclude_similar": None},
    ],
)
def test_invalid_record_preserves_valid_neighbor(tmp_path, change):
    settings = QSettings(str(tmp_path / "presets.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    store.save("Valid", PasswordConfig())
    data = json.loads(settings.value("presets"))
    bad = {
        "id": "custom-00000000-0000-4000-8000-000000000000",
        "name": "Bad",
        "config": {**data["presets"][0]["config"], **change},
    }
    data["presets"].append(bad)
    settings.setValue("presets", json.dumps(data))
    loaded = PresetStore(settings)
    assert loaded.invalid
    assert [p.name for p in loaded.custom] == ["Valid"]


def test_phrase_only_contains_active_parameters(tmp_path):
    store = PresetStore(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat))
    preset = store.save(
        "Words", PasswordConfig(mode=PasswordMode.HUMAN, wordlist_path="/missing.txt")
    )
    assert preset.config["wordlist"] == "/missing.txt"
    assert "length" not in preset.config


def test_cross_platform_contract():
    from pathlib import Path

    from app.generator import SIMILAR_CHARACTERS

    fixture = json.loads(
        (Path(__file__).parent / "fixtures/preset_contract.json").read_text()
    )
    assert fixture["similar_characters"] == SIMILAR_CHARACTERS
    assert fixture["builtins"] == [{"id": p.id, "config": p.config} for p in builtins()]
