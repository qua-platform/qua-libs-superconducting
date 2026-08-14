# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- QUA 1.3.1 / 1.4.0 migration runbook ([docs/plans/qua-1.4.0-migration-runbook.md](docs/plans/qua-1.4.0-migration-runbook.md)) — step-by-step playbook for all QCA modalities, repo bootstrap, and pre-AI checklist
- Modality fork bootstrap manifest ([docs/bootstrap/MANIFEST.md](docs/bootstrap/MANIFEST.md)) and `scripts/bootstrap_modality_repo.sh`
- Portable QCA migration grep gates ([tests/test_qca_migration_gates.py](tests/test_qca_migration_gates.py)); CI job `qca-migration-gates`
- `scripts/migration_paths.py` — shared `--modality` / `--qca-root` resolution for bulk migration scripts
- QUA 1.3.1 / 1.4.0 migration guide ([docs/plans/qua-1.4.0-migration.md](docs/plans/qua-1.4.0-migration.md)), covering iterables, config split, `amp()` deprecation, and program-queue `overrides` deprecation
- Auto-generated migrated-file inventory ([docs/plans/qua-1.4.0-migrated-files.md](docs/plans/qua-1.4.0-migrated-files.md))
- Cursor rules for QUA, QUAM, and QUAlibrate ([.cursor/rules/qua-documentation.mdc](.cursor/rules/qua-documentation.mdc))
- CI and static test gates: `test_qua_compile.py`, `test_config_split.py`, `test_no_deprecated_amp.py`, and [qualibration tests README](qualibration_graphs/superconducting/tests/README.md)
- Bulk migration scripts: `migrate_qca_qua_131.py`, `migrate_config_split.py`, `migrate_amp_to_amplitude_scale.py`, `generate_qua_migrated_files_inventory.py`
- Config-split helpers: `qua_config_split.py` (QCA and qualibration)
- `.python-version` pinning Python 3.14 for local development

### Changed

- Changed VALIDATION.md script matrix to drop ≥90% duplicate flux-tunable scripts and add flux-specific / coupled-gate calibrations for more robust migration validation
- Extended migration guide with universal keep-manual rules, standalone QCA templates, and Part 2 completion status; migration scripts accept `--modality` / `--qca-root`
- Pinned `qm-qua==1.4.0`; bumped `qualibrate>=1.5.0` and Qiskit `>=2.3,<3.0`; extended `requires-python` to `<3.15`
- CI runs on Python 3.14
- Replaced deprecated `declare_stream()` with `declare_output_stream()` across QCA scripts and qualibration nodes
- Migrated QUA scripts to 1.3.1 iterables and auto-streaming (`QuaIterable`, `declare_with_stream`) and 1.4.0 config split / `amplitude_scale` (see [qua-1.4.0-migrated-files.md](docs/plans/qua-1.4.0-migrated-files.md))
- Split QUA configs into controller and logical parts (273 files): 32 `configuration*.py`, 193 QCA scripts, 40 qualibration nodes, and 2 tutorial files; simulation stays on `qmm.simulate(merged config)` without `open_qm`
- Updated documentation, Cursor rules, and CONTRIBUTING for qm-qua 1.4.0 and the config-split pattern
- Replaced deprecated QUA `amp()` pulse multiplication with `amplitude_scale` on `play`/`measure` across ~70 files (~150 occurrences): 68 QCA scripts, 4 shared `macros.py`, 2 qualibration files, 1 notebook, and 1 README; added `test_no_deprecated_amp.py` grep gate

### Fixed

- Fixed duplicate QUA output stream tags in 10 Superconducting QCA scripts where `declare_with_stream` overlapped legacy manual `.save()` tags; added a migration grep gate
- Fixed 3D-storage-cavity scripts that used `declare_with_stream(bool, ..., average_axes=...)` (simulation error: average can't operate on bool items); state streams now use `int`, matching upstream `boolean_to_int().average()` behavior; `readout_macro` stores 0/1 for int or bool state variables
- Cast frequency/detuning sweep arrays to `.astype(int)` before `QuaIterable` when used with `update_frequency` (~60 QCA scripts and qualibration nodes); fixes simulation compile error `Expected type int but got fixed`
- `test_calibration_module_imports` no longer fails in CI: [`conftest.py`](qualibration_graphs/superconducting/tests/conftest.py) stubs QualibrationNode run-actions and hardware I/O during module import checks; redirects `Quam.load()` to the calibration package dir so repo-root pytest runs do not pick up incompatible QUAM state files

### Deprecated

- Transitional merged `config` alias in configuration files (kept for simulation and data export until a follow-up removal)

