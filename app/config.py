from dataclasses import dataclass
from enum import Enum

from app.errors import GenerationError


class PasswordMode(Enum):
    HUMAN = "human"
    MANAGER = "manager"


SUPPORTED_SEPARATORS = {
    "-",
    "_",
    ".",
    " ",
    "/",
    "|",
    "Random",
}


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
            raise GenerationError("unknown_error", "Unsupported password mode.")

    def _validate_manager(self) -> None:
        if self.length < 1:
            raise GenerationError(
                "invalid_length", "Password length must be at least 1."
            )

        character_sets_enabled = sum(
            [
                self.uppercase,
                self.lowercase,
                self.numbers,
                self.special,
            ]
        )

        if character_sets_enabled == 0:
            raise GenerationError(
                "no_sets", "At least one character set must be enabled."
            )

        if self.length < character_sets_enabled:
            raise GenerationError(
                "short_length",
                "Password length is too short for the selected character sets.",
            )

    def _validate_human(self) -> None:
        if self.words < 1:
            raise GenerationError(
                "invalid_words", "Number of words must be at least 1."
            )

        if not self.separator:
            raise GenerationError("invalid_separator", "Separator cannot be empty.")

        if self.separator not in SUPPORTED_SEPARATORS:
            raise GenerationError(
                "invalid_separator", f"Unsupported separator: {self.separator}"
            )
