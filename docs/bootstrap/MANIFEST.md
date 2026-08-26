# Bootstrap manifest — new QCA modality repository

Copy these paths from **qua-libs-superconducting** when spinning up a modality fork (e.g. `qua-libs-amo`, `qua-libs-quantum-dots`).

## Quick start

```bash
# Run from qua-libs-superconducting repo root
./scripts/bootstrap_modality_repo.sh AMO ../qua-libs-amo
```

Edit `../qua-libs-amo/.cursor/rules/qua-documentation.mdc` (modality name), adapt `pyproject.toml` / `README.md`, then follow [qua-1.4.0-migration-runbook.md](../plans/qua-1.4.0-migration-runbook.md).

## Files to copy from qua-libs-superconducting

| Path | Purpose |
|------|---------|
| `docs/plans/qua-1.4.0-migration.md` | API reference & templates |
| `docs/plans/qua-1.4.0-migration-runbook.md` | Executable playbook |
| `docs/bootstrap/MANIFEST.md` | This file |
| `scripts/migration_paths.py` | Shared CLI path resolution |
| `scripts/migrate_amp_to_amplitude_scale.py` | Part 3 bulk migration |
| `scripts/migrate_config_split.py` | Part 2 bulk migration |
| `scripts/migrate_qca_qua_131.py` | Part 1 bulk migration |
| `scripts/migrate_measure_none.py` | Part 5 bulk migration |
| `scripts/migrate_simulation_wait_until.py` | Part 6 bulk migration — OPX1000 simulation async wait |
| `scripts/generate_qua_migrated_files_inventory.py` | Optional inventory generator |
| `scripts/bootstrap_modality_repo.sh` | This bootstrap script |
| `scripts/README.md` | Catalog of scripts in this directory |

**Optional (Superconducting reference repo only):** `scripts/validate_simulation_baseline.py`, `scripts/validation_matrix.py`, `scripts/simulate_waveform_runner.py`, `scripts/emulate_waveform_runner.py`, `scripts/qca_script_loader.py` — automated waveform/schedule baseline comparison; the `simulate_waveform_runner.py` side requires sibling `../qua-libs` and CS rack access, the `emulate_waveform_runner.py` side (QUA 2 branch) does not.
| `Quantum-Control-Applications/Superconducting/qua_config_split.py` | → `{Modality}/qua_config_split.py` |
| `tests/test_qca_migration_gates.py` | Portable CI grep gates |
| `.cursor/rules/qua-documentation.mdc` | Cursor QUA context (edit modality) |
| `.cursor/rules/changelog.mdc` | Changelog rule |
| `.cursor/rules/migration-scripts.mdc` | Checklist when adding `scripts/migrate_*.py` |
| `.cursor/rules/scripts-readme.mdc` | Keep `scripts/README.md` in sync when scripts change |
| `.github/workflows/ci.yml` | Adapt: drop qualibration jobs if N/A |
| `CONTRIBUTING.md` | Adapt intro + migration links |
| `CHANGELOG.md` | Empty `[Unreleased]` skeleton or copy structure |

## After bootstrap

1. `uv sync`
2. Set `QCA_MODALITY={Modality}` in CI and locally
3. Pre-migration audit (runbook section C)
4. Migration execution (runbook section D)
