"""Grep gate: deprecated QUA `pulse * amp(...)` must not appear in active Python code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAN_ROOTS = (
    REPO_ROOT / "Quantum-Control-Applications",
    REPO_ROOT / "qualibration_graphs",
    REPO_ROOT / "Tutorials",
)
EXCLUDE_PATH_PARTS = (
    "scripts/migrate_amp",
    "docs/plans",
    "/.venv/",
    "/__pycache__/",
    "/site-packages/",
)
DEPRECATED_AMP_PATTERN = re.compile(r"\*\s*amp\s*\(")


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in rel for part in EXCLUDE_PATH_PARTS):
                continue
            if path.name == "test_no_deprecated_amp.py":
                continue
            if "migrate_amp" in path.name:
                continue
            files.append(path)
    return files


def _active_lines(text: str) -> list[tuple[int, str]]:
    active: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0]
        active.append((line_no, line))
    return active


def find_deprecated_amp_usages(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    hits: list[str] = []
    for line_no, line in _active_lines(text):
        if DEPRECATED_AMP_PATTERN.search(line):
            hits.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    return hits


@pytest.mark.parametrize(
    "py_file",
    _iter_python_files(),
    ids=lambda path: str(path.relative_to(REPO_ROOT)),
)
def test_no_deprecated_amp_in_python(py_file: Path) -> None:
    violations = find_deprecated_amp_usages(py_file)
    assert not violations, "Deprecated `* amp(` usage found:\n" + "\n".join(violations)
