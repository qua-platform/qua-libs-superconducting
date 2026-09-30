"""Offline smoke test for the emulate-based validation harness (QUA 2 branch).

Uses a synthetic QUA 2 fixture (`tests/fixtures/qua2_emulate_smoke_program.py`) —
not a real QCA script — so this runs fully offline: no CS rack, no `../qua-libs`
baseline checkout, no live QOP session. Real QCA scripts are not yet emulate-ready
(see scripts/emulate_waveform_runner.py module docstring for the known blockers);
this test only exercises the tooling.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "qua2_emulate_smoke_program.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

qua_evaluator = pytest.importorskip("qua_evaluator")

import emulate_waveform_runner  # noqa: E402
import validate_simulation_baseline as harness  # noqa: E402


@pytest.fixture()
def emulate_report() -> dict:
    return emulate_waveform_runner.emulate_script(FIXTURE, length_ns=None)


def test_fixture_emulates_without_blocking(emulate_report: dict) -> None:
    assert emulate_report["_backend"] == "emulate"
    assert "_blocked" not in emulate_report


def test_fixture_sequence_has_expected_entries(emulate_report: dict) -> None:
    sequence = emulate_report["sequence"]
    assert sequence, "expected at least one sequence entry"

    play_entries = [e for e in sequence if e["kind"] == "PlayEntry"]
    # 5 iterations (for_(0.1, 1.0, 0.2)) x 2 plays (qe_single, qe_mixed) per @shot call.
    assert len(play_entries) == 10

    elements = {e["element"] for e in play_entries}
    assert elements == {"qe_single", "qe_mixed"}

    single_entry = next(e for e in play_entries if e["element"] == "qe_single")
    assert single_entry["pulse"] == "pulse_single"
    assert single_entry["duration_ns"] == 400
    assert single_entry["analog_ports"] == ["ControllerPort(controller='con1', fem=1, port_number=1)"]

    mixed_entry = next(e for e in play_entries if e["element"] == "qe_mixed")
    assert mixed_entry["pulse"] == "pulse_mixed"
    assert mixed_entry["duration_ns"] == 800
    assert len(mixed_entry["analog_ports"]) == 2


def test_canonical_schedule_lines_self_diff_is_empty(emulate_report: dict) -> None:
    """Sanity-check the harness's emulate-side canonicalizer without needing a
    real baseline: comparing a report against itself must yield zero diff lines.
    """
    baseline_lines, migrated_lines, diff = harness.compare_reports(
        emulate_report,
        emulate_report,
        baseline_backend="emulate",
        migrated_backend="emulate",
    )
    assert baseline_lines == migrated_lines
    assert diff == ""
    assert len(baseline_lines) > 0


def test_canonical_schedule_lines_detect_a_real_difference() -> None:
    """The canonicalizer must not be a no-op: an actually-different report should
    produce a non-empty diff.
    """
    report_a = {
        "_backend": "emulate",
        "sequence": [
            {
                "kind": "PlayEntry",
                "element": "qe_single",
                "start_time_ns": 0,
                "duration_ns": 400,
                "pulse": "pulse_single",
            }
        ],
    }
    report_b = {
        "_backend": "emulate",
        "sequence": [
            {
                "kind": "PlayEntry",
                "element": "qe_single",
                "start_time_ns": 0,
                "duration_ns": 800,
                "pulse": "pulse_single",
            }
        ],
    }
    _, _, diff = harness.compare_reports(report_a, report_b, baseline_backend="emulate", migrated_backend="emulate")
    assert diff != ""


def test_emulate_runner_reports_blocked_status_for_pre_qua2_script(tmp_path: Path) -> None:
    """A pre-QUA-2 script (using QUA 1.x `for_()` 4-arg form) must be reported as
    `_blocked`, not raise — this is the expected state for today's real QCA scripts.
    """
    pre_qua2_script = tmp_path / "pre_qua2.py"
    pre_qua2_script.write_text(
        "from qm.qua import *\n"
        "from qm import QuantumMachinesManager\n"
        "qop_ip = '127.0.0.1'\n"
        "cluster_name = 'smoke-test'\n"
        "config = {}\n"
        "with program() as pre_qua2:\n"
        "    a = declare(fixed)\n"
        "    with for_(a, 0, a < 1.0, a + 0.1):\n"
        "        pass\n"
        "qmm = QuantumMachinesManager(host=qop_ip, cluster_name=cluster_name)\n",
        encoding="utf-8",
    )

    with pytest.raises(emulate_waveform_runner.EmulateBlocked) as exc_info:
        emulate_waveform_runner.emulate_script(pre_qua2_script, length_ns=None)
    assert exc_info.value.reason == "needs-qua2-script-migration"
