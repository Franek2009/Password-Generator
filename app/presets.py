"""Validated, versioned generator presets. No generated result belongs here."""

import json
import re
import unicodedata
from dataclasses import dataclass
from uuid import uuid4

from PySide6.QtCore import QSettings

from app.advanced_rules import AdvancedRules
from app.config import SUPPORTED_SEPARATORS, PasswordConfig, PasswordMode

CUSTOM_ID = re.compile(r"custom-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")

RESERVED_NAMES = {"STANDARD", "MOCNE", "STRONG", "FRAZA", "PHRASE"}


def preset_name(value):
    if not isinstance(value, str):
        raise ValueError("preset_invalid")  # noqa: TRY004 - stable validation API
    name = unicodedata.normalize("NFKC", value).strip()
    if not 1 <= len(name) <= 64 or any(
        unicodedata.category(c).startswith("C") for c in name
    ):
        raise ValueError("preset_invalid")
    return name


def parameters(config):
    """Explicit whitelist scoped to the active generator mode."""
    if config.mode == PasswordMode.MANAGER:
        return {
            "mode": "manager",
            "length": config.length,
            "uppercase": config.uppercase,
            "lowercase": config.lowercase,
            "numbers": config.numbers,
            "special": config.special,
            "exclude_similar": config.exclude_similar,
            "advanced": config.advanced.to_data(),
        }
    return {
        "mode": "human",
        "words": config.words,
        "separator": config.separator,
        "numbers": config.numbers,
        "special": config.special,
        "wordlist": config.wordlist_path or "",
    }


def validate_parameters(data, version=2):
    if type(version) is not int or version not in (1, 2):
        raise ValueError("preset_version")
    if not isinstance(data, dict):
        raise ValueError("preset_invalid")  # noqa: TRY004 - stable validation API
    mode = data.get("mode")
    boolean_keys = ["numbers", "special"]
    if mode == "manager":
        expected = {
            "mode",
            "length",
            "uppercase",
            "lowercase",
            "numbers",
            "special",
            "exclude_similar",
        }
        if version == 2:
            expected.add("advanced")
        boolean_keys += ["uppercase", "lowercase", "exclude_similar"]
        if type(data.get("length")) is not int or not 8 <= data["length"] <= 64:
            raise ValueError("preset_invalid")
    elif mode == "human":
        expected = {"mode", "words", "separator", "numbers", "special", "wordlist"}
        if (
            type(data.get("words")) is not int
            or not 2 <= data["words"] <= 8
            or not isinstance(data.get("separator"), str)
            or data["separator"] not in SUPPORTED_SEPARATORS
            or not isinstance(data.get("wordlist"), str)
            or "\0" in data["wordlist"]
        ):
            raise ValueError("preset_invalid")
    else:
        raise ValueError("preset_invalid")
    if set(data) != expected or any(
        type(data.get(k)) is not bool for k in boolean_keys
    ):
        raise ValueError("preset_invalid")
    if mode == "manager" and not any(
        data[k] for k in ["uppercase", "lowercase", "numbers", "special"]
    ):
        raise ValueError("preset_invalid")
    result = dict(data)
    if mode == "manager":
        rules = (
            AdvancedRules.from_data(data["advanced"])
            if version == 2
            else AdvancedRules()
        )
        result["advanced"] = rules.to_data()
        PasswordConfig(
            length=data["length"],
            uppercase=data["uppercase"],
            lowercase=data["lowercase"],
            numbers=data["numbers"],
            special=data["special"],
            exclude_similar=data["exclude_similar"],
            advanced=rules,
        ).validate()
    return result


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    config: dict
    builtin: bool = False


def builtins():
    return [
        Preset(
            "standard", "preset_standard", parameters(PasswordConfig(length=16)), True
        ),
        Preset("strong", "preset_strong", parameters(PasswordConfig(length=24)), True),
        Preset(
            "phrase",
            "preset_phrase",
            parameters(
                PasswordConfig(
                    mode=PasswordMode.HUMAN, words=5, numbers=False, special=False
                )
            ),
            True,
        ),
    ]


class PresetStore:
    def __init__(self, settings):
        self.settings = settings
        self.custom = []
        self.invalid = False
        self.write_blocked = False
        self.key = "presets_v2"
        version = 2 if settings.contains(self.key) else 1
        raw = settings.value(self.key if version == 2 else "presets", "")
        if not raw and version == 1:
            return
        try:
            root = json.loads(raw)
            if (
                not isinstance(root, dict)
                or set(root) != {"version", "presets"}
                or type(root["version"]) is not int
                or root["version"] != version
                or not isinstance(root["presets"], list)
            ):
                self.write_blocked = (
                    isinstance(root, dict)
                    and type(root.get("version")) is int
                    and root["version"] not in (1, 2)
                )
                raise ValueError()
            names, ids = set(RESERVED_NAMES), {p.id for p in builtins()}
            for item in root["presets"]:
                try:
                    if not isinstance(item, dict) or set(item) != {
                        "id",
                        "name",
                        "config",
                    }:
                        raise ValueError()
                    name = preset_name(item["name"])
                    identity = item["id"]
                    if (
                        not isinstance(identity, str)
                        or not CUSTOM_ID.fullmatch(identity)
                        or identity in ids
                        or name.upper() in names
                    ):
                        raise ValueError()
                    config = validate_parameters(item["config"], version)
                    self.custom.append(Preset(identity, name, config))
                    names.add(name.upper())
                    ids.add(identity)
                except (ValueError, TypeError, KeyError):
                    self.invalid = True
        except (ValueError, TypeError, RecursionError):
            self.invalid = True

    @property
    def all(self):
        return builtins() + self.custom

    def save(self, name, config):
        name = preset_name(name)
        if name.upper() in RESERVED_NAMES | {p.name.upper() for p in self.custom}:
            raise ValueError("preset_duplicate")
        preset = Preset(
            "custom-" + str(uuid4()), name, validate_parameters(parameters(config))
        )
        proposed = self.custom + [preset]
        self._write(proposed)
        self.custom = proposed
        return preset

    def update(self, identity, config):
        preset = self._custom(identity)
        replacement = Preset(
            preset.id, preset.name, validate_parameters(parameters(config))
        )
        self._replace(replacement)
        return replacement

    def rename(self, identity, name):
        preset = self._custom(identity)
        name = preset_name(name)
        if name.upper() in RESERVED_NAMES or any(
            p.id != identity and p.name.upper() == name.upper() for p in self.custom
        ):
            raise ValueError("preset_duplicate")
        replacement = Preset(preset.id, name, preset.config)
        self._replace(replacement)
        return replacement

    def _custom(self, identity):
        preset = next((p for p in self.custom if p.id == identity), None)
        if preset is None:
            raise ValueError("preset_invalid")
        return preset

    def _replace(self, preset):
        proposed = [preset if p.id == preset.id else p for p in self.custom]
        self._write(proposed)
        self.custom = proposed

    def delete(self, identity):
        if identity not in {p.id for p in self.custom}:
            raise ValueError("preset_invalid")
        proposed = [p for p in self.custom if p.id != identity]
        self._write(proposed)
        self.custom = proposed

    def _write(self, proposed):
        if self.write_blocked:
            raise ValueError("preset_version")
        payload = json.dumps(
            {
                "version": 2,
                "presets": [
                    {"id": p.id, "name": p.name, "config": p.config} for p in proposed
                ],
            },
            ensure_ascii=False,
        )
        existed = self.settings.contains(self.key)
        previous = self.settings.value(self.key)
        try:
            self.settings.setValue(self.key, payload)
            self.settings.sync()
            if self.settings.status() != QSettings.NoError:
                raise ValueError("settings_write")
        except (OSError, RuntimeError, ValueError) as error:
            # QSettings can update its cache before reporting a disk failure.
            try:
                if existed:
                    self.settings.setValue(self.key, previous)
                else:
                    self.settings.remove(self.key)
                self.settings.sync()
            except (OSError, RuntimeError):
                pass
            raise ValueError("settings_write") from error
