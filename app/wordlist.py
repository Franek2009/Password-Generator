from pathlib import Path


WORDS_FILE = Path(__file__).parent.parent / "data" / "words.txt"


def load_words() -> list[str]:
    with WORDS_FILE.open("r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip()
        ]
