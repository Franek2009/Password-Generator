"""Shared UI vocabulary, color tokens and persisted non-secret preferences."""

import json

from PySide6.QtCore import QLocale, QSettings

from app.advanced_rules import AdvancedRules
from app.clipboard import CLEAR_SECONDS
from app.resources import resource_path

UI = json.loads(resource_path("data", "ui.json").read_text(encoding="utf-8"))
DEFAULTS = {
    "language": "system",
    "theme": "system",
    "auto_copy": False,
    "clipboard_clear_seconds": 0,
    "transcription": False,
    "exclude_similar": False,
    "mode": 0,
    "length": 20,
    "words": 3,
    "separator": "-",
    "wordlist": "",
    "uppercase": True,
    "lowercase": True,
    "manager_numbers": True,
    "manager_special": True,
    "human_numbers": True,
    "human_special": True,
}


def language_for(value):
    return (
        ("pl" if QLocale.system().name().startswith("pl") else "en")
        if value == "system"
        else value
    )


class Preferences:
    def __init__(self, store=None):
        self.store = (
            store
            if store is not None
            else QSettings("PasswordGenerator", "PasswordGenerator")
        )
        self.values = {}
        choices = {
            "language": ["system", "pl", "en"],
            "theme": ["system", "light", "dark"],
            "mode": [0, 1],
            "clipboard_clear_seconds": CLEAR_SECONDS,
            "length": range(8, 65),
            "words": range(2, 9),
            "separator": ["-", "_", ".", " ", "/", "|", "Random"],
        }
        for key, default in DEFAULTS.items():
            value = self.store.value(key, default)
            if isinstance(default, bool):
                value = (
                    value
                    if isinstance(value, bool)
                    else {"true": True, "false": False}.get(str(value).lower(), default)
                )
            elif isinstance(default, int):
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = default
            if key in choices and value not in choices[key]:
                value = default
            if key == "wordlist" and not isinstance(value, str):
                value = ""
            self.values[key] = value
        self.advanced = AdvancedRules()
        self.rules_invalid = False
        if self.store.contains("advanced_rules_v1"):
            try:
                self.advanced = AdvancedRules.from_data(
                    json.loads(self.store.value("advanced_rules_v1"))
                )
            except (ValueError, TypeError, RecursionError):
                self.rules_invalid = True

    def set_advanced(self, rules):
        data = rules.to_data()
        self.store.setValue("advanced_rules_v1", json.dumps(data))
        self.store.sync()
        if self.store.status() != QSettings.NoError:
            raise ValueError("settings_write")
        self.advanced = AdvancedRules.from_data(data)

    def set(self, key, value):
        if key not in DEFAULTS:
            raise KeyError(key)
        self.values[key] = value
        self.store.setValue(key, value)

    def text(self, key):
        return UI["strings"][language_for(self.values["language"])].get(
            key, UI["strings"]["en"]["unknown_error"]
        )
