"""Non-secret, versioned advanced random-password parameters."""

from dataclasses import asdict, dataclass
from enum import Enum

from app.errors import GenerationError


class CharacterType(str, Enum):
    ANY = "any"
    LETTER = "letter"
    UPPER = "upper"
    LOWER = "lower"
    DIGIT = "digit"
    SYMBOL = "symbol"


@dataclass(frozen=True)
class AdvancedRules:
    enabled: bool = False
    min_uppercase: int = 0
    min_lowercase: int = 0
    min_digits: int = 0
    min_symbols: int = 0
    custom_alphabet_enabled: bool = False
    custom_alphabet: str = ""
    forbidden_characters: str = ""
    first_type: CharacterType = CharacterType.ANY
    last_type: CharacterType = CharacterType.ANY
    max_identical_run: int | None = None

    @property
    def minima(self):
        return (
            self.min_uppercase,
            self.min_lowercase,
            self.min_digits,
            self.min_symbols,
        )

    def validate_structure(self):
        if any(
            type(v) is not bool for v in (self.enabled, self.custom_alphabet_enabled)
        ):
            raise GenerationError("rules_invalid", "Invalid rule flags.")
        if any(type(v) is not int or not 0 <= v <= 64 for v in self.minima):
            raise GenerationError(
                "rules_invalid", "Minima must be integers from 0 to 64."
            )
        if self.max_identical_run is not None and (
            type(self.max_identical_run) is not int
            or not 1 <= self.max_identical_run <= 64
        ):
            raise GenerationError(
                "rules_invalid", "Run limit must be an integer from 1 to 64."
            )
        if not isinstance(self.first_type, CharacterType) or not isinstance(
            self.last_type, CharacterType
        ):
            raise GenerationError("rules_invalid", "Unknown position rule.")
        for value in (self.custom_alphabet, self.forbidden_characters):
            if not isinstance(value, str) or any(
                not 33 <= ord(c) <= 126 for c in value
            ):
                raise GenerationError(
                    "rules_ascii",
                    "Use visible ASCII characters (33–126), without spaces.",
                )

    def to_data(self):
        self.validate_structure()
        data = asdict(self)
        data["first_type"] = self.first_type.value
        data["last_type"] = self.last_type.value
        # Duplicate entries carry no weight; canonicalize persisted alphabets.
        for key in ("custom_alphabet", "forbidden_characters"):
            data[key] = "".join(sorted(set(data[key])))
        return data

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise GenerationError("rules_invalid", "Invalid advanced rule fields.")
        try:
            fields = dict(data)
            fields["first_type"] = CharacterType(fields["first_type"])
            fields["last_type"] = CharacterType(fields["last_type"])
            result = cls(**fields)
            result.validate_structure()
            return result
        except (TypeError, ValueError) as error:
            raise GenerationError(
                "rules_invalid", "Invalid advanced rule data."
            ) from error
