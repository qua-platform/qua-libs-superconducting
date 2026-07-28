#!/usr/bin/env python3
"""Generate docs/plans/qua-1.3.1-migrated-files.md from git history."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "135a164^"
DEFAULT_HEAD = "21fced8"
OUTPUT_PATH = REPO_ROOT / "docs" / "plans" / "qua-1.3.1-migrated-files.md"
MIGRATION_GUIDE = "qua-1.3.1-migration.md"


def group_key(rel: str) -> str:
    """Return a folder section key for a repo-relative path."""
    parts = Path(rel).parts
    if parts[0] == "Quantum-Control-Applications" and len(parts) >= 3:
        return "/".join(parts[:3])
    if parts[0] == "qualibration_graphs" and len(parts) >= 4:
        return "/".join(parts[:4])
    if parts[0] == "qualibration_graphs" and len(parts) >= 3:
        return "/".join(parts[:3])
    return parts[0]


def section_title(group: str) -> str:
    return group.replace("/", " / ")


def git_changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}", "--", "*.py"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git diff failed for {base}..{head}")
    return sorted(line for line in result.stdout.splitlines() if line)


def render_markdown(changed_files: list[str], base: str, head: str) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for rel in changed_files:
        groups[group_key(rel)].append(rel)

    lines = [
        "# QUA 1.3.1 migrated Python files",
        "",
        "> Auto-generated — do not edit by hand. Regenerate with:",
        "> `uv run python scripts/generate_qua_131_inventory.py`",
        "",
        "Inventory of Python files updated during the QUA 1.3.1 migration "
        "(new streaming API and/or QUA iterables). "
        f"See [{MIGRATION_GUIDE}]({MIGRATION_GUIDE}) for migration patterns and rationale.",
        "",
        "## Summary",
        "",
        f"- Total files: {len(changed_files)}",
        f"- Migration commits: `{base}` … `{head}`",
        "",
    ]

    for group in sorted(groups):
        files = groups[group]
        lines.append(f"## {section_title(group)} ({len(files)})")
        lines.append("")
        for rel in sorted(files, key=lambda path: Path(path).name):
            name = Path(rel).name
            lines.append(f"- [`{name}`](../../{rel})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"Git base ref (default: {DEFAULT_BASE})")
    parser.add_argument("--head", default=DEFAULT_HEAD, help=f"Git head ref (default: {DEFAULT_HEAD})")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output markdown path (default: {OUTPUT_PATH.relative_to(REPO_ROOT)})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        changed_files = git_changed_files(args.base, args.head)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not changed_files:
        print("No changed Python files found for the given git range.", file=sys.stderr)
        return 1

    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(changed_files, args.base, args.head), encoding="utf-8")

    print(f"Wrote {len(changed_files)} files to {output_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
