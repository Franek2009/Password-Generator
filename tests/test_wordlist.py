from pathlib import Path

import pytest

from app.wordlist import WordlistError, load_wordlist, load_words


def test_builtin_wordlist_contains_enough_words():
    words = load_words()

    assert len(words) >= 300


def test_builtin_wordlist_contains_no_empty_words():
    words = load_words()

    assert all(word.strip() for word in words)


def test_builtin_wordlist_contains_words_with_at_least_four_characters():
    words = load_words()

    assert all(len(word) >= 4 for word in words)


def test_custom_wordlist(tmp_path: Path):
    wordlist = tmp_path / "words.txt"

    wordlist.write_text(
        "kot\n"
        "zamek\n"
        "rower\n"
        "komputer\n",
        encoding="utf-8",
    )

    words = load_wordlist(wordlist)

    assert words == [
        "kot",
        "zamek",
        "rower",
        "komputer",
    ]


def test_custom_wordlist_ignores_empty_lines(tmp_path: Path):
    wordlist = tmp_path / "words.txt"

    wordlist.write_text(
        "kot\n"
        "\n"
        "zamek\n"
        "\n"
        "rower\n",
        encoding="utf-8",
    )

    words = load_wordlist(wordlist)

    assert words == [
        "kot",
        "zamek",
        "rower",
    ]


def test_missing_wordlist_raises_error(tmp_path: Path):
    wordlist = tmp_path / "missing.txt"

    with pytest.raises(WordlistError):
        load_wordlist(wordlist)


def test_empty_wordlist_raises_error(tmp_path: Path):
    wordlist = tmp_path / "empty.txt"
    wordlist.write_text("", encoding="utf-8")

    with pytest.raises(WordlistError):
        load_wordlist(wordlist)


def test_invalid_encoding_raises_error(tmp_path: Path):
    wordlist = tmp_path / "invalid.txt"
    wordlist.write_bytes(b"\xff\xfe\xfd")

    with pytest.raises(WordlistError):
        load_wordlist(wordlist)
