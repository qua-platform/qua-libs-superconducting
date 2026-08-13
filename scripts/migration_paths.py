"""Shared path resolution for QUA migration scripts (all QCA modalities)."""

from __future__ import annotations

import os
from pathlib import Path

MODALITIES = (
    "Superconducting",
    "Quantum-Dots",
    "Optically addressable spin qubits",
    "AMO",
)
DEFAULT_MODALITY = "Superconducting"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_modality(explicit: str | None = None) -> str:
    """Modality name from CLI, env ``QCA_MODALITY``, or default."""
    return explicit or os.environ.get("QCA_MODALITY") or DEFAULT_MODALITY


def resolve_qca_root(
    *,
    modality: str | None = None,
    qca_root: Path | str | None = None,
    repo: Path | None = None,
) -> Path:
    """Return the QCA tree root (e.g. ``Quantum-Control-Applications/Superconducting``)."""
    if qca_root is not None:
        path = Path(qca_root).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"QCA root not found: {path}")
        return path
    root = repo or repo_root()
    name = resolve_modality(modality)
    path = root / "Quantum-Control-Applications" / name
    if not path.is_dir():
        raise FileNotFoundError(
            f"Modality folder not found: {path}\n"
            f"Expected one of {MODALITIES!r} under Quantum-Control-Applications/"
        )
    return path


def modality_anchor(config_path: Path) -> Path:
    """Directory containing ``qua_config_split.py`` for imports from configuration files."""
    for parent in config_path.parents:
        if (parent / "qua_config_split.py").is_file():
            return parent
        if parent.parent.name == "Quantum-Control-Applications":
            return parent
    raise ValueError(f"No modality anchor for {config_path}")


def add_modality_args(parser) -> None:
    """Register ``--modality`` and ``--qca-root`` on an argparse parser."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--modality",
        choices=MODALITIES,
        default=None,
        help=f"QCA modality under Quantum-Control-Applications/ (default: {DEFAULT_MODALITY} or $QCA_MODALITY).",
    )
    group.add_argument(
        "--qca-root",
        type=Path,
        default=None,
        help="Explicit path to the modality folder (overrides --modality).",
    )
