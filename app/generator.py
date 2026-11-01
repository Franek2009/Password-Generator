import secrets
import string

from app.config import PasswordConfig, PasswordMode
from app.errors import GenerationError
from app.wordlist import load_wordlist, load_words

SIMILAR_CHARACTERS = "0Oo1Il"

RANDOM_SEPARATORS = ["-", "_", ".", " ", "/", "|"]


def _select_words(words: list[str], count: int) -> list[str]:
    if count <= len(words):
        return secrets.SystemRandom().sample(words, count)

    selected_words = list(words)

    selected_words.extend(secrets.choice(words) for _ in range(count - len(words)))

    secrets.SystemRandom().shuffle(selected_words)

    return selected_words


def _generate_human_password(config: PasswordConfig) -> str:
    if config.wordlist_path:
        words = load_wordlist(config.wordlist_path)
    else:
        words = load_words()

    if not words:
        raise GenerationError("empty_words", "Word list cannot be empty.")

    selected_words = [word.capitalize() for word in _select_words(words, config.words)]

    if config.separator == "Random":
        separator = secrets.choice(RANDOM_SEPARATORS)
    else:
        separator = config.separator

    parts = selected_words

    if config.numbers:
        parts.append(str(secrets.randbelow(100)))

    if config.special:
        special_characters = string.punctuation.replace(
            separator,
            "",
        )

        if not special_characters:
            raise GenerationError(
                "invalid_separator",
                "No special characters available for the selected separator.",
            )

        parts.append(secrets.choice(special_characters))

    secrets.SystemRandom().shuffle(parts)

    return separator.join(parts)


def generate_human_password(config: PasswordConfig) -> str:
    config.validate()
    return _generate_human_password(config)


def _generate_manager_password(config: PasswordConfig) -> str:
    character_sets = []

    if config.lowercase:
        character_sets.append(string.ascii_lowercase)

    if config.uppercase:
        character_sets.append(string.ascii_uppercase)

    if config.numbers:
        character_sets.append(string.digits)

    if config.special:
        character_sets.append(string.punctuation)

    if config.exclude_similar:
        character_sets = [
            "".join(c for c in pool if c not in SIMILAR_CHARACTERS)
            for pool in character_sets
        ]
    if any(not pool for pool in character_sets) or not character_sets:
        raise GenerationError(
            "empty_characters", "No characters available in a selected set."
        )

    password = [secrets.choice(character_set) for character_set in character_sets]

    all_characters = "".join(character_sets)

    password += [
        secrets.choice(all_characters) for _ in range(config.length - len(password))
    ]

    secrets.SystemRandom().shuffle(password)

    return "".join(password)


def generate_manager_password(config: PasswordConfig) -> str:
    config.validate()
    return _generate_manager_password(config)


def generate_password(config: PasswordConfig) -> str:
    config.validate()

    if config.mode == PasswordMode.HUMAN:
        return _generate_human_password(config)

    return _generate_manager_password(config)
