"""Compile and import checks for QUA 1.3.1 calibration programs."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

qm = pytest.importorskip("qm")

CALIBRATIONS_DIR = Path(__file__).resolve().parent.parent / "calibrations"


def discover_calibration_files() -> list[Path]:
    files: list[Path] = []
    if not CALIBRATIONS_DIR.is_dir():
        return files
    for path in sorted(CALIBRATIONS_DIR.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "create_qua_program" in text:
            files.append(path)
    return files


def test_qm_extensions_importable() -> None:
    from qm.qua import declare_output_stream, declare_with_stream
    from qm.qua.extensions import QuaIterable, QuaIterableRange

    assert QuaIterable is not None
    assert QuaIterableRange is not None
    assert declare_with_stream is not None
    assert declare_output_stream is not None


@pytest.mark.parametrize(
    "calibration_file",
    discover_calibration_files(),
    ids=lambda path: str(path.relative_to(CALIBRATIONS_DIR)),
)
def test_calibration_module_syntax(calibration_file: Path) -> None:
    source = calibration_file.read_text(encoding="utf-8")
    ast.parse(source, filename=str(calibration_file))


@pytest.mark.parametrize(
    "calibration_file",
    discover_calibration_files(),
    ids=lambda path: str(path.relative_to(CALIBRATIONS_DIR)),
)
def test_calibration_module_imports(calibration_file: Path) -> None:
    pytest.importorskip("qualibrate")
    pytest.importorskip("quam_config")
    spec = importlib.util.spec_from_file_location(calibration_file.stem, calibration_file)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        pytest.skip(f"Optional dependency missing for {calibration_file.name}: {exc}")


def test_no_deprecated_declare_stream_in_calibrations() -> None:
    """Calibration nodes must use declare_output_stream, not deprecated declare_stream."""
    violations: list[str] = []
    for path in discover_calibration_files():
        text = path.read_text(encoding="utf-8")
        if "declare_stream(" in text:
            violations.append(str(path.relative_to(CALIBRATIONS_DIR)))
    assert not violations, f"declare_stream() still used in: {violations}"
