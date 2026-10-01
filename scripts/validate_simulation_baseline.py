"""Compare migrated QCA scripts against their qua-libs baseline.

Default: both sides through `qmm.simulate()`, diffing waveform reports. With
`--baseline-backend emulate --migrated-backend emulate`, both sides go through
`QuaEvaluator` (baseline as QUA 1 via `export_qua_proto.py`, migrated as QUA 2) and the
pulse schedules are diffed instead.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from validation_matrix import (
    VALIDATION_FOLDERS,
    default_baseline_repo,
    list_folders,
    resolve_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKENDS = ("simulate", "emulate")
RUNNER_BY_BACKEND = {
    "simulate": REPO_ROOT / "scripts" / "simulate_waveform_runner.py",
    "emulate": REPO_ROOT / "scripts" / "emulate_waveform_runner.py",
}
EXPORT_RUNNER = REPO_ROOT / "scripts" / "export_qua_proto.py"
SCHEDULE_KINDS = ("PlayEntry", "MeasureEntry")


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
        for entry in (
            report.get(
                {"analog": "analog_waveforms", "digital": "digital_waveforms", "adc": "adc_acquisitions"}[category],
                [],
            )
            or []
        ):
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


def _canonical_schedule_entry(entry: dict[str, Any], relative_ts: int | None) -> str:
    ts = relative_ts if relative_ts is not None else entry.get("start_time_ns")
    parts = [
        "measure" if entry.get("kind") == "MeasureEntry" else "play",
        f"element={entry.get('element')}",
        f"pulse={entry.get('pulse')}",
        f"timestamp={ts}",
        f"length={entry.get('duration_ns')}",
        f"analog_ports={_fmt_ports(entry.get('analog_ports'))}",
        f"digital_ports={_fmt_ports(entry.get('digital_ports'))}",
        f"amp={_fmt_list(_round_value(entry.get('amplitude')))}",
        f"frequency={_round_value(entry.get('frequency'))}",
        f"frame={_round_value(entry.get('frame'))}",
    ]
    return " | ".join(parts)


def canonical_schedule_lines(report: dict[str, Any]) -> list[str]:
    """Canonicalize an `emulate_waveform_runner.py` report (`state.sequence`) into
    lines comparable in spirit to `canonical_waveform_lines`.

    Only `PlayEntry` / `MeasureEntry` items are included. Waits, aligns, and QUA 2 shot
    markers are left out: their effect shows up in the relative timestamps, while their
    count differs between dialects (QUA 2 inserts implicit aligns around shots/loops).
    The evaluator does not model ADC/measurement results, so there is no counterpart to
    `canonical_waveform_lines`' "adc" category.
    """
    play_entries = [e for e in (report.get("sequence") or []) if e.get("kind") in SCHEDULE_KINDS]
    starts = [e.get("start_time_ns") for e in play_entries if isinstance(e.get("start_time_ns"), (int, float))]
    min_ts = min(starts) if starts else None

    lines = []
    for entry in play_entries:
        ts = entry.get("start_time_ns")
        relative_ts = int(ts) - int(min_ts) if min_ts is not None and isinstance(ts, (int, float)) else None
        lines.append(_canonical_schedule_entry(entry, relative_ts))
    return sorted(lines)


def schedule_counts(report: dict[str, Any]) -> dict[str, int]:
    counts = {kind: 0 for kind in SCHEDULE_KINDS}
    for entry in report.get("sequence") or []:
        kind = entry.get("kind")
        if kind in counts:
            counts[kind] += 1
    return counts


def canonical_lines_for_backend(report: dict[str, Any], backend: str) -> list[str]:
    if backend == "simulate":
        return canonical_waveform_lines(report)
    if backend == "emulate":
        return canonical_schedule_lines(report)
    raise ValueError(f"Unknown backend: {backend!r}")


def counts_for_backend(report: dict[str, Any], backend: str) -> dict[str, int]:
    if backend == "simulate":
        return waveform_counts(report)
    if backend == "emulate":
        return schedule_counts(report)
    raise ValueError(f"Unknown backend: {backend!r}")


def _override_args(overrides: list[str] | None) -> list[str]:
    return [arg for item in overrides or [] for arg in ("--set", item)]


def _run(cmd: list[str], *, runner_cmd: str, cwd: Path, label: str) -> None:
    env = os.environ.copy()
    # Avoid inherited uv venv confusing Poetry's Python selection in qua-libs.
    if "poetry" in runner_cmd:
        env.pop("VIRTUAL_ENV", None)
        env.pop("UV_PROJECT_ENVIRONMENT", None)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"{label}:\n{proc.stderr or proc.stdout}")


def _emulate_length_ns(duration: int, emulate_length_ns: int | None) -> int:
    return emulate_length_ns if emulate_length_ns is not None else duration * 4


def run_side(
    *,
    backend: str,
    runner_cmd: str,
    runner_repo: Path,
    script_path: Path,
    output_path: Path,
    duration: int,
    emulate_length_ns: int | None,
    overrides: list[str] | None = None,
) -> dict[str, Any]:
    runner_path = RUNNER_BY_BACKEND[backend]
    cmd = [*shlex.split(runner_cmd), str(runner_path.resolve()), str(script_path.resolve())]
    if backend == "simulate":
        cmd += ["--duration", str(duration)]
    else:
        cmd += ["--length-ns", str(_emulate_length_ns(duration, emulate_length_ns))]
        cmd += _override_args(overrides)
    cmd += ["--output", str(output_path.resolve())]
    _run(cmd, runner_cmd=runner_cmd, cwd=runner_repo, label=f"{backend} failed for {script_path.name}")
    return json.loads(output_path.read_text(encoding="utf-8"))


def run_baseline_emulate(
    *,
    export_runner_cmd: str,
    export_repo: Path,
    evaluator_runner_cmd: str,
    evaluator_repo: Path,
    script_path: Path,
    envelope_path: Path,
    output_path: Path,
    duration: int,
    emulate_length_ns: int | None,
    overrides: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate a baseline (QUA 1) script: build its program/config in the baseline env
    with `export_qua_proto.py`, then evaluate the serialized bytes in this repo's env."""
    export_cmd = [
        *shlex.split(export_runner_cmd),
        str(EXPORT_RUNNER.resolve()),
        str(script_path.resolve()),
        "--output",
        str(envelope_path.resolve()),
        *_override_args(overrides),
    ]
    _run(export_cmd, runner_cmd=export_runner_cmd, cwd=export_repo, label=f"export failed for {script_path.name}")

    eval_cmd = [
        *shlex.split(evaluator_runner_cmd),
        str(RUNNER_BY_BACKEND["emulate"].resolve()),
        str(envelope_path.resolve()),
        "--from-proto",
        "--length-ns",
        str(_emulate_length_ns(duration, emulate_length_ns)),
        "--output",
        str(output_path.resolve()),
    ]
    _run(
        eval_cmd,
        runner_cmd=evaluator_runner_cmd,
        cwd=evaluator_repo,
        label=f"emulate failed for exported {script_path.name}",
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def compare_reports(
    baseline: dict[str, Any],
    migrated: dict[str, Any],
    *,
    baseline_backend: str = "simulate",
    migrated_backend: str = "simulate",
) -> tuple[list[str], list[str], str]:
    baseline_lines = canonical_lines_for_backend(baseline, baseline_backend)
    migrated_lines = canonical_lines_for_backend(migrated, migrated_backend)
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
    baseline_backend: str = "simulate",
    migrated_root: Path,
    migrated_repo: Path,
    migrated_runner: str,
    migrated_backend: str = "simulate",
    results_dir: Path,
    duration: int,
    emulate_length_ns: int | None = None,
    overrides: list[str] | None = None,
) -> dict[str, Any]:
    if baseline_backend == "emulate" and migrated_backend != "emulate":
        raise ValueError("--baseline-backend emulate requires --migrated-backend emulate")
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

    # Run the migrated side first: if it's blocked (script/config not yet migrated
    # to the migrated backend's requirements), skip the baseline run entirely —
    # no point spending a rack session comparing against a report we can't produce.
    migrated_report = run_side(
        backend=migrated_backend,
        runner_cmd=migrated_runner,
        runner_repo=migrated_repo,
        script_path=migrated_script,
        output_path=migrated_report_path,
        duration=duration,
        emulate_length_ns=emulate_length_ns,
        overrides=overrides,
    )

    blocked = migrated_report.get("_blocked")
    if blocked:
        summary = {
            "script": script_name,
            "status": "blocked",
            "passed": False,
            "baseline_backend": baseline_backend,
            "migrated_backend": migrated_backend,
            "blocked_reason": blocked.get("reason"),
            "blocked_detail": blocked.get("detail"),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary

    if baseline_backend == "emulate":
        baseline_report = run_baseline_emulate(
            export_runner_cmd=baseline_runner,
            export_repo=baseline_repo,
            evaluator_runner_cmd=migrated_runner,
            evaluator_repo=migrated_repo,
            script_path=baseline_script,
            envelope_path=out_dir / "baseline_proto.json",
            output_path=baseline_report_path,
            duration=duration,
            emulate_length_ns=emulate_length_ns,
            overrides=overrides,
        )
    else:
        baseline_report = run_side(
            backend=baseline_backend,
            runner_cmd=baseline_runner,
            runner_repo=baseline_repo,
            script_path=baseline_script,
            output_path=baseline_report_path,
            duration=duration,
            emulate_length_ns=emulate_length_ns,
        )

    baseline_lines, migrated_lines, diff = compare_reports(
        baseline_report,
        migrated_report,
        baseline_backend=baseline_backend,
        migrated_backend=migrated_backend,
    )
    (out_dir / "baseline_lines.txt").write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")
    (out_dir / "migrated_lines.txt").write_text("\n".join(migrated_lines) + "\n", encoding="utf-8")
    (out_dir / "diff.txt").write_text(diff, encoding="utf-8")

    baseline_counts = counts_for_backend(baseline_report, baseline_backend)
    migrated_counts = counts_for_backend(migrated_report, migrated_backend)
    # Counts vocabularies only match when both sides use the same backend
    # (simulate/simulate or emulate/emulate; not meaningful across simulate/emulate).
    counts_comparable = baseline_backend == migrated_backend
    passed = diff == "" and (not counts_comparable or baseline_counts == migrated_counts)

    summary = {
        "script": script_name,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "baseline_backend": baseline_backend,
        "migrated_backend": migrated_backend,
        "overrides": list(overrides or []),
        "timestamp": datetime.now(UTC).isoformat(),
        "baseline_counts": baseline_counts,
        "migrated_counts": migrated_counts,
        "baseline_line_count": len(baseline_lines),
        "migrated_line_count": len(migrated_lines),
        "diff_line_count": len(
            [ln for ln in diff.splitlines() if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def format_notes(summary: dict[str, Any], results_dir: Path) -> str:
    status = summary.get("status", "pass" if summary.get("passed") else "fail")
    if status == "blocked":
        return f"blocked ({summary.get('blocked_reason')}): {summary.get('blocked_detail')}"

    migrated_backend = summary.get("migrated_backend", "simulate")
    bc = summary.get("baseline_counts", {})
    rel = results_dir / Path(summary["script"]).stem / "diff.txt"
    try:
        diff_path = rel.relative_to(REPO_ROOT)
    except ValueError:
        diff_path = rel

    if migrated_backend == "simulate":
        if summary["passed"]:
            return (
                f"simulate=True; waveform report matches baseline "
                f"({bc['analog']} analog, {bc['digital']} digital, {bc['adc']} ADC); 0 diff lines"
            )
        return f"simulate=True; waveform mismatch — see {diff_path}"

    # emulate backend: schedule-structure comparison (no ADC/measurement counterpart)
    counts_str = ", ".join(f"{k}={v}" for k, v in sorted(bc.items())) or "no entries"
    overrides = summary.get("overrides") or []
    override_str = f" [{', '.join(overrides)}]" if overrides else ""
    if summary.get("baseline_backend") == "emulate":
        if summary["passed"]:
            return f"evaluator QUA1 vs QUA2{override_str}; schedule matches baseline ({counts_str}); 0 diff lines"
        return f"evaluator QUA1 vs QUA2{override_str}; schedule mismatch — see {diff_path}"
    if summary["passed"]:
        return f"emulate=True; schedule matches baseline structure ({counts_str}); 0 diff lines"
    return f"emulate=True; schedule mismatch vs simulator baseline (formats differ) — see {diff_path}"


def _print_folder_catalog() -> None:
    total = 0
    for key in list_folders():
        folder = VALIDATION_FOLDERS[key]
        count = len(folder.scripts)
        total += count
        print(f"  {key} ({count} scripts)")
    print(f"\nTotal: {len(list_folders())} folders, {total} scripts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        choices=list_folders(),
        default=None,
        help="VALIDATION.md folder preset (sets paths and script list)",
    )
    parser.add_argument(
        "--list-folders",
        action="store_true",
        help="List VALIDATION.md folder presets and exit",
    )
    parser.add_argument(
        "--baseline-root",
        type=Path,
        default=None,
        help="Baseline script folder (required unless --folder is set)",
    )
    parser.add_argument(
        "--baseline-repo",
        type=Path,
        default=None,
        help="qua-libs repo root for poetry run cwd (default: ../qua-libs)",
    )
    parser.add_argument(
        "--baseline-runner",
        default="poetry run python",
        help="Command prefix to run baseline simulate_waveform_runner.py",
    )
    parser.add_argument(
        "--migrated-root",
        type=Path,
        default=None,
        help="Migrated script folder (default from --folder or 3D-storage-cavity)",
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
        help="Command prefix to run the migrated-side runner",
    )
    parser.add_argument(
        "--migrated-backend",
        choices=BACKENDS,
        default="simulate",
        help=(
            "Backend for the migrated (this-branch) side: 'simulate' (qmm.simulate(), "
            "default) or 'emulate' (QuaEvaluator.evaluate(), QUA 2 branch). Combined with a "
            "'simulate' baseline the two report formats differ, so the line diff cannot pass; "
            "use --baseline-backend emulate for a real comparison."
        ),
    )
    parser.add_argument(
        "--baseline-backend",
        choices=BACKENDS,
        default="simulate",
        help=(
            "Backend for the baseline (qua-libs) side: 'simulate' (qmm.simulate(), default) or "
            "'emulate' (build the program with --baseline-runner via export_qua_proto.py, then "
            "evaluate it as QUA 1 with --migrated-runner). 'emulate' requires --migrated-backend "
            "emulate and needs no CS rack."
        ),
    )
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        metavar="NAME=EXPR",
        help=(
            "Emulate backends only: rewrite a top-level script assignment on both sides before "
            "loading (repeatable), e.g. --set n_avg=2. The evaluator unrolls every loop iteration."
        ),
    )
    parser.add_argument(
        "--emulate-length-ns",
        type=int,
        default=None,
        help="Emulation window length in ns when --migrated-backend=emulate (default: --duration * 4)",
    )
    parser.add_argument(
        "--scripts",
        default=None,
        help="Comma-separated script filenames (default from --folder or 3D-storage-cavity preset)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for comparison artifacts (default from --folder)",
    )
    parser.add_argument("--duration", type=int, default=10_000, help="Simulation duration (clock cycles)")
    parser.add_argument(
        "--print-notes",
        action="store_true",
        help="Print VALIDATION.md Notes snippets for each script",
    )
    return parser


def _resolve_run_config(args: argparse.Namespace) -> tuple[list[str], Path, Path, Path, Path, Path]:
    baseline_repo = (args.baseline_repo or default_baseline_repo()).resolve()
    migrated_repo = args.migrated_repo.resolve()

    if args.folder:
        paths = resolve_paths(args.folder, repo_root=REPO_ROOT, baseline_repo=baseline_repo)
        scripts = list(paths.scripts)
        baseline_root = paths.baseline_root
        migrated_root = paths.migrated_root
        results_dir = paths.results_dir
    else:
        if args.baseline_root is None:
            raise SystemExit("Either --folder or --baseline-root is required.")
        folder = VALIDATION_FOLDERS["3D-storage-cavity"]
        scripts = [s.strip() for s in args.scripts.split(",") if s.strip()] if args.scripts else list(folder.scripts)
        baseline_root = args.baseline_root.resolve()
        migrated_root = (
            args.migrated_root.resolve()
            if args.migrated_root
            else REPO_ROOT / "Quantum-Control-Applications/Superconducting/3D-storage-cavity"
        )
        results_dir = (
            args.results_dir.resolve() if args.results_dir else REPO_ROOT / "validation_results/3D-storage-cavity"
        )

    if args.scripts and args.folder:
        scripts = [s.strip() for s in args.scripts.split(",") if s.strip()]

    return scripts, baseline_root, baseline_repo, migrated_root, migrated_repo, results_dir


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_folders:
        _print_folder_catalog()
        return 0

    if args.baseline_backend == "emulate" and args.migrated_backend != "emulate":
        parser.error("--baseline-backend emulate requires --migrated-backend emulate")
    if args.overrides and "emulate" not in (args.baseline_backend, args.migrated_backend):
        parser.error("--set only applies to emulate backends")

    scripts, baseline_root, baseline_repo, migrated_root, migrated_repo, results_dir = _resolve_run_config(args)

    if args.folder:
        print(f"Folder preset: {args.folder}")
        print(f"  migrated_root: {migrated_root}")
        print(f"  baseline_root: {baseline_root}")
        print(f"  results_dir:   {results_dir}")
        print()

    summaries: list[dict[str, Any]] = []
    failures: list[str] = []
    blocked: list[str] = []

    for script_name in scripts:
        print(f"Validating {script_name}...", flush=True)
        try:
            summary = validate_script(
                script_name=script_name,
                baseline_root=baseline_root,
                baseline_repo=baseline_repo,
                baseline_runner=args.baseline_runner,
                baseline_backend=args.baseline_backend,
                migrated_root=migrated_root,
                migrated_repo=migrated_repo,
                migrated_runner=args.migrated_runner,
                migrated_backend=args.migrated_backend,
                results_dir=results_dir,
                duration=args.duration,
                emulate_length_ns=args.emulate_length_ns,
                overrides=args.overrides,
            )
            summaries.append(summary)
            notes = format_notes(summary, results_dir)
            if summary.get("status") == "blocked":
                print(f"  BLOCKED: {notes}")
                blocked.append(script_name)
            else:
                status = "PASS" if summary["passed"] else "FAIL"
                print(f"  {status}: {notes}")
                if not summary["passed"]:
                    failures.append(script_name)
            if args.print_notes:
                print(f"  Notes: {notes}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}", file=sys.stderr)
            failures.append(script_name)

    aggregate = {
        "folder": args.folder,
        "baseline_backend": args.baseline_backend,
        "migrated_backend": args.migrated_backend,
        "overrides": list(args.overrides or []),
        "passed": len(failures) == 0,
        "scripts": summaries,
        "failures": failures,
        "blocked": blocked,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2) + "\n",
        encoding="utf-8",
    )

    if blocked:
        print(f"\nBlocked scripts (not yet migrated): {', '.join(blocked)}", file=sys.stderr)
    if failures:
        print(f"\nFailed scripts: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("\nAll non-blocked scripts passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
