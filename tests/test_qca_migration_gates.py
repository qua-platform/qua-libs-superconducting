"""Portable grep gates for QUA 1.3.1 / 1.4.0 migration under Quantum-Control-Applications."""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODALITY = "Superconducting"
MODALITY = os.environ.get("QCA_MODALITY", DEFAULT_MODALITY)
QCA_ROOT = REPO_ROOT / "Quantum-Control-Applications" / MODALITY

CONTROLLER_KEYS = frozenset({"controllers", "octaves", "mixers"})
LOGICAL_KEYS = frozenset(
    {"oscillators", "elements", "integration_weights", "waveforms", "digital_waveforms", "pulses"}
)
DEPRECATED_AMP_PATTERN = re.compile(r"\*\s*amp\s*\(")


def _skip_if_no_qca_root() -> None:
    if not QCA_ROOT.is_dir():
        pytest.skip(f"QCA root not found: {QCA_ROOT} (set QCA_MODALITY)")


def discover_configuration_files() -> list[Path]:
    _skip_if_no_qca_root()
    return sorted(QCA_ROOT.rglob("configuration*.py"))


def discover_qca_python_files() -> list[Path]:
    _skip_if_no_qca_root()
    files: list[Path] = []
    for path in sorted(QCA_ROOT.rglob("*.py")):
        if path.name == "qua_config_split.py":
            continue
        files.append(path)
    return files


def discover_qca_scripts_with_execute_or_simulate() -> list[Path]:
    files: list[Path] = []
    for path in discover_qca_python_files():
        if path.name.startswith("configuration"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "open_qm" in text or "qmm.simulate" in text:
            files.append(path)
    return files


def _top_level_assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


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


@pytest.mark.parametrize(
    "config_file",
    discover_configuration_files(),
    ids=lambda path: str(path.relative_to(REPO_ROOT)),
)
def test_configuration_file_defines_split_exports(config_file: Path) -> None:
    source = config_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(config_file))
    top_level_names = _top_level_assigned_names(tree)
    assert "controller_config" in top_level_names, f"{config_file} missing controller_config"
    assert "logical_config" in top_level_names, f"{config_file} missing logical_config"
    assert "config" in top_level_names, f"{config_file} missing transitional config alias"
    assert "merge_qua_config" in source or "split_qua_config" in source


def test_no_declare_stream_in_qca() -> None:
    violations: list[str] = []
    for path in discover_qca_python_files():
        text = path.read_text(encoding="utf-8")
        if "declare_stream(" in text:
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"declare_stream() still used in: {violations}"


def test_no_open_qm_with_merged_config() -> None:
    violations: list[str] = []
    for path in discover_qca_scripts_with_execute_or_simulate():
        text = path.read_text(encoding="utf-8")
        if re.search(r"open_qm\s*\(\s*config\s*\)", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"open_qm(config) still used in: {violations}"


def test_qca_execute_passes_logical_config() -> None:
    violations: list[str] = []
    for path in discover_qca_scripts_with_execute_or_simulate():
        text = path.read_text(encoding="utf-8")
        if "qm.execute" not in text:
            continue
        for match in re.finditer(r"qm\.execute\s*\(([^)]*)\)", text):
            args = match.group(1)
            if "config=" not in args and "**" not in args:
                violations.append(f"{path.relative_to(REPO_ROOT)}: qm.execute({args[:80]})")
    assert not violations, f"qm.execute without config= in: {violations}"


def test_no_deprecated_amp_in_qca() -> None:
    violations: list[str] = []
    for path in discover_qca_python_files():
        if "migrate_amp" in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line_no, line in _active_lines(text):
            if DEPRECATED_AMP_PATTERN.search(line):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")
    assert not violations, "Deprecated `* amp(` usage found:\n" + "\n".join(violations)


def test_simulate_uses_manager_not_open_qm() -> None:
    violations: list[str] = []
    for path in discover_qca_scripts_with_execute_or_simulate():
        text = path.read_text(encoding="utf-8")
        if "qmm.simulate" not in text:
            continue
        if re.search(r"open_qm\s*\([^)]*\)[\s\S]{0,200}qmm\.simulate", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"open_qm before qmm.simulate in: {violations}"


def test_qua_config_split_at_modality_root() -> None:
    _skip_if_no_qca_root()
    helper = QCA_ROOT / "qua_config_split.py"
    assert helper.is_file(), f"Missing {helper} — copy from a migrated modality repo"


def test_split_merge_round_trip() -> None:
    import sys

    _skip_if_no_qca_root()
    sys.path.insert(0, str(QCA_ROOT))
    try:
        from qua_config_split import merge_qua_config, split_qua_config  # noqa: PLC0415
    finally:
        sys.path.pop(0)

    sample = {
        "controllers": {"con1": {"type": "opx1000", "fems": {}}},
        "elements": {"q1": {"operations": {}}},
        "pulses": {"const": {"operation": "control"}},
        "waveforms": {"wf": {"type": "constant", "sample": 0.1}},
        "digital_waveforms": {"ON": {"samples": [(1, 0)]}},
        "integration_weights": {"cos": {"cosine": [(1.0, 0)]}},
    }
    controller, logical = split_qua_config(sample)
    merged = merge_qua_config(controller, logical)
    assert merged == sample
    assert set(controller.keys()).issubset(CONTROLLER_KEYS)
    assert set(logical.keys()).issubset(LOGICAL_KEYS)
