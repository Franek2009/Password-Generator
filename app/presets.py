"""Validated, versioned generator presets. No generated result belongs here."""

import json
import re
import unicodedata
from dataclasses import dataclass
from uuid import uuid4

from app.config import SUPPORTED_SEPARATORS, PasswordConfig, PasswordMode

CUSTOM_ID = re.compile(r"custom-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")

RESERVED_NAMES = {"STANDARD", "MOCNE", "STRONG", "FRAZA", "PHRASE"}


def preset_name(value):
    if not isinstance(value, str):
        raise ValueError("preset_invalid")
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
        }
    return {
        "mode": "human",
        "words": config.words,
        "separator": config.separator,
        "numbers": config.numbers,
        "special": config.special,
        "wordlist": config.wordlist_path or "",
    }


def validate_parameters(data):
    if not isinstance(data, dict):
        raise ValueError("preset_invalid")
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
    return dict(data)


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
        raw = settings.value("presets", "")
        if not raw:
            return
        try:
            root = json.loads(raw)
            if (
                not isinstance(root, dict)
                or set(root) != {"version", "presets"}
                or type(root["version"]) is not int
                or root["version"] != 1
                or not isinstance(root["presets"], list)
            ):
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
                    config = validate_parameters(item["config"])
                    self.custom.append(Preset(identity, name, config))
                    names.add(name.upper())
                    ids.add(identity)
                except (ValueError, TypeError, KeyError):
                    self.invalid = True
        except (ValueError, TypeError):
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
        self.custom.append(preset)
        self._write()
        return preset

    def delete(self, identity):
        if identity not in {p.id for p in self.custom}:
            raise ValueError("preset_invalid")
        self.custom = [p for p in self.custom if p.id != identity]
        self._write()

    def _write(self):
        self.settings.setValue(
            "presets",
            json.dumps(
                {
                    "version": 1,
                    "presets": [
                        {"id": p.id, "name": p.name, "config": p.config}
                        for p in self.custom
                    ],
                },
                ensure_ascii=False,
            ),
        )
