"""Tests and grep gates for controller / logical QUA config split."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from calibration_utils.qua_config_split import (
    CONTROLLER_KEYS,
    LOGICAL_KEYS,
    merge_qua_config,
    split_qua_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
QCA_ROOT = REPO_ROOT / "Quantum-Control-Applications" / "Superconducting"
CALIBRATIONS_DIR = Path(__file__).resolve().parent.parent / "calibrations"

MINIMAL_FULL_CONFIG = {
    "controllers": {"con1": {"type": "opx1000", "fems": {}}},
    "mixers": {"mixer1": {"correction": []}},
    "elements": {"q1": {"operations": {}}},
    "pulses": {"const": {"operation": "control"}},
    "waveforms": {"wf": {"type": "constant", "sample": 0.1}},
    "digital_waveforms": {"ON": {"samples": [(1, 0)]}},
    "integration_weights": {"cos": {"cosine": [(1.0, 0)]}},
}


def discover_configuration_files() -> list[Path]:
    patterns = [
        QCA_ROOT.rglob("configuration*.py"),
        (REPO_ROOT / "Tutorials" / "intro-to-QUAlibrate" / "configuration").rglob("configuration*.py"),
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(pattern))
    return files


def discover_qca_scripts() -> list[Path]:
    files: list[Path] = []
    for path in sorted(QCA_ROOT.rglob("*.py")):
        if path.name.startswith("configuration"):
            continue
        if path.name == "qua_config_split.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "open_qm" in text or "qmm.simulate" in text:
            files.append(path)
    return files


def discover_calibration_execute_files() -> list[Path]:
    files: list[Path] = []
    if not CALIBRATIONS_DIR.is_dir():
        return files
    for path in sorted(CALIBRATIONS_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "execute_qua_program" in text and "qm.execute" in text:
            files.append(path)
    return files


def test_split_merge_round_trip() -> None:
    controller, logical = split_qua_config(MINIMAL_FULL_CONFIG)
    merged = merge_qua_config(controller, logical)
    assert merged == MINIMAL_FULL_CONFIG
    assert set(controller.keys()).issubset(CONTROLLER_KEYS)
    assert set(logical.keys()).issubset(LOGICAL_KEYS)
    assert not set(controller.keys()) & set(logical.keys())


def test_split_merge_no_key_overlap() -> None:
    controller, logical = split_qua_config(MINIMAL_FULL_CONFIG)
    assert not set(controller) & set(logical)


def _top_level_assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


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
    assert "merge_qua_config" in source, f"{config_file} missing merge_qua_config usage"


def test_no_open_qm_with_merged_config_in_qca() -> None:
    violations: list[str] = []
    for path in discover_qca_scripts():
        text = path.read_text(encoding="utf-8")
        if re.search(r"open_qm\s*\(\s*config\s*\)", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"open_qm(config) still used in: {violations}"


def test_qca_execute_passes_logical_config() -> None:
    violations: list[str] = []
    for path in discover_qca_scripts():
        text = path.read_text(encoding="utf-8")
        if "qm.execute" not in text:
            continue
        for match in re.finditer(r"qm\.execute\s*\(([^)]*)\)", text):
            args = match.group(1)
            if "config=" not in args and "**" not in args:
                violations.append(f"{path.relative_to(REPO_ROOT)}: qm.execute({args[:80]})")
    assert not violations, f"qm.execute without config= in: {violations}"


def test_calibration_nodes_use_controller_config_in_qm_session() -> None:
    violations: list[str] = []
    for path in discover_calibration_execute_files():
        text = path.read_text(encoding="utf-8")
        if re.search(r'qm_session\s*\(\s*qmm,\s*config\b', text):
            violations.append(str(path.relative_to(REPO_ROOT)))
        if re.search(r'qm_session\s*\(\s*qmm,\s*node\.namespace\["config"\]', text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"qm_session still uses merged config in: {violations}"


def test_calibration_nodes_execute_with_logical_config() -> None:
    violations: list[str] = []
    for path in discover_calibration_execute_files():
        text = path.read_text(encoding="utf-8")
        if "config=logical_config" not in text and "qm.execute" in text:
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"calibration execute missing logical_config in: {violations}"


def test_simulate_uses_manager_not_open_qm() -> None:
    """Simulation branches must not open a QM before simulate."""
    violations: list[str] = []
    for path in discover_qca_scripts():
        text = path.read_text(encoding="utf-8")
        if "qmm.simulate" not in text:
            continue
        if re.search(r"open_qm\s*\([^)]*\)[\s\S]{0,200}qmm\.simulate", text):
            violations.append(str(path.relative_to(REPO_ROOT)))
    assert not violations, f"open_qm before qmm.simulate in: {violations}"


def test_hello_qua_configuration_import_and_merge() -> None:
    """Smoke: reference configuration exports valid split configs that round-trip."""
    pytest.importorskip("qm")
    import sys

    hello_dir = QCA_ROOT / "Single-Fixed-Transmon"
    sys.path.insert(0, str(hello_dir))
    try:
        from configuration import config, controller_config, logical_config  # noqa: PLC0415
    finally:
        sys.path.pop(0)

    merged = merge_qua_config(controller_config, logical_config)
    assert merged == config
    assert set(controller_config.keys()).issubset(CONTROLLER_KEYS)
    assert set(logical_config.keys()).issubset(LOGICAL_KEYS)


def test_simulate_hello_qua_with_merged_split_config() -> None:
    """Compile/simulate smoke when a QOP is reachable (skipped in offline CI)."""
    pytest.importorskip("qm")
    import sys

    from qm import QuantumMachinesManager, SimulationConfig
    from qm.qua import amp, declare, fixed, for_, infinite_loop_, play, program, wait
    from qm.exceptions import QmServerDetectionError

    hello_dir = QCA_ROOT / "Single-Fixed-Transmon"
    sys.path.insert(0, str(hello_dir))
    try:
        from configuration import config  # noqa: PLC0415
    finally:
        sys.path.pop(0)

    with program() as hello_qua:
        a = declare(fixed)
        with infinite_loop_():
            with for_(a, 0, a < 1.1, a + 0.05):
                play("pi", "qubit", amplitude_scale=a)
            wait(25, "qubit")

    try:
        qmm = QuantumMachinesManager(host="127.0.0.1")
        job = qmm.simulate(config, hello_qua, SimulationConfig(duration=1_000))
    except QmServerDetectionError as exc:
        pytest.skip(f"No QOP available for simulate smoke: {exc}")

    job.wait_until("Done")
    assert job.get_simulated_samples() is not None
