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

from dataclasses import dataclass
from pathlib import Path

import pytest
from discovery import discover_node_files
from harness import run_node_up_to_program

CALIBRATIONS_DIR = Path(__file__).resolve().parents[1] / "calibrations"
KNOWN_BROKEN_FILE = Path(__file__).resolve().parent / "known_broken.txt"

PER_NODE_TIMEOUT_SECONDS = 120


def _relative_id(path: Path) -> str:
    return str(path.relative_to(CALIBRATIONS_DIR))


@dataclass(frozen=True)
class KnownBroken:
    """A node that is expected to fail, and the error it is expected to fail with."""

    expected_error: str
    reason: str


def _load_known_broken() -> dict[str, KnownBroken]:
    """Parse `path | expected error  # reason` lines from known_broken.txt."""
    broken: dict[str, KnownBroken] = {}
    if not KNOWN_BROKEN_FILE.exists():
        return broken
    for line in KNOWN_BROKEN_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entry, _, reason = line.partition("#")
        path_part, bar, expected_error = entry.partition("|")
        path_part, expected_error = path_part.strip(), expected_error.strip()
        if not bar or not expected_error:
            raise ValueError(
                f"known_broken.txt entry {path_part!r} has no expected error text. "
                "Use `path | expected error  # reason`, so a different failure is not hidden."
            )
        broken[path_part] = KnownBroken(expected_error, reason.strip() or "known-broken")
    return broken


def _build_params() -> list[pytest.param]:
    known_broken = _load_known_broken()
    params = []
    for node_file in discover_node_files(CALIBRATIONS_DIR):
        rel = _relative_id(node_file)
        params.append(
            pytest.param(
                node_file,
                known_broken.get(rel),
                id=rel,
                marks=[pytest.mark.timeout(PER_NODE_TIMEOUT_SECONDS)],
            )
        )
    return params


_PARAMS = _build_params()


def _build_program_and_config(node_file: Path) -> None:
    node = run_node_up_to_program(node_file)
    config = node.machine.generate_config()
    assert config, f"{node_file.name}: generate_config() returned an empty config"


@pytest.mark.parametrize("node_file, known_broken", _PARAMS)
def test_node_builds_program_and_config(node_file: Path, known_broken: KnownBroken | None) -> None:
    if known_broken is None:
        _build_program_and_config(node_file)
        return

    # A known-broken node must fail with its recorded error. Any other failure
    # (an import error, an upstream API change, a different guard) goes red
    # instead of being absorbed as "expected".
    try:
        _build_program_and_config(node_file)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        if known_broken.expected_error not in failure:
            raise AssertionError(
                f"{node_file.name} is listed in known_broken.txt, but it failed with a different error.\n"
                f"  expected text: {known_broken.expected_error}\n"
                f"  actual error:  {failure}"
            ) from exc
    else:
        pytest.fail(
            f"{node_file.name} is listed in known_broken.txt but now builds its program and config. "
            "Remove its entry."
        )
    pytest.xfail(known_broken.reason)


def test_discovery_found_the_expected_nodes() -> None:
    """Guard against a silent discovery break (e.g. a directory rename)."""
    found = len(_PARAMS)
    assert found >= 50, (
        f"only found {found} calibration node files under {CALIBRATIONS_DIR} -- "
        "discovery may be broken (check discovery.py against the current directory layout)"
    )


def test_known_broken_entries_exist() -> None:
    """Every known_broken.txt path must still be a discovered node.

    `_build_params` only looks up discovered nodes in the list. A renamed,
    deleted, or mistyped entry matches nothing, and the real node then runs
    without its xfail.
    """
    discovered = {_relative_id(p) for p in discover_node_files(CALIBRATIONS_DIR)}
    stale = set(_load_known_broken()) - discovered
    assert not stale, f"known_broken.txt has entries that match no node: {sorted(stale)}"
