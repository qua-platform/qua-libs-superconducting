"""Compare migrated QCA script simulations against qua-libs baseline waveform reports."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "simulate_waveform_runner.py"

DEFAULT_3D_SCRIPTS = (
    "01_storage_spectroscopy.py",
    "00_selective_pulse_power_rabi.py",
    "06a_qubit_AC_Stark_shift_from_readout_pumping.py",
    "03a_number_splitting_spectroscopy_w_displacement.py",
    "09_swapping.py",
)

SKIP_KEYS = frozenset({"pulser", "chirp_info", "iq_info"})


def _round_value(value: Any, precision: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, precision)
    if isinstance(value, list):
        return [_round_value(v, precision) for v in value]
    if isinstance(value, dict):
        return {k: _round_value(v, precision) for k, v in value.items()}
    return value


def _fmt_list(values: Any) -> str:
    if not isinstance(values, list):
        return str(values)
    return ",".join(f"{v:.6f}" if isinstance(v, float) else str(v) for v in values)


def _fmt_ports(values: Any) -> str:
    if isinstance(values, list):
        return ",".join(str(v) for v in values)
    return str(values)


def _pulse_label(pulse_name: str) -> str:
    if "OriginPulseName=" in pulse_name:
        return pulse_name.split("OriginPulseName=", 1)[1]
    return pulse_name


def _iq_label(entry: dict[str, Any]) -> str:
    iq = entry.get("iq_info") or {}
    if iq.get("isI"):
        return "I"
    if iq.get("isQ"):
        return "Q"
    return "?"


def _canonical_analog(entry: dict[str, Any]) -> str:
    parts = [
        "analog",
        f"controller={entry.get('controller')}",
        f"element={entry.get('element')}",
        f"pulse={_pulse_label(str(entry.get('pulse_name', '')))}",
        f"waveform={entry.get('waveform_name')}",
        f"timestamp={entry.get('timestamp')}",
        f"length={entry.get('length')}",
        f"ports={_fmt_ports(entry.get('output_ports'))}",
        f"iq={_iq_label(entry)}",
        f"amp={_fmt_list(_round_value(entry.get('current_amp_elements')))}",
        f"frame={_fmt_list(_round_value(entry.get('current_frame')))}",
        f"if={_round_value(entry.get('current_intermediate_frequency'))}",
        f"phase={_round_value(entry.get('current_phase'))}",
    ]
    return " | ".join(parts)


def _canonical_digital(entry: dict[str, Any]) -> str:
    parts = [
        "digital",
        f"controller={entry.get('controller')}",
        f"element={entry.get('element')}",
        f"pulse={_pulse_label(str(entry.get('pulse_name', '')))}",
        f"timestamp={entry.get('timestamp')}",
        f"length={entry.get('length')}",
        f"ports={_fmt_ports(entry.get('output_ports'))}",
        f"samples={entry.get('samples')}",
    ]
    return " | ".join(parts)


def _canonical_adc(entry: dict[str, Any]) -> str:
    parts = [
        "adc",
        f"controller={entry.get('controller')}",
        f"element={entry.get('element')}",
        f"pulse={_pulse_label(str(entry.get('pulse_name', '')))}",
        f"timestamp={entry.get('timestamp')}",
        f"length={entry.get('length')}",
        f"ports={_fmt_ports(entry.get('input_ports'))}",
    ]
    return " | ".join(parts)


def canonical_waveform_lines(report: dict[str, Any]) -> list[str]:
    entries: list[tuple[int | None, str]] = []
    min_ts: int | None = None
    for category, formatter in (
        ("analog", _canonical_analog),
        ("digital", _canonical_digital),
        ("adc", _canonical_adc),
    ):
        for entry in report.get(
            {"analog": "analog_waveforms", "digital": "digital_waveforms", "adc": "adc_acquisitions"}[category],
            [],
        ) or []:
            ts = entry.get("timestamp")
            if isinstance(ts, (int, float)):
                ts_int = int(ts)
                min_ts = ts_int if min_ts is None else min(min_ts, ts_int)
            entries.append((ts if isinstance(ts, (int, float)) else None, category, entry))

    def _with_relative_ts(entry: dict[str, Any], ts: int | None) -> dict[str, Any]:
        if min_ts is None or ts is None:
            return entry
        adjusted = dict(entry)
        adjusted["timestamp"] = int(ts) - min_ts
        return adjusted

    lines: list[str] = []
    for ts, category, entry in entries:
        if category == "analog":
            lines.append(_canonical_analog(_with_relative_ts(entry, ts)))
        elif category == "digital":
            lines.append(_canonical_digital(_with_relative_ts(entry, ts)))
        else:
            lines.append(_canonical_adc(entry))
    return sorted(lines)


def waveform_counts(report: dict[str, Any]) -> dict[str, int]:
    return {
        "analog": len(report.get("analog_waveforms") or []),
        "digital": len(report.get("digital_waveforms") or []),
        "adc": len(report.get("adc_acquisitions") or []),
    }


def run_side_simulation(
    *,
    runner_cmd: str,
    runner_repo: Path,
    script_path: Path,
    output_path: Path,
    duration: int,
) -> dict[str, Any]:
    cmd = [
        *shlex.split(runner_cmd),
        str(RUNNER.resolve()),
        str(script_path.resolve()),
        "--duration",
        str(duration),
        "--output",
        str(output_path.resolve()),
    ]
    env = os.environ.copy()
    # Avoid inherited uv venv confusing Poetry's Python selection in qua-libs.
    if "poetry" in runner_cmd:
        env.pop("VIRTUAL_ENV", None)
        env.pop("UV_PROJECT_ENVIRONMENT", None)
    proc = subprocess.run(
        cmd,
        cwd=runner_repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Simulation failed for {script_path.name}:\n{proc.stderr or proc.stdout}"
        )
    return json.loads(output_path.read_text(encoding="utf-8"))


def compare_reports(baseline: dict[str, Any], migrated: dict[str, Any]) -> tuple[list[str], list[str], str]:
    baseline_lines = canonical_waveform_lines(baseline)
    migrated_lines = canonical_waveform_lines(migrated)
    diff = "\n".join(
        difflib.unified_diff(
            baseline_lines,
            migrated_lines,
            fromfile="baseline",
            tofile="migrated",
            lineterm="",
        )
    )
    return baseline_lines, migrated_lines, diff


def validate_script(
    *,
    script_name: str,
    baseline_root: Path,
    baseline_repo: Path,
    baseline_runner: str,
    migrated_root: Path,
    migrated_repo: Path,
    migrated_runner: str,
    results_dir: Path,
    duration: int,
) -> dict[str, Any]:
    stem = Path(script_name).stem
    out_dir = results_dir / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline_script = baseline_root / script_name
    migrated_script = migrated_root / script_name
    for path in (baseline_script, migrated_script):
        if not path.is_file():
            raise FileNotFoundError(path)

    baseline_report_path = out_dir / "baseline_report.json"
    migrated_report_path = out_dir / "migrated_report.json"

    baseline_report = run_side_simulation(
        runner_cmd=baseline_runner,
        runner_repo=baseline_repo,
        script_path=baseline_script,
        output_path=baseline_report_path,
        duration=duration,
    )
    migrated_report = run_side_simulation(
        runner_cmd=migrated_runner,
        runner_repo=migrated_repo,
        script_path=migrated_script,
        output_path=migrated_report_path,
        duration=duration,
    )

    baseline_lines, migrated_lines, diff = compare_reports(baseline_report, migrated_report)
    (out_dir / "baseline_lines.txt").write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")
    (out_dir / "migrated_lines.txt").write_text("\n".join(migrated_lines) + "\n", encoding="utf-8")
    (out_dir / "diff.txt").write_text(diff, encoding="utf-8")

    baseline_counts = waveform_counts(baseline_report)
    migrated_counts = waveform_counts(migrated_report)
    passed = diff == "" and baseline_counts == migrated_counts

    summary = {
        "script": script_name,
        "passed": passed,
        "timestamp": datetime.now(UTC).isoformat(),
        "baseline_counts": baseline_counts,
        "migrated_counts": migrated_counts,
        "baseline_line_count": len(baseline_lines),
        "migrated_line_count": len(migrated_lines),
        "diff_line_count": len([ln for ln in diff.splitlines() if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def format_notes(summary: dict[str, Any]) -> str:
    bc = summary["baseline_counts"]
    if summary["passed"]:
        return (
            f"simulate=True; waveform report matches baseline "
            f"({bc['analog']} analog, {bc['digital']} digital, {bc['adc']} ADC); 0 diff lines"
        )
    diff_path = f"validation_results/3D-storage-cavity/{Path(summary['script']).stem}/diff.txt"
    return f"simulate=True; waveform mismatch — see {diff_path}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-root",
        type=Path,
        required=True,
        help="Baseline script folder (e.g. qua-libs .../3D-storage-cavity)",
    )
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=Path("/Users/brunogiacomazzo/qua-libs"),
        help="qua-libs repo root for poetry run cwd",
    )
    parser.add_argument(
        "--baseline-runner",
        default="poetry run python",
        help="Command prefix to run baseline simulate_waveform_runner.py",
    )
    parser.add_argument(
        "--migrated-root",
        type=Path,
        default=REPO_ROOT / "Quantum-Control-Applications/Superconducting/3D-storage-cavity",
        help="Migrated script folder",
    )
    parser.add_argument(
        "--migrated-repo",
        type=Path,
        default=REPO_ROOT,
        help="Migrated repo root for uv run cwd",
    )
    parser.add_argument(
        "--migrated-runner",
        default="uv run python",
        help="Command prefix to run migrated simulate_waveform_runner.py",
    )
    parser.add_argument(
        "--scripts",
        default=",".join(DEFAULT_3D_SCRIPTS),
        help="Comma-separated script filenames",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=REPO_ROOT / "validation_results/3D-storage-cavity",
        help="Directory for comparison artifacts",
    )
    parser.add_argument("--duration", type=int, default=10_000, help="Simulation duration (clock cycles)")
    parser.add_argument(
        "--print-notes",
        action="store_true",
        help="Print VALIDATION.md Notes snippets for each script",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    scripts = [s.strip() for s in args.scripts.split(",") if s.strip()]

    summaries: list[dict[str, Any]] = []
    failures: list[str] = []

    for script_name in scripts:
        print(f"Validating {script_name}...", flush=True)
        try:
            summary = validate_script(
                script_name=script_name,
                baseline_root=args.baseline_root.resolve(),
                baseline_repo=args.baseline_repo.resolve(),
                baseline_runner=args.baseline_runner,
                migrated_root=args.migrated_root.resolve(),
                migrated_repo=args.migrated_repo.resolve(),
                migrated_runner=args.migrated_runner,
                results_dir=args.results_dir.resolve(),
                duration=args.duration,
            )
            summaries.append(summary)
            status = "PASS" if summary["passed"] else "FAIL"
            print(f"  {status}: {format_notes(summary)}")
            if args.print_notes:
                print(f"  Notes: {format_notes(summary)}")
            if not summary["passed"]:
                failures.append(script_name)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}", file=sys.stderr)
            failures.append(script_name)

    aggregate = {
        "passed": len(failures) == 0,
        "scripts": summaries,
        "failures": failures,
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2) + "\n",
        encoding="utf-8",
    )

    if failures:
        print(f"\nFailed scripts: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("\nAll scripts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
