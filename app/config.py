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
    language = "pl"
