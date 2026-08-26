import json
import secrets
import string
from pathlib import Path

from app.config import PasswordConfig, PasswordMode


WORDS_FILE = Path(__file__).parent.parent / "data" / "words.json"


def load_words() -> list[str]:
    with WORDS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def generate_human_password(config: PasswordConfig) -> str:
    words = load_words()

    if config.words < 1:
        raise ValueError("Number of words must be at least 1.")

    selected_words = [
        secrets.choice(words)
        for _ in range(config.words)
    ]

    password = config.separator.join(selected_words)

    if config.numbers:
        password += str(secrets.randbelow(100))

    if config.special:
        special_characters = string.punctuation.replace(
            config.separator, ""
        )
        password += secrets.choice(special_characters)

    return password


def generate_manager_password(config: PasswordConfig) -> str:
    character_sets = []

    if config.lowercase:
        character_sets.append(string.ascii_lowercase)

    if config.uppercase:
        character_sets.append(string.ascii_uppercase)

    if config.numbers:
        character_sets.append(string.digits)

    if config.special:
        character_sets.append(string.punctuation)

    if not character_sets:
        raise ValueError("At least one character set must be enabled.")

    if config.length < len(character_sets):
        raise ValueError(
            "Password length is too short for the selected character sets."
        )

    password = [
        secrets.choice(character_set)
        for character_set in character_sets
    ]

    all_characters = "".join(character_sets)

    password += [
        secrets.choice(all_characters)
        for _ in range(config.length - len(password))
    ]

    secrets.SystemRandom().shuffle(password)

    return "".join(password)


def generate_password(config: PasswordConfig) -> str:
    if config.mode == PasswordMode.HUMAN:
        return generate_human_password(config)

    return generate_manager_password(config)
