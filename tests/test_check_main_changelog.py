"""Tests for check_main_changelog.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check_main_changelog import check_changelog  # noqa: E402

OLD_CHANGELOG = """## [Unreleased]

## [2026-09-01]

### Added

- Previous work.
"""

NEW_CHANGELOG = """## [Unreleased]

## [2026-09-25]

### Added

- New work.

## [2026-09-01]

### Added

- Previous work.
"""


def test_accepts_new_dated_section() -> None:
    check_changelog(old_changelog=OLD_CHANGELOG, new_changelog=NEW_CHANGELOG)


def test_accepts_changelog_when_main_had_none() -> None:
    check_changelog(old_changelog="", new_changelog=NEW_CHANGELOG)


def test_rejects_unchanged_changelog() -> None:
    with pytest.raises(SystemExit, match="CHANGELOG.md must change"):
        check_changelog(old_changelog=OLD_CHANGELOG, new_changelog=OLD_CHANGELOG)


def test_rejects_unreleased_only_edit() -> None:
    edited = """## [Unreleased]

### Added

- Note that never left Unreleased.

## [2026-09-01]

### Added

- Previous work.
"""
    with pytest.raises(SystemExit, match=r"must add a ## \[YYYY-MM-DD\]"):
        check_changelog(old_changelog=OLD_CHANGELOG, new_changelog=edited)


def test_rejects_empty_new_dated_section() -> None:
    empty_section = """## [Unreleased]

## [2026-09-25]

## [2026-09-01]

### Added

- Previous work.
"""
    with pytest.raises(SystemExit, match=r"section \[2026-09-25\] is empty"):
        check_changelog(old_changelog=OLD_CHANGELOG, new_changelog=empty_section)
