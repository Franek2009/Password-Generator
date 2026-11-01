"""Shared UI vocabulary, color tokens and persisted non-secret preferences."""

import json

from PySide6.QtCore import QLocale, QSettings

from app.resources import resource_path

UI = json.loads(resource_path("data", "ui.json").read_text(encoding="utf-8"))
DEFAULTS = {
    "language": "system",
    "theme": "system",
    "auto_copy": False,
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

    def set(self, key, value):
        if key not in DEFAULTS:
            raise KeyError(key)
        self.values[key] = value
        self.store.setValue(key, value)

    def text(self, key):
        return UI["strings"][language_for(self.values["language"])].get(
            key, UI["strings"]["en"]["unknown_error"]
        )
