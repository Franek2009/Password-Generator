import pytest

from app.config import PasswordConfig, PasswordMode
from app.generator import generate_password


def test_manager_password_has_correct_length():
    config = PasswordConfig(
        mode=PasswordMode.MANAGER,
        length=32,
    )

    password = generate_password(config)

    assert len(password) == 32


def test_manager_password_contains_selected_character_sets():
    config = PasswordConfig(
        mode=PasswordMode.MANAGER,
        length=32,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    password = generate_password(config)

    assert any(char.isupper() for char in password)
    assert any(char.islower() for char in password)
    assert any(char.isdigit() for char in password)


def test_manager_password_raises_when_no_character_set_is_selected():
    config = PasswordConfig(
        mode=PasswordMode.MANAGER,
        length=20,
        uppercase=False,
        lowercase=False,
        numbers=False,
        special=False,
    )

    with pytest.raises(ValueError):
        generate_password(config)


def test_manager_password_raises_when_length_is_too_short():
    config = PasswordConfig(
        mode=PasswordMode.MANAGER,
        length=2,
        uppercase=True,
        lowercase=True,
        numbers=True,
        special=True,
    )

    with pytest.raises(ValueError):
        generate_password(config)


def test_human_password_contains_correct_number_of_words():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=4,
        separator="-",
        numbers=False,
        special=False,
    )

    password = generate_password(config)

    words = password.split("-")

    assert len(words) == 4


def test_human_password_uses_selected_separator():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=4,
        separator="_",
        numbers=False,
        special=False,
    )

    password = generate_password(config)

    assert "_" in password
    assert "-" not in password


def test_human_password_can_add_numbers_and_special_characters():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=3,
        separator="-",
        numbers=True,
        special=True,
    )

    password = generate_password(config)

    assert any(char.isdigit() for char in password)


def test_human_password_with_random_separator():
    config = PasswordConfig(
        mode=PasswordMode.HUMAN,
        words=4,
        separator="Random",
        numbers=False,
        special=False,
    )

    password = generate_password(config)

    allowed_separators = {"-", "_", ".", " ", "/", "|"}

    separators = [
        char
        for char in password
        if char in allowed_separators
    ]

    assert len(separators) == 3
    assert len(set(separators)) == 1
