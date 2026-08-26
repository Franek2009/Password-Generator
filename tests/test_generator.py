import string

import pytest

from app.config import PasswordConfig, PasswordMode
from app.generator import generate_password
from app.wordlist import load_words


def test_password_has_correct_length():
    config = PasswordConfig(length=32)

    password = generate_password(config)

    assert len(password) == 32


def test_password_contains_selected_character_sets():
    config = PasswordConfig(
        length=20,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    password = generate_password(config)

    assert any(char in string.ascii_uppercase for char in password)
    assert any(char in string.ascii_lowercase for char in password)
    assert any(char in string.digits for char in password)
    assert any(char in string.punctuation for char in password)


def test_password_uses_only_selected_characters():
    config = PasswordConfig(
        length=20,
        uppercase=False,
        lowercase=True,
        numbers=False,
        special=False,
    )

    password = generate_password(config)

    assert all(char in string.ascii_lowercase for char in password)


def test_password_rejects_too_short_length():
    config = PasswordConfig(
        length=3,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    with pytest.raises(ValueError):
        generate_password(config)


def test_password_rejects_empty_character_set():
    config = PasswordConfig(
        length=20,
        uppercase=False,
        lowercase=False,
        numbers=False,
        special=False,
    )

    with pytest.raises(ValueError):
        generate_password(config)


def test_human_password():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=True,
        special=True,
    )

    password = generate_password(config)

    parts = password.split(config.separator)

    assert len(parts) == config.words

    word_list = load_words()

    for word in parts:
        word_without_suffix = word.rstrip(
            string.digits + string.punctuation
        )

        assert word_without_suffix.lower() in word_list
        assert word_without_suffix[0].isupper()
