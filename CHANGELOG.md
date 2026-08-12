# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- QUA 1.3.1 migration guide ([docs/plans/qua-1.3.1-migration.md](docs/plans/qua-1.3.1-migration.md))
- Auto-generated migrated-file inventory ([docs/plans/qua-1.3.1-migrated-files.md](docs/plans/qua-1.3.1-migrated-files.md), 225 files)
- Cursor rules for QUA, QUAM, and QUAlibrate ([.cursor/rules/qua-documentation.mdc](.cursor/rules/qua-documentation.mdc))
- CI and static test gates: `test_qua_compile.py`, `test_config_split.py`, `test_no_deprecated_amp.py`, and [qualibration tests README](qualibration_graphs/superconducting/tests/README.md)
- Bulk migration scripts: `migrate_qca_qua_131.py`, `migrate_config_split.py`, `migrate_amp_to_amplitude_scale.py`, `generate_qua_131_inventory.py`
- Config-split helpers: `qua_config_split.py` (QCA and qualibration)
- `.python-version` pinning Python 3.14 for local development

### Changed

- Pinned `qm-qua==1.4.0`; bumped `qualibrate>=1.5.0` and Qiskit `>=2.3,<3.0`; extended `requires-python` to `<3.15`
- CI runs on Python 3.14
- Replaced deprecated `declare_stream()` with `declare_output_stream()` across QCA scripts and qualibration nodes
- Migrated 225 files to QUA 1.3.1 iterables and auto-streaming (`QuaIterable`, `declare_with_stream`): 186 QCA, 35 qualibration calibrations, 2 qualibration support files, 1 tutorial, 1 script (see [qua-1.3.1-migrated-files.md](docs/plans/qua-1.3.1-migrated-files.md))
- Split QUA configs into controller and logical parts (273 files): 32 `configuration*.py`, 193 QCA scripts, 40 qualibration nodes, and 2 tutorial files; simulation stays on `qmm.simulate(merged config)` without `open_qm`
- Updated documentation, Cursor rules, and CONTRIBUTING for qm-qua 1.4.0 and the config-split pattern
- Replaced deprecated QUA `amp()` pulse multiplication with `amplitude_scale` on `play`/`measure` across ~70 files (~150 occurrences): 68 QCA scripts, 4 shared `macros.py`, 2 qualibration files, 1 notebook, and 1 README; added `test_no_deprecated_amp.py` grep gate

### Deprecated

- Transitional merged `config` alias in configuration files (kept for simulation and data export until a follow-up removal)

