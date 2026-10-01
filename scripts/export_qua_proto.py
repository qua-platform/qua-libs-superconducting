"""Export a QCA script's QUA program and config as serialized protobuf (JSON envelope).

Run this under the environment whose `qm-qua` major matches the script — typically the
`../qua-libs` Poetry env (qm-qua 1.x) for the `QL-1212-validation` originals. It only
builds the `Program` object and converts the dict config with `load_config`; nothing is
sent to a QOP server and no `qua_evaluator` import is needed. The output is read by
`emulate_waveform_runner.py --from-proto` in this repo's env, where the evaluator runs it
with an explicit dialect.

Output shape:
    {"dialect": "qua1", "qm_qua_version": "...", "program": "<base64>", "config": "<base64>"}
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
from qca_script_loader import load_program_namespace, parse_overrides  # noqa: E402


def export_script(script_path: Path, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    import logging

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)

    import qm
    from qm import QuantumMachinesManager
    from qm.exceptions import CapabilitiesNotInitializedError
    from qm.program import load_config

    config, program, _ns = load_program_namespace(script_path, overrides)

    try:
        load_config({})
    except CapabilitiesNotInitializedError:
        QuantumMachinesManager.set_capabilities_offline()

    major = int(qm.__version__.split(".", 1)[0])
    program_bytes = program.qua_program.SerializeToString()
    config_bytes = load_config(config).SerializeToString()
    return {
        "dialect": f"qua{major}",
        "qm_qua_version": qm.__version__,
        "program": base64.b64encode(program_bytes).decode("ascii"),
        "config": base64.b64encode(config_bytes).decode("ascii"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("script", type=Path, help="QCA script path")
    parser.add_argument("--output", type=Path, required=True, help="Write the JSON envelope to this file")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="NAME=EXPR",
        help="Rewrite a top-level script assignment before loading (repeatable), e.g. --set n_avg=2",
    )
    args = parser.parse_args()

    script_path = args.script.resolve()
    if not script_path.is_file():
        print(f"Script not found: {script_path}", file=sys.stderr)
        return 1

    output_path = args.output.resolve()
    os.chdir(script_path.parent)
    sys.path.insert(0, str(script_path.parent))

    try:
        payload = export_script(script_path, parse_overrides(args.overrides))
    except Exception as exc:  # noqa: BLE001 — surface failures to the orchestrator
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
