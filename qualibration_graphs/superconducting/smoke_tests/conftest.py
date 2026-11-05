"""Session setup for the overnight smoke tests.

Isolates this run from any machine-level `~/.qualibrate/config.toml` (quam
and qualibrate both fall back to that file/env vars when no path is given --
see `quam.config.resolvers.get_quam_config` and
`qualibrate_config.resolvers.get_qualibrate_config_path`), builds a small
fake QUAM state once per session, and makes `machine.connect()` raise for
every node instead of silently no-op-ing.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

SUPERCONDUCTING_ROOT = Path(__file__).resolve().parents[1]
CALIBRATIONS_DIR = SUPERCONDUCTING_ROOT / "calibrations"

# Make `quam_config`, `calibration_utils`, `calibrations` importable the same
# way the existing `tests/` suite does (see e.g. tests/test_iq_blobs_gef.py).
sys.path.insert(0, str(SUPERCONDUCTING_ROOT))

from fake_quam import build_fake_quam

_QUALIBRATE_CONFIG_TEMPLATE = """
[quam]
state_path = "{state_path}"

[qualibrate]
version = 5
project = "smoke_test"
log_folder = "{log_folder}"

[qualibrate.storage]
type = "local_storage"
location = "{storage_location}"

[qualibrate.calibration_library]
folder = "{calibrations_dir}"
resolver = "qualibrate.QualibrationLibrary"
"""


@pytest.fixture(scope="session", autouse=True)
def _isolated_quam_environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Point quam/qualibrate at a throwaway state + config dir, then build the fake QUAM."""
    session_dir = tmp_path_factory.mktemp("smoke_quam")
    state_path = session_dir / "quam_state"
    config_dir = session_dir / "qualibrate_config"
    log_folder = session_dir / "logs"
    storage_location = session_dir / "data"
    for d in (state_path, config_dir, log_folder, storage_location):
        d.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    config_path.write_text(
        _QUALIBRATE_CONFIG_TEMPLATE.format(
            state_path=state_path,
            log_folder=log_folder,
            storage_location=storage_location,
            calibrations_dir=CALIBRATIONS_DIR,
        )
    )

    env_overrides = {
        "QUAM_STATE_PATH": str(state_path),
        "QUAM_CONFIG_FILE": str(config_path),
        "QUALIBRATE_CONFIG_FILE": str(config_dir),
    }
    previous = {key: os.environ.get(key) for key in env_overrides}
    os.environ.update(env_overrides)
    try:
        build_fake_quam(state_path)
        yield state_path
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture(scope="session", autouse=True)
def _block_hardware_connect(_isolated_quam_environment: Path) -> Iterator[None]:
    """Make `machine.connect()` raise loudly instead of reaching real hardware.

    In the normal case this is never hit: the harness stops every node right
    after `create_qua_program`, before `simulate_qua_program`/
    `execute_qua_program` (the actions that call `connect()`) ever run. This
    is a tripwire, not the primary control -- see harness.py.
    """
    from quam_builder.architecture.superconducting.qpu import FixedFrequencyQuam, FluxTunableQuam

    def _blocked_connect(self, *args, **kwargs):
        raise RuntimeError(
            "Smoke test tried to call machine.connect() -- this run must never reach "
            "real hardware. If a node legitimately needs this, it is out of scope for "
            "smoke testing."
        )

    originals = (FluxTunableQuam.connect, FixedFrequencyQuam.connect)
    FluxTunableQuam.connect = _blocked_connect
    FixedFrequencyQuam.connect = _blocked_connect
    try:
        yield
    finally:
        FluxTunableQuam.connect, FixedFrequencyQuam.connect = originals


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    """Write the morning report to the GitHub Actions step summary, if running in CI."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    outcome_labels = {
        "passed": "✅ passed",
        "failed": "❌ FAILED",
        "error": "❌ ERROR",
        "xfailed": "🟡 known-broken (as expected)",
        "xpassed": "⚠️ known-broken list is stale -- this now passes",
    }
    lines = ["", "## Nightly QuaLibs smoke test", "", "| Node | Result |", "| --- | --- |"]
    stats = terminalreporter.stats
    for outcome in ("failed", "error", "xpassed", "passed", "xfailed"):
        for report in stats.get(outcome, []):
            node_id = getattr(report, "nodeid", "")
            name = node_id.split("::")[-1] if "::" in node_id else node_id
            if not name:
                continue
            lines.append(f"| `{name}` | {outcome_labels.get(outcome, outcome)} |")

    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
