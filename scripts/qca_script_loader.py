"""Shared QCA script loading helpers for the simulate/emulate waveform runners.

Both `simulate_waveform_runner.py` (OPX simulator) and `emulate_waveform_runner.py`
(QUA emulator) need to load a QCA script's prelude to get at its `program` and
`config` without running the rest of the file (plotting, live fetching, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def json_default(obj: Any) -> Any:
    """`json.dumps(..., default=...)` handler for numpy scalars/arrays."""
    if hasattr(obj, "item"):
        return obj.item()
    if hasattr(obj, "tolist"):
        return obj.tolist()
    return str(obj)


def find_program_name(source: str) -> str | None:
    match = re.search(r"with\s+program\s*\(\s*\)\s+as\s+(\w+)\s*:", source)
    return match.group(1) if match else None


def load_program_namespace(script_path: Path) -> tuple[Any, Any, dict[str, Any]]:
    """Exec a QCA script's prelude (everything before `qmm = QuantumMachinesManager(...)`)
    and return `(config, program, namespace)`.

    Callers that need `qop_ip` / `cluster_name` / `qop_port` (e.g. to open a live
    session for OPX simulation) should check for those in the returned namespace
    themselves — this helper only guarantees `program` and `config`.
    """
    import matplotlib

    matplotlib.use("Agg")

    source = script_path.read_text(encoding="utf-8")
    marker = "qmm = QuantumMachinesManager"
    if marker not in source:
        raise RuntimeError(f"{script_path}: could not find '{marker}'")
    prelude = source.split(marker, 1)[0]

    ns: dict[str, Any] = {
        "__name__": "__simulate_runner__",
        "__file__": str(script_path.resolve()),
    }
    exec(compile(prelude, str(script_path), "exec"), ns)  # noqa: S102

    prog_name = find_program_name(source)
    program = ns.get(prog_name) if prog_name else None
    if program is None:
        for key, value in ns.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "is_reversed"):
                program = value
                break
    if program is None:
        raise RuntimeError(f"{script_path}: QUA program not found (expected '{prog_name}')")

    if "config" not in ns:
        raise RuntimeError(f"{script_path}: configuration did not define 'config'")

    return ns["config"], program, ns
