from app.wordlist import load_words


def test_wordlist_is_loaded():
    words = load_words()

    assert len(words) == 3888
    assert all(isinstance(word, str) for word in words)
    assert all(word for word in words)
