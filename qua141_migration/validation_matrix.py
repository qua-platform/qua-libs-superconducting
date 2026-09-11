"""VALIDATION.md folder presets for simulation baseline comparison.

Per-folder ``scripts`` order matches VALIDATION.md Results tables (alphabetical by filename).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QCA_MODALITY = "Superconducting"


@dataclass(frozen=True)
class ValidationFolder:
    qca_subpath: str
    scripts: tuple[str, ...]


VALIDATION_FOLDERS: dict[str, ValidationFolder] = {
    "Single-Fixed-Transmon": ValidationFolder(
        qca_subpath="Single-Fixed-Transmon",
        scripts=(
            "00_hello_qua.py",
            "04a_resonator_spectroscopy.py",
            "05_resonator_spectroscopy_vs_amplitude.py",
            "08b_power_rabi.py",
            "08c_power_rabi_error_amplification.py",
        ),
    ),
    "3D-storage-cavity": ValidationFolder(
        qca_subpath="3D-storage-cavity",
        scripts=(
            "00_selective_pulse_power_rabi.py",
            "01_storage_spectroscopy.py",
            "03a_number_splitting_spectroscopy_w_displacement.py",
            "06a_qubit_AC_Stark_shift_from_readout_pumping.py",
            "09_swapping.py",
        ),
    ),
    "Single-Flux-Tunable-Transmon": ValidationFolder(
        qca_subpath="Single-Flux-Tunable-Transmon",
        scripts=(
            "05b_resonator_spectroscopy_vs_flux.py",
            "06b_qubit_spectroscopy_vs_flux.py",
            "07a_rabi_chevron_duration.py",
            "07b_rabi_chevron_amplitude.py",
            "08a_time_rabi.py",
        ),
    ),
    "Two-Fixed-Coupled-Transmons": ValidationFolder(
        qca_subpath="Two-Fixed-Coupled-Transmons",
        scripts=(
            "00_hello_qua.py",
            "03_resonator_spectroscopy_single.py",
            "04_resonator_spectroscopy_multiplexed.py",
            "05_resonator_spectroscopy_vs_amplitude.py",
            "08_power_rabi.py",
        ),
    ),
    "Two-Flux-Tunable-Coupled-Transmons": ValidationFolder(
        qca_subpath="Two-Flux-Tunable-Coupled-Transmons/Standard Configuration",
        scripts=(
            "04_resonator_spectroscopy_single.py",
            "05_resonator_spectroscopy_multiplexed.py",
            "06_resonator_spectroscopy_vs_amplitude.py",
            "08_qubit_spectroscopy_vs_flux_simultaneous.py",
            "21_CZ.py",
        ),
    ),
}


def list_folders() -> list[str]:
    return sorted(VALIDATION_FOLDERS.keys())


def get_folder(folder_key: str) -> ValidationFolder:
    try:
        return VALIDATION_FOLDERS[folder_key]
    except KeyError as exc:
        known = ", ".join(list_folders())
        raise KeyError(f"Unknown folder {folder_key!r}. Known folders: {known}") from exc


def default_baseline_repo(repo_root: Path | None = None) -> Path:
    root = repo_root or REPO_ROOT
    return (root / ".." / "qua-libs").resolve()


def qca_path(repo_root: Path, qca_subpath: str) -> Path:
    return repo_root / "Quantum-Control-Applications" / QCA_MODALITY / qca_subpath


def results_slug(folder_key: str) -> str:
    return folder_key.replace("/", "-")


@dataclass(frozen=True)
class ResolvedValidationPaths:
    folder_key: str
    scripts: tuple[str, ...]
    migrated_root: Path
    baseline_root: Path
    results_dir: Path


def resolve_paths(
    folder_key: str,
    *,
    repo_root: Path | None = None,
    baseline_repo: Path | None = None,
) -> ResolvedValidationPaths:
    folder = get_folder(folder_key)
    root = (repo_root or REPO_ROOT).resolve()
    baseline = (baseline_repo or default_baseline_repo(root)).resolve()
    slug = results_slug(folder_key)
    return ResolvedValidationPaths(
        folder_key=folder_key,
        scripts=folder.scripts,
        migrated_root=qca_path(root, folder.qca_subpath),
        baseline_root=qca_path(baseline, folder.qca_subpath),
        results_dir=root / "qua141_migration" / "validation_results" / slug,
    )
