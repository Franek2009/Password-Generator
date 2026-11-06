"""Release headless Qt test resources while Python bindings are still alive."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def release_offscreen_clipboard(qapp):
    yield
    # The offscreen backend keeps MIME data in a C++ global past Python shutdown.
    # Delete Python-created test MIME objects before Shiboken is finalized.
    # Never clear a native desktop clipboard as part of test-session cleanup.
    if qapp.platformName() == "offscreen":
        qapp.clipboard().clear()
