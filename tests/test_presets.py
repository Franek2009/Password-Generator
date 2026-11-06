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
        "advanced",
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
    data = json.loads(settings.value("presets_v2"))
    bad = {
        "id": "custom-00000000-0000-4000-8000-000000000000",
        "name": "Bad",
        "config": {**data["presets"][0]["config"], **change},
    }
    data["presets"].append(bad)
    settings.setValue("presets_v2", json.dumps(data))
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


def test_v1_migration_is_lazy_and_preserves_original(tmp_path):
    from pathlib import Path

    settings = QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)
    original = (Path(__file__).parent / "fixtures/legacy_presets_v1.json").read_text()
    settings.setValue("presets", original)
    loaded = PresetStore(settings)
    assert not loaded.invalid and len(loaded.custom) == 2
    assert not settings.contains("presets_v2")
    assert loaded.custom[0].config["advanced"]["enabled"] is False
    loaded.save("New entry", PasswordConfig())
    assert json.loads(settings.value("presets_v2"))["version"] == 2
    assert settings.value("presets") == original
    assert len(PresetStore(settings).custom) == 3


def test_corrupt_v2_does_not_fall_back_to_v1(tmp_path):
    from pathlib import Path

    settings = QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)
    settings.setValue(
        "presets",
        (Path(__file__).parent / "fixtures/legacy_presets_v1.json").read_text(),
    )
    settings.setValue("presets_v2", "{")
    loaded = PresetStore(settings)
    assert loaded.invalid and not loaded.custom
    assert settings.value("presets_v2") == "{"


def test_unknown_version_blocks_writing(tmp_path):
    settings = QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)
    original = '{"version":3,"presets":[]}'
    settings.setValue("presets_v2", original)
    loaded = PresetStore(settings)
    with pytest.raises(ValueError, match="preset_version"):
        loaded.save("New entry", PasswordConfig())
    assert settings.value("presets_v2") == original


def test_failed_write_keeps_in_memory_presets(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    monkeypatch.setattr(settings, "status", lambda: QSettings.AccessError)
    with pytest.raises(ValueError, match="settings_write"):
        store.save("Not saved", PasswordConfig())
    assert not store.custom


def test_unknown_validation_schema_is_never_treated_as_legacy():
    from app.presets import builtins, validate_parameters

    for version in (0, 3, True, "2"):
        with pytest.raises(ValueError, match="preset_version"):
            validate_parameters(builtins()[0].config, version=version)


def test_edit_roundtrip_identity_order_and_secret_whitelist(tmp_path):
    settings = QSettings(str(tmp_path / "edit.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    first = store.save("First", PasswordConfig())
    second = store.save("Second", PasswordConfig())
    updated = store.update(first.id, PasswordConfig(length=32, exclude_similar=True))
    renamed = store.rename(first.id, "  FIRST renamed  ")
    assert updated.id == renamed.id == first.id
    assert renamed.name == "FIRST renamed"
    assert renamed.config == updated.config
    assert PresetStore(settings).custom == [renamed, second]
    assert json.loads(settings.value("presets_v2"))["version"] == 2
    assert "password" not in renamed.config
    assert store.rename(first.id, renamed.name) == renamed


def test_edit_rejects_missing_builtin_duplicates_and_invalid_config(tmp_path):
    settings = QSettings(str(tmp_path / "edit.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    first = store.save("First", PasswordConfig())
    store.save("Second", PasswordConfig())
    before = settings.value("presets_v2")
    for identity in ["missing", "standard", "strong", "phrase"]:
        with pytest.raises(ValueError):
            store.update(identity, PasswordConfig())
        with pytest.raises(ValueError):
            store.rename(identity, "Another")
    for name in ["SECOND", "Standard", "", "bad\nname"]:
        with pytest.raises(ValueError):
            store.rename(first.id, name)
    with pytest.raises(ValueError):
        store.update(first.id, PasswordConfig(length=65))
    assert settings.value("presets_v2") == before
    assert store.custom[0] == first


def test_failed_edits_preserve_memory_and_future_schema(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / "edit.ini"), QSettings.IniFormat)
    store = PresetStore(settings)
    first = store.save("First", PasswordConfig())
    original = settings.value("presets_v2")
    monkeypatch.setattr(settings, "status", lambda: QSettings.AccessError)
    for edit in [
        lambda: store.rename(first.id, "Other"),
        lambda: store.update(first.id, PasswordConfig(length=32)),
    ]:
        with pytest.raises(ValueError, match="settings_write"):
            edit()
        assert store.custom == [first]
        assert settings.value("presets_v2") == original
        assert PresetStore(settings).custom == [first]
    store.write_blocked = True
    with pytest.raises(ValueError, match="preset_version"):
        store.rename(first.id, "Other")
    assert store.custom == [first]


@pytest.mark.parametrize("operation", ["rename", "update"])
def test_edit_legacy_presets_migrates_without_rewriting_original(tmp_path, operation):
    from pathlib import Path

    settings = QSettings(str(tmp_path / "legacy-edit.ini"), QSettings.IniFormat)
    original = (Path(__file__).parent / "fixtures/legacy_presets_v1.json").read_text()
    settings.setValue("presets", original)
    store = PresetStore(settings)
    identity = store.custom[0].id
    if operation == "rename":
        edited = store.rename(identity, "Renamed legacy")
    else:
        edited = store.update(identity, PasswordConfig(length=32))
    assert settings.value("presets") == original
    assert json.loads(settings.value("presets_v2"))["version"] == 2
    assert PresetStore(settings).custom[0] == edited
    assert edited.id == identity
