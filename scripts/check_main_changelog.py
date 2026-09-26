#!/usr/bin/env python3
"""Require a new dated CHANGELOG.md section when updating main.

Compares the current tree to a base git revision (PR base or previous main
tip). Intended for pull requests into ``main`` and pushes to ``main``, not for
ordinary ``develop`` work.

This repo is not a versioned package. Dated ``## [YYYY-MM-DD]`` headings stand
in for a release version.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = "CHANGELOG.md"
ZERO_SHA = re.compile(r"^0+$")
DATE_HEADING_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]", re.MULTILINE)
SECTION_RE = re.compile(
    r"^## \[(?P<heading>[^\]]+)\](?:[^\n]*)\n(?P<body>.*?)(?=^## \[|\Z)",
    re.MULTILINE | re.DOTALL,
)


def git_show(revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def dated_headings(changelog: str) -> list[str]:
    return DATE_HEADING_RE.findall(changelog)


def section_body(changelog: str, heading: str) -> str:
    for match in SECTION_RE.finditer(changelog):
        if match.group("heading") == heading:
            return match.group("body").strip()
    return ""


def check_changelog(*, old_changelog: str, new_changelog: str) -> None:
    if old_changelog == new_changelog:
        raise SystemExit("CHANGELOG.md must change when merging to main.")
    old_dates = set(dated_headings(old_changelog))
    new_dates = dated_headings(new_changelog)
    added = [date for date in new_dates if date not in old_dates]
    if not added:
        raise SystemExit("CHANGELOG.md must add a ## [YYYY-MM-DD] section when merging to main.")
    newest = added[0]
    if not section_body(new_changelog, newest):
        raise SystemExit(f"CHANGELOG.md section [{newest}] is empty")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-sha",
        required=True,
        help="Git revision of current main (PR base SHA, or github.event.before on push).",
    )
    args = parser.parse_args()
    base_sha = args.base_sha.strip()
    if not base_sha or ZERO_SHA.fullmatch(base_sha):
        raise SystemExit(f"Invalid base SHA {base_sha!r}; cannot compare against main.")

    old_changelog = git_show(base_sha, CHANGELOG_PATH)
    new_path = REPO_ROOT / CHANGELOG_PATH
    if not new_path.is_file():
        raise SystemExit("CHANGELOG.md is missing.")
    new_changelog = new_path.read_text(encoding="utf-8")
    check_changelog(old_changelog=old_changelog, new_changelog=new_changelog)
    added = [d for d in dated_headings(new_changelog) if d not in set(dated_headings(old_changelog))]
    print(f"OK: CHANGELOG.md added section [{added[0]}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
