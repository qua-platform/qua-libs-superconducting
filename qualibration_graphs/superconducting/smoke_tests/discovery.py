"""Finds calibration node files to smoke test -- no manual list to maintain.

A file is a node (not a graph) if it defines `create_qua_program` and does
not construct a `QualibrationGraph`. This is a plain text scan, not an
import: discovery must stay side-effect-free, since importing *is* running
for these files (see harness.py).
"""

from __future__ import annotations

from pathlib import Path

NODE_SUBDIRS = ("1Q_calibrations", "CZ_calibrations")


def discover_node_files(calibrations_dir: Path) -> list[Path]:
    found: list[Path] = []
    for subdir in NODE_SUBDIRS:
        directory = calibrations_dir / subdir
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            text = path.read_text()
            if "QualibrationGraph(" in text:
                continue
            if "def create_qua_program" not in text:
                continue
            found.append(path)
    return found
