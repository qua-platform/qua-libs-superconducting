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


def parse_overrides(items: list[str] | None) -> dict[str, str]:
    """Parse repeated `NAME=EXPR` CLI values into a dict."""
    overrides: dict[str, str] = {}
    for item in items or []:
        name, sep, expr = item.partition("=")
        if not sep or not name.strip().isidentifier() or not expr.strip():
            raise ValueError(f"Invalid override {item!r}; expected NAME=EXPR (e.g. n_avg=2)")
        overrides[name.strip()] = expr.strip()
    return overrides


def apply_overrides(source: str, overrides: dict[str, str]) -> str:
    """Rewrite top-level `NAME = ...` assignment lines in a script to `NAME = EXPR`.

    Only unindented, single-line assignments are rewritten (e.g. `n_avg = 1000  # ...`).
    Names with no such assignment are left alone, so one folder-wide `--set n_avg=2`
    also works for scripts that have no `n_avg`.
    """
    for name, expr in overrides.items():
        pattern = re.compile(rf"^{re.escape(name)}\s*=(?!=).*$", re.MULTILINE)
        source = pattern.sub(f"{name} = {expr}", source)
    return source


def load_program_namespace(
    script_path: Path, overrides: dict[str, str] | None = None
) -> tuple[Any, Any, dict[str, Any]]:
    """Exec a QCA script's prelude (everything before `qmm = QuantumMachinesManager(...)`)
    and return `(config, program, namespace)`.

    `overrides` rewrites top-level assignments before exec (see `apply_overrides`).

    Callers that need `qop_ip` / `cluster_name` / `qop_port` (e.g. to open a live
    session for OPX simulation) should check for those in the returned namespace
    themselves — this helper only guarantees `program` and `config`.
    """
    import matplotlib

    matplotlib.use("Agg")

    source = script_path.read_text(encoding="utf-8")
    if overrides:
        source = apply_overrides(source, overrides)
    marker = "qmm = QuantumMachinesManager"
    if marker not in source:
        raise RuntimeError(f"{script_path}: could not find '{marker}'")
    prelude = source.split(marker, 1)[0]

    ns: dict[str, Any] = {
        "__name__": "__simulate_runner__",
        "__file__": str(script_path.resolve()),
    }
    # dont_inherit=True: this module's `from __future__ import annotations` (line 8)
    # would otherwise leak into the compiled prelude, silently stringifying every
    # annotation in the exec'd script (e.g. `def play_two(a: fixed)` -> `a: "fixed"`),
    # which breaks qm-qua 2's `@shot` decorator (it requires a resolved concrete type).
    exec(compile(prelude, str(script_path), "exec", dont_inherit=True), ns)  # noqa: S102

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
