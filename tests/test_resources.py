import importlib
import sys
from pathlib import Path

from app.resources import resource_path


def test_resource_path_uses_project_root(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    path = resource_path("data", "words.txt")

    assert path == (
        Path(__file__).resolve().parent.parent
        / "data"
        / "words.txt"
    )


def test_resource_path_does_not_depend_on_working_directory(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)

    path = resource_path("data", "words.txt")

    assert path == (
        Path(__file__).resolve().parent.parent
        / "data"
        / "words.txt"
    )


def test_resource_path_uses_pyinstaller_bundle_directory(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    path = resource_path("data", "words.txt")

    assert path == tmp_path / "data" / "words.txt"


def test_load_words_uses_pyinstaller_bundled_wordlist(
    monkeypatch,
    tmp_path: Path,
):
    data_directory = tmp_path / "data"
    data_directory.mkdir()
    (data_directory / "words.txt").write_text(
        "zamek\nrower\nkomputer\n",
        encoding="utf-8",
    )

    original_wordlist = importlib.import_module("app.wordlist")
    app_package = sys.modules["app"]

    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                sys,
                "_MEIPASS",
                str(tmp_path),
                raising=False,
            )
            sys.modules.pop("app.wordlist")
            bundled_wordlist = importlib.import_module(
                "app.wordlist"
            )

            assert bundled_wordlist.load_words() == [
                "zamek",
                "rower",
                "komputer",
            ]
    finally:
        sys.modules["app.wordlist"] = original_wordlist
        app_package.wordlist = original_wordlist
