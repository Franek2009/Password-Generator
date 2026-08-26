from pathlib import Path


WORDS_FILE = Path(__file__).parent.parent / "data" / "words.txt"


def load_words() -> list[str]:
    return load_wordlist(WORDS_FILE)


def load_wordlist(path: str | Path) -> list[str]:
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip()
        ]
