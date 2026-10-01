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

With `--from-proto`, the positional argument is instead a JSON envelope written by
`export_qua_proto.py` (serialized program + config built in another environment, e.g.
the `../qua-libs` Poetry env with qm-qua 1.x). The bytes are evaluated with the
envelope's dialect, so the QUA 1 originals can be evaluated here without qm-qua 1.x.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qca_script_loader import json_default as _json_default  # noqa: E402
from qca_script_loader import load_program_namespace, parse_overrides  # noqa: E402


class EmulateBlocked(RuntimeError):
    """A script cannot yet be emulated for a known, expected reason (not a bug)."""

    def __init__(self, reason: str, detail: str):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _fmt_port(port: Any) -> str:
    """`con/fem/port` — the dialects resolve ports to `ControllerPort` or a plain tuple."""
    try:
        return "/".join(str(part) for part in tuple(port))
    except TypeError:
        return str(port)


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
            data["analog_ports"] = [_fmt_port(p.port) for p in analog_port.all_ports]
        except Exception:  # noqa: BLE001 — best-effort enrichment, never fatal
            pass

    digital_port = getattr(entry, "digital_port", None)
    if digital_port is not None:
        try:
            data["digital_ports"] = [_fmt_port(p.port) for p in digital_port.all_ports]
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


def _quiet_logging() -> None:
    import logging

    # qm/qua_evaluator log to stdout by default; keep stdout clean for the JSON payload
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)


def _evaluate(program: Any, config: Any, length_ns: int | None, dialect: Any = None) -> dict[str, Any]:
    from qm.exceptions import ConfigValidationException
    from qua_evaluator import QuaEvaluator
    from qua_evaluator.errors import InvalidStatementContextError, UnsupportedFeatureError

    try:
        state = QuaEvaluator().evaluate(program, config=config, length=length_ns, dialect=dialect)
    except InvalidStatementContextError as exc:
        raise EmulateBlocked("needs-shot-migration", str(exc)) from exc
    except UnsupportedFeatureError as exc:
        raise EmulateBlocked("unsupported-feature", str(exc)) from exc
    except ConfigValidationException as exc:
        raise EmulateBlocked("needs-config-migration", str(exc)) from exc

    return {
        "_backend": "emulate",
        "dialect": state.dialect.value if state.dialect is not None else None,
        "sequence": [_entry_to_dict(entry) for entry in state.sequence],
    }


def emulate_script(script_path: Path, length_ns: int | None, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    _quiet_logging()

    from qm import QuantumMachinesManager
    from qm.exceptions import CapabilitiesNotInitializedError
    from qm.program import load_config

    try:
        config, program, _ns = load_program_namespace(script_path, overrides)
    except Exception as exc:  # noqa: BLE001 — pre-QUA-2 scripts fail loading in many ways
        raise EmulateBlocked("needs-qua2-script-migration", str(exc)) from exc

    try:
        load_config({})
    except CapabilitiesNotInitializedError:
        QuantumMachinesManager.set_capabilities_offline()

    return _evaluate(program, config, length_ns)


def emulate_proto(envelope_path: Path, length_ns: int | None) -> dict[str, Any]:
    """Evaluate a program/config envelope written by `export_qua_proto.py`."""
    _quiet_logging()

    from qua_evaluator import Dialect

    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    dialect = Dialect(envelope["dialect"])
    program = base64.b64decode(envelope["program"])
    config = base64.b64decode(envelope["config"])
    return _evaluate(program, config, length_ns, dialect=dialect)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "script",
        type=Path,
        help="QCA script path (run from its directory context), or an export_qua_proto.py envelope with --from-proto",
    )
    parser.add_argument(
        "--from-proto",
        action="store_true",
        help="Treat the positional argument as an export_qua_proto.py JSON envelope instead of a script",
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="NAME=EXPR",
        help="Rewrite a top-level script assignment before loading (repeatable), e.g. --set n_avg=2",
    )
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

    output_path = args.output.resolve() if args.output else None

    try:
        if args.from_proto:
            if args.overrides:
                print("--set applies at export time; pass it to export_qua_proto.py instead", file=sys.stderr)
                return 1
            report = emulate_proto(script_path, args.length_ns)
        else:
            os.chdir(script_path.parent)
            sys.path.insert(0, str(script_path.parent))
            report = emulate_script(script_path, args.length_ns, parse_overrides(args.overrides))
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
    if output_path:
        output_path.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
