from dataclasses import dataclass
from enum import Enum


class PasswordMode(Enum):
    HUMAN = "human"
    MANAGER = "manager"


@dataclass
class PasswordConfig:
    mode: PasswordMode = PasswordMode.MANAGER
    length: int = 20
    uppercase: bool = True
    lowercase: bool = True
    numbers: bool = True
    special: bool = True
    words: int = 3
    separator: str = "-"
    wordlist_path: str | None = None

    def validate(self) -> None:
        if self.mode == PasswordMode.MANAGER:
            self._validate_manager()
        elif self.mode == PasswordMode.HUMAN:
            self._validate_human()
        else:
            raise ValueError("Unsupported password mode.")

    def _validate_manager(self) -> None:
        character_sets_enabled = sum(
            [
                self.uppercase,
                self.lowercase,
                self.numbers,
                self.special,
            ]
        )

        if character_sets_enabled == 0:
            raise ValueError(
                "At least one character set must be enabled."
            )

        if self.length < character_sets_enabled:
            raise ValueError(
                "Password length is too short for the selected "
                "character sets."
            )

    def _validate_human(self) -> None:
        if self.words < 1:
            raise ValueError("Number of words must be at least 1.")

        if not self.separator:
            raise ValueError("Separator cannot be empty.")
