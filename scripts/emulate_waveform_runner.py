"""Headless QCA script emulation — emits a pulse-schedule JSON on stdout.

Runs a QCA script's QUA program through `qua_evaluator.QuaEvaluator.evaluate()` instead
of `qmm.simulate()`. This is the QUA 2 / QOP 4 counterpart to
`simulate_waveform_runner.py`: no live QOP session is needed, but the QUA program
must be QUA 2-shaped (real-time ops inside a `@shot`) and the config must already
be QUA 2 schema. Scripts that are not yet migrated fail in one of a few known,
expected ways — reported as a `_blocked` payload rather than a crash:

- Any error while loading/exec'ing the script's prelude — it still imports QUA
  1.4.0-only APIs (e.g. `qm.qua.extensions.QuaIterable`) that don't exist in
  qm-qua 2.0, or uses old QUA 1.x call signatures (e.g. 4-arg
  `for_(var, start, cond, step)`, removed in favor of `with for_(lo, hi, step) as i`).
  This is deliberately broad: pre-QUA-2 scripts can fail in many different ways
  while exec'ing their (not-yet-migrated) control flow.
- `InvalidStatementContextError` / `UnsupportedFeatureError` (qua_evaluator.errors) —
  real-time ops (`play`, `measure`, `wait`, ...) used outside a `@shot`.
- `qm.exceptions.ConfigValidationException` (e.g. `ConfigSchemaError`) — the config
  still uses QUA 1.x / 1.4.0 keys (e.g. pulse-level `waveforms`, element-level
  `smearing` / `time_of_flight`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qca_script_loader import json_default as _json_default  # noqa: E402
from qca_script_loader import load_program_namespace  # noqa: E402


class EmulateBlocked(RuntimeError):
    """A script cannot yet be emulated for a known, expected reason (not a bug)."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"kind": type(entry).__name__}

    quantum_element = getattr(entry, "quantum_element", None)
    if quantum_element is not None:
        data["element"] = quantum_element

    for attr in (
        "start_time_ns",
        "start_time_digital_ns",
        "duration_ns",
        "amplitude",
        "condition",
        "reset_phase",
        "truncate_ns",
    ):
        value = getattr(entry, attr, None)
        if value is not None:
            data[attr] = value

    pulse_ref = getattr(entry, "pulse_ref", None)
    if pulse_ref is not None:
        data["pulse"] = str(pulse_ref)

    analog_port = getattr(entry, "analog_port", None)
    if analog_port is not None:
        try:
            data["analog_ports"] = [str(p.port) for p in analog_port.all_ports]
        except Exception:  # noqa: BLE001 — best-effort enrichment, never fatal
            pass

    digital_port = getattr(entry, "digital_port", None)
    if digital_port is not None:
        try:
            data["digital_ports"] = [str(p.port) for p in digital_port.all_ports]
        except Exception:  # noqa: BLE001
            pass

    up_conversion = getattr(entry, "up_conversion", None)
    if up_conversion is not None:
        frequency = getattr(up_conversion, "frequency", None)
        if frequency is not None:
            data["frequency"] = frequency
        frame = getattr(up_conversion, "frame", None)
        if frame is not None:
            data["frame"] = frame

    return data


def emulate_script(script_path: Path, length_ns: int | None) -> dict[str, Any]:
    import logging

    # qm/qua_evaluator log to stdout by default; keep stdout clean for the JSON payload
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)

    from qm import QuantumMachinesManager
    from qm.exceptions import CapabilitiesNotInitializedError, ConfigValidationException
    from qm.program import load_config
    from qua_evaluator import QuaEvaluator
    from qua_evaluator.errors import InvalidStatementContextError, UnsupportedFeatureError

    try:
        config, program, _ns = load_program_namespace(script_path)
    except Exception as exc:  # noqa: BLE001 — pre-QUA-2 scripts fail loading in many ways
        raise EmulateBlocked("needs-qua2-script-migration", str(exc)) from exc

    try:
        load_config({})
    except CapabilitiesNotInitializedError:
        QuantumMachinesManager.set_capabilities_offline()

    try:
        state = QuaEvaluator().evaluate(program, config=config, length=length_ns)
    except InvalidStatementContextError as exc:
        raise EmulateBlocked("needs-shot-migration", str(exc)) from exc
    except UnsupportedFeatureError as exc:
        raise EmulateBlocked("unsupported-feature", str(exc)) from exc
    except ConfigValidationException as exc:
        raise EmulateBlocked("needs-config-migration", str(exc)) from exc

    sequence = [_entry_to_dict(entry) for entry in state.sequence]
    return {
        "_backend": "emulate",
        "sequence": sequence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="QCA script path (run from its directory context)")
    parser.add_argument(
        "--length-ns",
        type=int,
        default=None,
        help="Emulation window length in ns (default: inferred from the program's sequence)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to this file (default: stdout)",
    )
    args = parser.parse_args()

    script_path = args.script.resolve()
    if not script_path.is_file():
        print(f"Script not found: {script_path}", file=sys.stderr)
        return 1

    import os

    os.chdir(script_path.parent)
    sys.path.insert(0, str(script_path.parent))

    try:
        report = emulate_script(script_path, args.length_ns)
    except EmulateBlocked as blocked:
        report = {
            "_backend": "emulate",
            "_blocked": {"reason": blocked.reason, "detail": blocked.detail},
            "sequence": [],
        }
    except Exception as exc:  # noqa: BLE001 — surface unexpected runner failures to orchestrator
        print(str(exc), file=sys.stderr)
        return 1

    payload = json.dumps(report, default=_json_default, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
