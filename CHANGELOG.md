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
- QUA 1.3.1 / 1.4.0 migration guide ([docs/plans/qua-1.4.0-migration.md](docs/plans/qua-1.4.0-migration.md)), covering iterables, config split, `amp()` deprecation, program-queue `overrides` deprecation, and `measure()` ADC placeholder removal
- Auto-generated migrated-file inventory ([docs/plans/qua-1.4.0-migrated-files.md](docs/plans/qua-1.4.0-migrated-files.md))
- [AGENTS.md](AGENTS.md) at the repo root: the single source of rules for AI coding assistants (Cursor, Codex, Claude Code, Copilot, and others), covering QUA/QUAM/QUAlibrate context, changelog maintenance, the `scripts/README.md` catalog rule, and the migration-script checklist
- CI and static test gates: `test_qua_compile.py`, `test_config_split.py`, `test_no_deprecated_amp.py`, and [qualibration tests README](qualibration_graphs/superconducting/tests/README.md)
- Bulk migration scripts: `migrate_qca_qua_131.py`, `migrate_config_split.py`, `migrate_amp_to_amplitude_scale.py`, `migrate_measure_none.py`, `migrate_simulation_wait_until.py`, `generate_qua_migrated_files_inventory.py`
- Config-split helpers: `qua_config_split.py` (QCA and qualibration)
- `.python-version` pinning Python 3.14 for local development
- Simulation baseline validation harness ([scripts/validate_simulation_baseline.py](scripts/validate_simulation_baseline.py), [scripts/simulate_waveform_runner.py](scripts/simulate_waveform_runner.py), [scripts/validation_matrix.py](scripts/validation_matrix.py))
- Scripts catalog ([scripts/README.md](scripts/README.md)) and an agent rule to keep it in sync ([AGENTS.md](AGENTS.md))
- Emulator-based backend for the validation harness (QUA 2 branch): `--migrated-backend emulate` on [scripts/validate_simulation_baseline.py](scripts/validate_simulation_baseline.py) runs this repo's side through `QuaEmulator().emulate()` via new [scripts/emulate_waveform_runner.py](scripts/emulate_waveform_runner.py) instead of `qmm.simulate()`, comparing pulse-schedule structure; baseline (`../qua-libs`) is unchanged. Scripts not yet migrated to QUA 2 report a distinct `BLOCKED` status (with reason) instead of failing. `scripts/qca_script_loader.py` factors the shared script-prelude loader out of `simulate_waveform_runner.py` for reuse. Offline smoke test ([tests/test_qua2_emulate_smoke.py](tests/test_qua2_emulate_smoke.py) with fixture [tests/fixtures/qua2_emulate_smoke_program.py](tests/fixtures/qua2_emulate_smoke_program.py)) and CI job `qua2-emulate-smoke` validate the tooling without needing a real QUA-2-migrated QCA script or CS rack access. See [VALIDATION.md § QUA 2 branch](VALIDATION.md#qua-2-branch-emulator-based-validation-experimental) for current status and caveats
- CZ JAZZ-N / JAZZ2-N, leakage amplification, phase-compensation error-amp, and two-qubit RB calibration nodes from qua-libs `main`, migrated to QUA 1.3.1/1.4.0

### Changed

- Consolidated the Cursor rules into [AGENTS.md](AGENTS.md) so contributors using other AI tools follow the same rules; removed the always-applied `qua-documentation.mdc` and `changelog.mdc`, and kept the glob-scoped `migration-scripts.mdc` and `scripts-readme.mdc` as stubs pointing to `AGENTS.md`; the bootstrap kit now copies `AGENTS.md`
- Switched the QUA 2 branch's emulate-based validation backend from `qua-emulator==0.2.13` (`qua_emulator.QuaEmulator.emulate()`) to `qua-evaluator==1.0.4` (`qua_evaluator.QuaEvaluator.evaluate()`) in [scripts/emulate_waveform_runner.py](scripts/emulate_waveform_runner.py); added the `qop-models==0.1.2` dependency it requires; renamed the local wheel bundle directory `qua-emulator-0.2.13-delivery/` to `qua2-wheels/`
- Standardized CS rack targets across QCA `configuration*.py` files: OPX+ configs use **CS_1** (`172.16.33.101`); OPX1000 FEM configs use **CS_3** (`172.16.33.115`) with LF-FEM slots aligned to the rack (LF-only → 5, LF+Octave → 3); documented assignment in [VALIDATION.md](VALIDATION.md)
- Pointed simulation validation baseline to `qua-libs` branch **`QL-1212-validation`** (replacing `main` @ `30823059`); documented CS rack network prerequisites for `validate_simulation_baseline.py` in [VALIDATION.md](VALIDATION.md) and [AGENTS.md](AGENTS.md)
- Aligned `validation_matrix.py` script order with VALIDATION.md Results tables (alphabetical by filename)
- Updated migration runbook, migration guide, bootstrap manifest, and Cursor rules for `migrate_measure_none.py`, measure-None grep gate, and Superconducting simulation validation harness
- Generalized simulation baseline validation harness with `--folder` presets from VALIDATION.md ([scripts/validation_matrix.py](scripts/validation_matrix.py)); reran Single-Fixed-Transmon simulation baseline comparison (5 scripts, all pass)
- Changed VALIDATION.md script matrix to drop ≥90% duplicate flux-tunable scripts and add flux-specific / coupled-gate calibrations for more robust migration validation
- Completed 3D-storage-cavity simulation validation (5 scripts vs qua-libs baseline); documented dual runtime environments (`uv` migrated, Poetry baseline) in VALIDATION.md
- Extended migration guide with universal keep-manual rules, standalone QCA templates, and Part 2 completion status; migration scripts accept `--modality` / `--qca-root`
- Pinned `qm-qua==1.4.0`; bumped `qualibrate>=1.5.0` and Qiskit `>=2.3,<3.0`; extended `requires-python` to `<3.15`
- CI runs on Python 3.14
- Replaced deprecated `declare_stream()` with `declare_output_stream()` across QCA scripts and qualibration nodes
- Migrated QUA scripts to 1.3.1 iterables and auto-streaming (`QuaIterable`, `declare_with_stream`) and 1.4.0 config split / `amplitude_scale` (see [qua-1.4.0-migrated-files.md](docs/plans/qua-1.4.0-migrated-files.md))
- Split QUA configs into controller and logical parts (273 files): 32 `configuration*.py`, 193 QCA scripts, 40 qualibration nodes, and 2 tutorial files; simulation stays on `qmm.simulate(merged config)` without `open_qm`
- Updated documentation, Cursor rules, and CONTRIBUTING for qm-qua 1.4.0 and the config-split pattern
- Replaced deprecated QUA `amp()` pulse multiplication with `amplitude_scale` on `play`/`measure` across ~70 files (~150 occurrences): 68 QCA scripts, 4 shared `macros.py`, 2 qualibration files, 1 notebook, and 1 README; added `test_no_deprecated_amp.py` grep gate
- Reran simulation baseline validation for Single-Fixed-Transmon, 3D-storage-cavity, and Single-Flux-Tunable-Transmon (15 scripts, all pass vs existing VALIDATION.md counts); completed first Two-Fixed-Coupled-Transmons validation run (5 scripts, all pass)
- Completed Two-Flux-Tunable-Coupled-Transmons simulation validation (5 scripts, all pass vs qua-libs baseline); closes the 25-script Superconducting VALIDATION.md matrix
- Documented readout `amplitude_scale=None` vs `amplitude_scale=1` parity pitfall in migration guide and Cursor rules
- Merged qua-libs `main` superconducting calibrations; added `uncertainties>=3.2.2` and kept Qiskit `>=2.3,<3.0` for Python 3.14

### Fixed

- `scripts/qca_script_loader.py`'s `load_program_namespace()` now compiles the exec'd QCA-script prelude with `dont_inherit=True`, so its own `from __future__ import annotations` no longer leaks into scripts it loads. Without this, every annotation in an exec'd script was silently stringified (e.g. `def play_two(a: fixed)` became `a: "fixed"`), which broke qm-qua 2's `@shot` decorator (it requires a resolved concrete type annotation, not a string) — surfaced by `tests/test_qua2_emulate_smoke.py`
- Migrated `tests/fixtures/qua2_emulate_smoke_program.py` to actual QUA 2 config schema (`single_input`/`mix_inputs` + `imbalance_correction`, no top-level `mixers`) and annotated its `@shot` function parameter (`a: fixed`), so the fixture emulates cleanly instead of reporting `BLOCKED`
- `20_all_xy.py` migrated to the controller/logical config split (`split_qua_config`, `qm_session(qmm, controller_config, ...)`, `qm.execute(..., config=logical_config)`) and `declare_output_stream()` instead of deprecated `declare_stream()`, matching the pattern used by sibling calibration nodes
- Updated `test_qm_extensions_importable` to match verified `qm-qua==2.0.0.dev19` behavior: unlike the earlier `2.0.0.dev5` dev build, `dev19` still ships `qm.qua.extensions` (`QuaIterable`/`QuaIterableRange`) and top-level `declare_with_stream` as a transitional compatibility shim alongside `@shot`, so the test no longer asserts `ModuleNotFoundError` for major version ≥2
- Test gates that assumed the QUA 1.4.0 API now work under `qm-qua 2.0.0.dev5`: `test_qm_extensions_importable` asserts the API surface for the installed qm-qua major version (2.0 removed `qm.qua.extensions.QuaIterable` / `declare_with_stream` and added `@shot`), and `test_simulate_hello_qua_with_merged_split_config` builds its sweep with the version-appropriate `for_` signature and skips when the folder's `configuration.py` is not yet QUA 2 schema
- Two-Flux-Tunable-Coupled-Transmons validation fixes: readout parity (`amplitude_scale=1` on inline `measure` in `08_qubit_spectroscopy_vs_flux_simultaneous.py` and `21_CZ.py`); nested 2D sweep streaming in `06_resonator_spectroscopy_vs_amplitude.py` (manual `qua_declaration` saves + stream buffers alongside iterables)
- Two-Fixed-Coupled-Transmons extended simulation audit (~22 scripts): readout parity (`amplitude_scale=1` / `multiplexed_readout`), streaming/iterable migration fixes, and `12_T1` pulse-order correction; 21/22 pass vs baseline (`19a` non-parity: baseline uses localhost/mw_fem config)
- Added `job.wait_until("Done")` before simulation result pulls in 3 Two-Fixed OPX1000 scripts; `simulate_waveform_runner.py` waits only for OPX1000 configs; grep gate `test_simulation_wait_until_before_samples_in_opx1000_qca`
- Restored missing `update_frequency` calls in Single-Flux `05b_resonator_spectroscopy_vs_flux.py` and `06b_qubit_spectroscopy_vs_flux.py` (iterables migration regression); documented Single-Flux-Tunable-Transmon simulation validation (5 scripts, all pass) in VALIDATION.md
- Removed deprecated `measure(..., None, ...)` ADC-stream placeholder across Superconducting QCA scripts (~142 files); real ADC streaming calls (`adc_st`, etc.) unchanged; added `test_no_measure_none_adc_placeholder_in_qca` grep gate
- Fixed duplicate QUA output stream tags in 10 Superconducting QCA scripts where `declare_with_stream` overlapped legacy manual `.save()` tags; added a migration grep gate
- Fixed 3D-storage-cavity scripts that used `declare_with_stream(bool, ..., average_axes=...)` (simulation error: average can't operate on bool items); state streams now use `int`, matching upstream `boolean_to_int().average()` behavior; `readout_macro` stores 0/1 for int or bool state variables
- Fixed `09_swapping.py` missing `save(state, state_st)` after readout (empty stream compile error under iterables + manual `state_st`)
- Cast frequency/detuning sweep arrays to `.astype(int)` before `QuaIterable` when used with `update_frequency` (~60 QCA scripts and qualibration nodes); fixes simulation compile error `Expected type int but got fixed`
- `test_calibration_module_imports` no longer fails in CI: [`conftest.py`](qualibration_graphs/superconducting/tests/conftest.py) stubs QualibrationNode run-actions and hardware I/O during module import checks; redirects `Quam.load()` to the calibration package dir so repo-root pytest runs do not pick up incompatible QUAM state files

### Deprecated

- Transitional merged `config` alias in configuration files (kept for simulation and data export until a follow-up removal)

