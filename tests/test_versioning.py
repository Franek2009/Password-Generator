from pathlib import Path

import pytest

from app.versioning import (
    development_version,
    get_application_version,
    validate_release_version,
    version_for_build,
    version_from_tag,
    write_application_version,
)


def test_version_from_tag_removes_v_prefix():
    assert version_from_tag("v1.0.2") == "1.0.2"


@pytest.mark.parametrize(
    "tag",
    (
        "1.0.2",
        "v1.0",
        "v1.0.2.3",
        "v1.0.x",
        "v01.0.2",
        "v1.0.2-rc1",
    ),
)
def test_version_from_tag_rejects_invalid_tags(tag):
    with pytest.raises(ValueError, match="expected vMAJOR.MINOR.PATCH"):
        version_from_tag(tag)


def test_development_version_uses_short_commit_sha():
    assert (
        development_version("ABCDEF0123456789ABCDEF0123456789ABCDEF01")
        == "development-abcdef012345"
    )


def test_development_version_without_sha_is_unversioned():
    assert development_version(None) == "development"


def test_version_for_build_prefers_release_tag():
    assert version_for_build("v1.0.2", "abcdef0123456789") == "1.0.2"


def test_write_and_read_application_version(tmp_path):
    version_path = tmp_path / "VERSION"

    written = write_application_version(
        version_path,
        "v1.0.2",
        None,
    )

    assert written == "1.0.2"
    assert get_application_version(version_path) == "1.0.2"


def test_committed_application_version_is_development():
    version_path = Path(__file__).parents[1] / "app" / "VERSION"

    assert get_application_version(version_path) == "development"


def test_validate_release_version_accepts_matching_version():
    assert validate_release_version("v1.0.2", "1.0.2", "Linux") == "1.0.2"


def test_validate_release_version_reports_mismatch():
    with pytest.raises(
        ValueError,
        match=(
            "Version mismatch for Windows: tag=v1.0.2, "
            "expected=1.0.2, detected=1.0.1"
        ),
    ):
        validate_release_version("v1.0.2", "1.0.1", "Windows")
