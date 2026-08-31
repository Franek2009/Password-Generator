"""Build-time and runtime application version handling."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

from app.resources import resource_path


RELEASE_TAG_PATTERN = re.compile(
    r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
)


def version_from_tag(tag: str) -> str:
    match = RELEASE_TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(
            f"Invalid release tag {tag!r}; expected vMAJOR.MINOR.PATCH."
        )
    return ".".join(match.groups())


def development_version(commit_sha: str | None) -> str:
    if not commit_sha:
        return "development"

    normalized_sha = commit_sha.strip().lower()
    if (
        len(normalized_sha) < 7
        or re.fullmatch(r"[0-9a-f]+", normalized_sha) is None
    ):
        raise ValueError(f"Invalid commit SHA {commit_sha!r}.")
    return f"development-{normalized_sha[:12]}"


def version_for_build(release_tag: str | None, commit_sha: str | None) -> str:
    if release_tag:
        return version_from_tag(release_tag)
    return development_version(commit_sha)


def get_application_version(version_path: Path | None = None) -> str:
    path = version_path or resource_path("app", "VERSION")
    version = path.read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError(f"Application version file is empty: {path}")
    return version


def write_application_version(
    output: Path,
    release_tag: str | None,
    commit_sha: str | None,
) -> str:
    version = version_for_build(release_tag, commit_sha)
    output.write_text(f"{version}\n", encoding="utf-8")
    return version


def validate_release_version(tag: str, detected: str, artifact: str) -> str:
    expected = version_from_tag(tag)
    if detected != expected:
        raise ValueError(
            f"Version mismatch for {artifact}: tag={tag}, "
            f"expected={expected}, detected={detected}"
        )
    return expected


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--output", type=Path, required=True)

    tag_parser = subparsers.add_parser("from-tag")
    tag_parser.add_argument("tag")

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("tag")
    check_parser.add_argument("detected")
    check_parser.add_argument("--artifact", required=True)

    args = parser.parse_args()
    try:
        if args.command == "write":
            version = write_application_version(
                args.output,
                os.environ.get("PASSWORD_GENERATOR_RELEASE_TAG"),
                os.environ.get("GITHUB_SHA"),
            )
        elif args.command == "from-tag":
            version = version_from_tag(args.tag)
        else:
            version = validate_release_version(
                args.tag,
                args.detected,
                args.artifact,
            )
    except ValueError as error:
        parser.error(str(error))
    print(version)


if __name__ == "__main__":
    main()
