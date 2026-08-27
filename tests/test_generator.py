import string

import pytest

from app.config import PasswordConfig, PasswordMode
from app.generator import (
    RANDOM_SEPARATORS,
    generate_human_password,
    generate_manager_password,
    generate_password,
)
from app.wordlist import WordlistError


def test_manager_password_has_correct_length():
    config = PasswordConfig(length=32)

    password = generate_manager_password(config)

    assert len(password) == 32


def test_manager_password_contains_selected_character_sets():
    config = PasswordConfig(
        length=32,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    password = generate_manager_password(config)

    assert any(char in string.ascii_uppercase for char in password)
    assert any(char in string.ascii_lowercase for char in password)
    assert any(char in string.digits for char in password)
    assert any(char in string.punctuation for char in password)


def test_manager_password_lowercase_only():
    config = PasswordConfig(
        length=20,
        uppercase=False,
        lowercase=True,
        numbers=False,
        special=False,
    )

    password = generate_manager_password(config)

    assert len(password) == 20
    assert all(char in string.ascii_lowercase for char in password)


def test_manager_password_uppercase_only():
    config = PasswordConfig(
        length=20,
        uppercase=True,
        lowercase=False,
        numbers=False,
        special=False,
    )

    password = generate_manager_password(config)

    assert len(password) == 20
    assert all(char in string.ascii_uppercase for char in password)


def test_manager_password_numbers_only():
    config = PasswordConfig(
        length=20,
        uppercase=False,
        lowercase=False,
        numbers=True,
        special=False,
    )

    password = generate_manager_password(config)

    assert len(password) == 20
    assert all(char in string.digits for char in password)


def test_manager_password_special_only():
    config = PasswordConfig(
        length=20,
        uppercase=False,
        lowercase=False,
        numbers=False,
        special=True,
    )

    password = generate_manager_password(config)

    assert len(password) == 20
    assert all(char in string.punctuation for char in password)


def test_manager_password_rejects_no_character_sets():
    config = PasswordConfig(
        uppercase=False,
        lowercase=False,
        numbers=False,
        special=False,
    )

    with pytest.raises(ValueError, match="At least one character set"):
        generate_manager_password(config)


def test_manager_password_rejects_too_short_length():
    config = PasswordConfig(
        length=3,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    with pytest.raises(
        ValueError,
        match="Password length is too short",
    ):
        generate_manager_password(config)


def test_manager_password_exact_minimum_length():
    config = PasswordConfig(
        length=4,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    password = generate_manager_password(config)

    assert len(password) == 4
    assert any(char in string.ascii_uppercase for char in password)
    assert any(char in string.ascii_lowercase for char in password)
    assert any(char in string.digits for char in password)
    assert any(char in string.punctuation for char in password)


def test_human_password_has_correct_number_of_words():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=5,
        numbers=False,
        special=False,
    )

    password = generate_human_password(config)

    assert len(password.split(config.separator)) == 5


def test_human_password_uses_selected_separator():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=4,
        separator="_",
        numbers=False,
        special=False,
    )

    password = generate_human_password(config)

    assert "_" in password
    assert "-" not in password


def test_human_password_random_separator_is_consistent():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=6,
        separator="Random",
        numbers=False,
        special=False,
    )

    password = generate_human_password(config)

    separators = [
        char
        for char in password
        if char in RANDOM_SEPARATORS
    ]

    assert separators
    assert len(set(separators)) == 1


def test_human_password_can_include_numbers():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=True,
        special=False,
    )

    password = generate_human_password(config)

    assert any(char in string.digits for char in password)


def test_human_password_can_include_special_characters():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=False,
        special=True,
    )

    password = generate_human_password(config)

    assert any(char in string.punctuation for char in password)


def test_generate_password_uses_manager_mode():
    config = PasswordConfig(
        mode=PasswordMode.MANAGER,
        length=20,
    )

    password = generate_password(config)

    assert len(password) == 20


def test_generate_password_uses_human_mode():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=False,
        special=False,
    )

    password = generate_password(config)

    assert len(password.split(config.separator)) == 3


def test_human_password_with_one_word():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=1,
        numbers=False,
        special=False,
    )

    password = generate_human_password(config)

    assert password
    assert config.separator not in password


def test_human_password_with_zero_words():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=0,
        numbers=False,
        special=False,
    )

    password = generate_human_password(config)

    assert password == ""


def test_human_password_with_custom_wordlist(tmp_path):
    wordlist = tmp_path / "words.txt"
    wordlist.write_text(
        "kot\npies\nzamek\n",
        encoding="utf-8",
    )

    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=False,
        special=False,
        wordlist_path=str(wordlist),
    )

    password = generate_human_password(config)

    words = password.split(config.separator)

    assert len(words) == 3
    assert all(
        word.lower() in {"kot", "pies", "zamek"}
        for word in words
    )


def test_human_password_with_single_word_wordlist(tmp_path):
    wordlist = tmp_path / "words.txt"
    wordlist.write_text("kot\n", encoding="utf-8")

    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        numbers=False,
        special=False,
        wordlist_path=str(wordlist),
    )

    password = generate_human_password(config)

    assert password == "Kot-Kot-Kot"


def test_human_password_with_empty_custom_wordlist(tmp_path):
    wordlist = tmp_path / "empty.txt"
    wordlist.write_text("", encoding="utf-8")

    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        wordlist_path=str(wordlist),
    )

    with pytest.raises(
        WordlistError,
        match="Word list cannot be empty",
    ):
        generate_human_password(config)


def test_human_password_with_missing_custom_wordlist(tmp_path):
    wordlist = tmp_path / "missing.txt"

    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        wordlist_path=str(wordlist),
    )

    with pytest.raises(WordlistError, match="Word list not found"):
        generate_human_password(config)


def test_manager_password_with_length_one():
    config = PasswordConfig(
        length=1,
        uppercase=False,
        lowercase=True,
        numbers=False,
        special=False,
    )

    password = generate_manager_password(config)

    assert len(password) == 1
    assert password in string.ascii_lowercase


def test_manager_password_with_zero_length():
    config = PasswordConfig(
        length=0,
        uppercase=False,
        lowercase=True,
        numbers=False,
        special=False,
    )

    with pytest.raises(
        ValueError,
        match="Password length is too short",
    ):
        generate_manager_password(config)


def test_manager_password_with_length_one_and_multiple_sets():
    config = PasswordConfig(
        length=1,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    with pytest.raises(
        ValueError,
        match="Password length is too short",
    ):
        generate_manager_password(config)
