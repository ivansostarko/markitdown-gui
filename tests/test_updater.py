"""Tests for the update-check helpers (no network access needed)."""

import pytest

from markitdown_gui.updater import UpdateInfo, _version_tuple


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("1.0.0", (1, 0, 0)),
        ("v1.2.3", (1, 2, 3)),
        ("V2.10", (2, 10, 0)),
        ("1.2.3-beta", (1, 2, 3)),
        ("1.2.3rc1", (1, 2, 3)),
        ("", (0, 0, 0)),
        ("garbage", (0, 0, 0)),
    ],
)
def test_version_tuple(version, expected):
    assert _version_tuple(version) == expected


@pytest.mark.parametrize(
    ("current", "latest", "available"),
    [
        ("1.0.0", "v1.0.0", False),
        ("1.0.0", "v1.0.1", True),
        ("1.0.0", "v2.0.0", True),
        ("2.0.0", "v1.9.9", False),
        ("1.0.0", "v1.0.0-beta", False),
    ],
)
def test_update_available(current, latest, available):
    info = UpdateInfo(current=current, latest=latest, url="https://example.invalid")
    assert info.available is available
