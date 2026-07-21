#!/usr/bin/env python3
"""Migrate Quantum-Control-Applications QUA scripts to qm-qua 1.3.1."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QCA_ROOT = REPO_ROOT / "Quantum-Control-Applications" / "Superconducting"

PRIORITY_FOLDERS = [
    "Single-Fixed-Transmon",
    "Single-Flux-Tunable-Transmon",
    "Two-Fixed-Coupled-Transmons",
    "Two-Flux-Tunable-Coupled-Transmons/Standard Configuration",
    "3D-storage-cavity",
]

SKIP_NAME_PATTERNS = (
    re.compile(r"RB", re.IGNORECASE),
    re.compile(r"randomized_benchmarking", re.IGNORECASE),
    re.compile(r"tomography", re.IGNORECASE),
    re.compile(r"IQ_blobs", re.IGNORECASE),
    re.compile(r"cryoscope", re.IGNORECASE),
    re.compile(r"frequency_tracking", re.IGNORECASE),
)

SIMPLE_DECL_BLOCK = re.compile(
    r"^    n = declare\(int\)[^\n]*\n"
    r"^    (?P<sweep_var>\w+) = declare\(int\)[^\n]*\n"
    r"^    I = declare\(fixed\)[^\n]*\n"
    r"^    Q = declare\(fixed\)[^\n]*\n"
    r"^    I_st = declare_(?:output_)?stream\(\)[^\n]*\n"
    r"^    Q_st = declare_(?:output_)?stream\(\)[^\n]*\n"
    r"^    n_st = declare_(?:output_)?stream\(\)[^\n]*\n",
    re.MULTILINE,
)

OUTER_LOOP = re.compile(
    r"^    with for_\(n, 0, n < (?P<n_avg>\w+), n \+ 1\):[^\n]*\n"
    r"^        with for_\(\*from_array\((?P<sweep_var>\w+), (?P<sweep_array>\w+)\)\):[^\n]*\n",
    re.MULTILINE,
)

STREAM_IQ = re.compile(
    r"^        I_st\.buffer\(len\((?P<sweep_array>\w+)\)\)\.average\(\)\.save\(\"I\"\)[^\n]*\n"
    r"^        Q_st\.buffer\(len\(\w+\)\)\.average\(\)\.save\(\"Q\"\)[^\n]*\n",
    re.MULTILINE,
)


@dataclass
class MigrationReport:
    changed_files: list[Path] = field(default_factory=list)
    iterables_files: list[Path] = field(default_factory=list)
    compat_only_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def ordered_folders() -> list[Path]:
    """Return migration folders in rollout order, de-duplicated."""
    folders: list[Path] = []
    processed_dirs: set[Path] = set()

    def add_folder(path: Path) -> None:
        resolved = path.resolve()
        if not path.is_dir() or resolved in processed_dirs:
            return
        folders.append(path)
        processed_dirs.add(resolved)
        for child in path.rglob("*"):
            if child.is_dir():
                processed_dirs.add(child.resolve())

    for rel in PRIORITY_FOLDERS:
        add_folder(QCA_ROOT / rel)

    for folder in sorted(QCA_ROOT.rglob("*")):
        if not folder.is_dir() or folder.resolve() == QCA_ROOT.resolve():
            continue
        if folder.resolve() in processed_dirs:
            continue
        if any(parent.resolve() in processed_dirs for parent in folder.parents if parent != QCA_ROOT):
            continue
        add_folder(folder)

    return folders


def find_qua_program_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(folder.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            continue
        if "with program()" in text:
            files.append(path)
    return files


def path_is_complex(path: Path) -> bool:
    path_str = str(path)
    return any(pattern.search(path_str) for pattern in SKIP_NAME_PATTERNS)


def content_is_complex(content: str) -> bool:
    return ".save_all(" in content or "boolean_to_int" in content


def rename_declare_stream(content: str) -> str:
    return content.replace("declare_stream(", "declare_output_stream(")


def ensure_extensions_import(content: str) -> str:
    import_line = "from qm.qua.extensions import QuaIterable, QuaIterableRange\n"
    if import_line in content:
        return content
    match = re.search(r"^from qm\.qua import .*\n", content, re.MULTILINE)
    if match:
        insert_at = match.end()
        return content[:insert_at] + import_line + content[insert_at:]
    return import_line + content


def detect_simple_sweep(content: str) -> dict[str, str] | None:
    if "with program()" not in content:
        return None
    if content.count("with for_(*from_array(") != 1:
        return None
    if re.search(r"I = \[declare\(fixed\)", content):
        return None
    if re.search(r"I_st = \[declare_", content):
        return None
    if "state_st" in content:
        return None
    if re.search(r"^    \w+ = declare\(bool\)", content, re.MULTILINE):
        return None
    decl = SIMPLE_DECL_BLOCK.search(content)
    outer = OUTER_LOOP.search(content)
    stream = STREAM_IQ.search(content)
    if not (decl and outer and stream):
        return None
    if decl.group("sweep_var") != outer.group("sweep_var"):
        return None
    if outer.group("sweep_array") != stream.group("sweep_array"):
        return None
    if re.search(
        r"with stream_processing\(\):\n(?:[^\n]*\n)*?        if ",
        content,
    ):
        return None
    return {
        "sweep_var": outer.group("sweep_var"),
        "sweep_array": outer.group("sweep_array"),
        "n_avg": outer.group("n_avg"),
    }


def replace_declarations(content: str, info: dict[str, str]) -> str:
    sweep_var = info["sweep_var"]
    sweep_array = info["sweep_array"]
    n_avg = info["n_avg"]
    replacement = (
        f'    shots = QuaIterableRange("shots", {n_avg})\n'
        f'    {sweep_var}_sweep = QuaIterable("{sweep_var}", {sweep_array})\n'
        "    n = declare(int)  # QUA variable for the averaging loop\n"
        "    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'\n"
    )
    return SIMPLE_DECL_BLOCK.sub(replacement, content, count=1)


def replace_loops(content: str, info: dict[str, str]) -> str:
    sweep_var = info["sweep_var"]
    start = OUTER_LOOP.search(content)
    if not start:
        raise ValueError("outer loop not found")
    line_start = start.start()
    lines = content[line_start:].splitlines(keepends=True)
    body_lines: list[str] = []
    idx = 2  # skip outer and inner for headers
    end_idx = line_start
    while idx < len(lines):
        line = lines[idx]
        if re.match(r"^            save\(I, I_st\)", line):
            idx += 1
            if idx < len(lines) and re.match(r"^            save\(Q, Q_st\)", lines[idx]):
                idx += 1
            continue
        if re.match(r"^        save\(n, n_st\)", line):
            idx += 1
            break
        if line.startswith("            "):
            body_lines.append(line)
        elif re.match(r"^        #", line):
            idx += 1
            continue
        elif line.startswith("        ") and not line.startswith("            "):
            break
        idx += 1
    body = "".join(body_lines)
    new_loop = (
        f"    for shot in shots:\n"
        f"        assign(n, shot)\n"
        f"        save(n, n_st)\n"
        f"        for {sweep_var} in {sweep_var}_sweep:\n"
        f'            I = declare_with_stream(fixed, "I", average_axes=["shots"])\n'
        f'            Q = declare_with_stream(fixed, "Q", average_axes=["shots"])\n'
        f"{body}"
    )
    for line in lines[:idx]:
        end_idx += len(line)
    return content[:line_start] + new_loop + content[end_idx:]


def simplify_stream_processing(content: str, sweep_array: str) -> str:
    content = re.sub(
        rf"^        I_st\.buffer\(len\({re.escape(sweep_array)}\)\)\.average\(\)\.save\(\"I\"\)[^\n]*\n",
        "",
        content,
        flags=re.MULTILINE,
    )
    content = re.sub(
        rf"^        Q_st\.buffer\(len\({re.escape(sweep_array)}\)\)\.average\(\)\.save\(\"Q\"\)[^\n]*\n",
        "",
        content,
        flags=re.MULTILINE,
    )
    return content


def migrate_iterables(content: str, info: dict[str, str]) -> str:
    content = replace_declarations(content, info)
    content = replace_loops(content, info)
    content = simplify_stream_processing(content, info["sweep_array"])
    content = ensure_extensions_import(content)
    content = re.sub(
        r"(for shot in shots:\n(?:.*\n)*?        for \w+ in \w+_sweep:\n(?:.*\n)*?)"
        r"        save\(n, n_st\)\n(\n    with stream_processing\(\):)",
        r"\1\2",
        content,
        count=1,
    )
    return content


def migrate_file(path: Path, report: MigrationReport, dry_run: bool = False) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.errors.append(f"{path}: read failed: {exc}")
        return False

    updated = rename_declare_stream(original)
    applied_iterables = False
    complex_path = path_is_complex(path)
    complex_content = content_is_complex(original)

    if not complex_path and not complex_content:
        info = detect_simple_sweep(updated)
        if info is not None:
            try:
                updated = migrate_iterables(updated, info)
                applied_iterables = True
            except Exception as exc:  # noqa: BLE001 - collect and continue
                report.errors.append(f"{path}: iterables migration failed: {exc}")

    if updated == original:
        if complex_path or complex_content:
            report.skipped_files.append(path)
        return False

    if dry_run:
        print(f"Would update: {path}" + (" [iterables]" if applied_iterables else " [compat]"))
    else:
        path.write_text(updated, encoding="utf-8")

    report.changed_files.append(path)
    if applied_iterables:
        report.iterables_files.append(path)
    else:
        report.compat_only_files.append(path)
    return True


def migrate_macros(
    folder: Path,
    report: MigrationReport,
    processed_files: set[Path],
    dry_run: bool = False,
) -> None:
    for path in sorted(folder.rglob("macros.py")):
        if path.resolve() in processed_files:
            continue
        processed_files.add(path.resolve())
        try:
            original = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.errors.append(f"{path}: read failed: {exc}")
            continue
        if "declare_stream(" not in original:
            continue
        updated = rename_declare_stream(original)
        if updated == original:
            continue
        if dry_run:
            print(f"Would update macros: {path}")
        else:
            path.write_text(updated, encoding="utf-8")
        report.changed_files.append(path)
        report.compat_only_files.append(path)


def migrate_folder(
    folder: Path,
    report: MigrationReport,
    processed_files: set[Path],
    dry_run: bool = False,
) -> None:
    if not folder.is_dir():
        report.errors.append(f"Folder not found: {folder}")
        return
    migrate_macros(folder, report, processed_files, dry_run=dry_run)
    for path in find_qua_program_files(folder):
        if path.resolve() in processed_files:
            continue
        processed_files.add(path.resolve())
        migrate_file(path, report, dry_run=dry_run)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        action="append",
        dest="folders",
        help="Restrict migration to one or more folders under Superconducting/ (relative path).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = MigrationReport()
    processed_files: set[Path] = set()

    if args.folders:
        folders = [QCA_ROOT / rel for rel in args.folders]
    else:
        folders = ordered_folders()

    for folder in folders:
        rel = folder.relative_to(QCA_ROOT) if folder.is_relative_to(QCA_ROOT) else folder
        print(f"Migrating {rel}...")
        migrate_folder(folder, report, processed_files, dry_run=args.dry_run)

    print("\n=== Migration summary ===")
    print(f"Changed files: {len(report.changed_files)}")
    print(f"  Iterables migration: {len(report.iterables_files)}")
    print(f"  Compat rename only: {len(report.compat_only_files)}")
    print(f"Skipped (complex / unchanged): {len(report.skipped_files)}")
    if report.errors:
        print(f"Errors: {len(report.errors)}")
        for err in report.errors:
            print(f"  - {err}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
