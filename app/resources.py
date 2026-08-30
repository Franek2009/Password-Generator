import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """Return the path to a bundled application resource."""
    base_path = Path(
        getattr(
            sys,
            "_MEIPASS",
            Path(__file__).resolve().parent.parent,
        )
    )

    return base_path.joinpath(*parts)
