import secrets
import string

from app.config import PasswordConfig, PasswordMode
from app.wordlist import load_wordlist, load_words


RANDOM_SEPARATORS = ["-", "_", ".", " ", "/", "|"]


def _select_words(words: list[str], count: int) -> list[str]:
    if count <= len(words):
        return secrets.SystemRandom().sample(words, count)

    selected_words = list(words)

    selected_words.extend(
        secrets.choice(words)
        for _ in range(count - len(words))
    )

    secrets.SystemRandom().shuffle(selected_words)

    return selected_words


def generate_human_password(config: PasswordConfig) -> str:
    config.validate()

    if config.wordlist_path:
        words = load_wordlist(config.wordlist_path)
    else:
        words = load_words()

    if not words:
        raise ValueError("Word list cannot be empty.")

    selected_words = [
        word.capitalize()
        for word in _select_words(words, config.words)
    ]

    if config.separator == "Random":
        separator = secrets.choice(RANDOM_SEPARATORS)
    else:
        separator = config.separator

    parts = selected_words

    if config.numbers:
        parts.append(str(secrets.randbelow(100)))

    if config.special:
        parts.append(secrets.choice(string.punctuation))

    secrets.SystemRandom().shuffle(parts)

    return separator.join(parts)


def generate_manager_password(config: PasswordConfig) -> str:
    config.validate()

    character_sets = []

    if config.lowercase:
        character_sets.append(string.ascii_lowercase)

    if config.uppercase:
        character_sets.append(string.ascii_uppercase)

    if config.numbers:
        character_sets.append(string.digits)

    if config.special:
        character_sets.append(string.punctuation)

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
    config.validate()

    if config.mode == PasswordMode.HUMAN:
        return generate_human_password(config)

    return generate_manager_password(config)
