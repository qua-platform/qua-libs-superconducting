"""Overnight smoke test.

For every discovered calibration node, with default parameters:
  1. import            -- the node file loads
  2. load parameters   -- defaults validate (pydantic, at QualibrationNode construction)
  3. load a machine    -- the shared fake QUAM loads (at QualibrationNode construction)
  4. build the program -- create_qua_program runs for real
  5. generate config   -- machine.generate_config() runs for real

Nothing here opens a QuantumMachinesManager, runs a simulator, or touches
real/simulated hardware -- see harness.py and conftest.py for how that's
enforced, not just assumed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from discovery import discover_node_files
from harness import run_node_up_to_program

CALIBRATIONS_DIR = Path(__file__).resolve().parents[1] / "calibrations"
KNOWN_BROKEN_FILE = Path(__file__).resolve().parent / "known_broken.txt"

PER_NODE_TIMEOUT_SECONDS = 120


def _relative_id(path: Path) -> str:
    return str(path.relative_to(CALIBRATIONS_DIR))


def _load_known_broken() -> dict[str, str]:
    broken: dict[str, str] = {}
    if not KNOWN_BROKEN_FILE.exists():
        return broken
    for line in KNOWN_BROKEN_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        path_part, _, reason = line.partition("#")
        broken[path_part.strip()] = reason.strip() or "known-broken on the smoke-test fake QUAM"
    return broken


def _build_params() -> list[pytest.param]:
    known_broken = _load_known_broken()
    params = []
    for node_file in discover_node_files(CALIBRATIONS_DIR):
        rel = _relative_id(node_file)
        marks = [pytest.mark.timeout(PER_NODE_TIMEOUT_SECONDS)]
        reason = known_broken.get(rel)
        if reason is not None:
            # strict=True: if this starts passing, that's news -- the job
            # should go red so someone removes the stale known_broken.txt entry.
            marks.append(pytest.mark.xfail(reason=reason, strict=True))
        params.append(pytest.param(node_file, id=rel, marks=marks))
    return params


_PARAMS = _build_params()


@pytest.mark.parametrize("node_file", _PARAMS)
def test_node_builds_program_and_config(node_file: Path) -> None:
    node = run_node_up_to_program(node_file)
    config = node.machine.generate_config()
    assert config, f"{node_file.name}: generate_config() returned an empty config"


def test_discovery_found_the_expected_nodes() -> None:
    """Guard against a silent discovery break (e.g. a directory rename)."""
    found = len(_PARAMS)
    assert found >= 50, (
        f"only found {found} calibration node files under {CALIBRATIONS_DIR} -- "
        "discovery may be broken (check discovery.py against the current directory layout)"
    )
