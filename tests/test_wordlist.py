from pathlib import Path

from app.wordlist import load_wordlist, load_words


def test_builtin_wordlist_contains_enough_words():
    words = load_words()

    assert len(words) >= 300


def test_builtin_wordlist_contains_no_empty_words():
    words = load_words()

    assert all(word.strip() for word in words)


def test_builtin_wordlist_contains_words_longer_than_four_characters():
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
