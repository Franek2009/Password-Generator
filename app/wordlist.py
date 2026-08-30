from pathlib import Path

from app.resources import resource_path


WORDS_FILE = resource_path("data", "words.txt")


class WordlistError(Exception):
    """Raised when a word list cannot be loaded or is invalid."""


def _read_words(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8") as file:
            words = [
                line.strip()
                for line in file
                if line.strip()
            ]
    except FileNotFoundError as error:
        raise WordlistError(
            f"Word list not found: {path}"
        ) from error
    except OSError as error:
        raise WordlistError(
            f"Could not read word list: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise WordlistError(
            "Word list must be a UTF-8 text file."
        ) from error

    if not words:
        raise WordlistError("Word list cannot be empty.")

    return words


def load_words() -> list[str]:
    return _read_words(WORDS_FILE)


def load_wordlist(path: str | Path) -> list[str]:
    return _read_words(Path(path))
