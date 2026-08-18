# Scripts

Tooling for QUA 1.3.1 / 1.4.0 migration, modality-repo bootstrap, and Superconducting simulation validation.

Run Python tools from the **repo root** with `uv run python scripts/<name>.py` unless noted. Bulk migrators accept `--modality` / `--qca-root` (or `$QCA_MODALITY`) via [`migration_paths.py`](migration_paths.py). Prefer `--dry-run` before applying.

Related docs: [migration runbook](../docs/plans/qua-1.4.0-migration-runbook.md), [migration guide](../docs/plans/qua-1.4.0-migration.md), [VALIDATION.md](../VALIDATION.md), [bootstrap manifest](../docs/bootstrap/MANIFEST.md).

## Shared helper

### [`migration_paths.py`](migration_paths.py)

Shared `--modality` / `--qca-root` / `$QCA_MODALITY` resolution for bulk migration scripts. Not a standalone CLI.

## Migration (all modalities)

Execution order and flags: [runbook section D](../docs/plans/qua-1.4.0-migration-runbook.md).

### [`migrate_amp_to_amplitude_scale.py`](migrate_amp_to_amplitude_scale.py)

Part 3 — replace deprecated `pulse * amp(...)` with `amplitude_scale=` on `play` / `measure`.

```
uv run python scripts/migrate_amp_to_amplitude_scale.py --modality Superconducting --dry-run
uv run python scripts/migrate_amp_to_amplitude_scale.py --modality Superconducting
```

`--skip-qualibration` limits the scan to the QCA modality tree.

### [`migrate_config_split.py`](migrate_config_split.py)

Part 2 — split QUA configs into controller / logical parts and update `open_qm` / `execute` / `simulate` call sites.

```
uv run python scripts/migrate_config_split.py --modality Superconducting
```

`--skip-qualibration` skips `qualibration_graphs` nodes (modality-only repos).

### [`migrate_qca_qua_131.py`](migrate_qca_qua_131.py)

Part 1 — simple 1D iterables and auto-streaming (`QuaIterable`, `declare_with_stream`). Optional `--folder` restricts the scan.

```
uv run python scripts/migrate_qca_qua_131.py --modality Superconducting --dry-run
uv run python scripts/migrate_qca_qua_131.py --modality Superconducting --folder Single-Fixed-Transmon --dry-run
```

### [`migrate_measure_none.py`](migrate_measure_none.py)

Part 5 — remove literal `None` as the ADC-stream placeholder in `measure()`.

```
uv run python scripts/migrate_measure_none.py --modality Superconducting --dry-run
uv run python scripts/migrate_measure_none.py --modality Superconducting
```

### [`migrate_simulation_wait_until.py`](migrate_simulation_wait_until.py)

Part 6 — insert `job.wait_until("Done")` after `qmm.simulate()` for OPX1000/FEM configs only.

```
uv run python scripts/migrate_simulation_wait_until.py --modality Superconducting --dry-run
uv run python scripts/migrate_simulation_wait_until.py --modality Superconducting
```

## Inventory

### [`generate_qua_migrated_files_inventory.py`](generate_qua_migrated_files_inventory.py)

Writes [`docs/plans/qua-1.4.0-migrated-files.md`](../docs/plans/qua-1.4.0-migrated-files.md) from git history.

```
uv run python scripts/generate_qua_migrated_files_inventory.py
```

## Bootstrap

### [`bootstrap_modality_repo.sh`](bootstrap_modality_repo.sh)

Copy the migration bootstrap kit into a new modality repo. File list: [MANIFEST.md](../docs/bootstrap/MANIFEST.md).

```
./scripts/bootstrap_modality_repo.sh AMO ../qua-libs-amo
```

## Simulation validation (this repo only)

Automated waveform comparison against sibling [`../qua-libs`](https://github.com/qua-platform/qua-libs) on branch `QL-1212-validation`. Requires CS rack network access. Full usage: [VALIDATION.md](../VALIDATION.md). Modality forks can skip these unless they maintain their own `VALIDATION.md`.

### [`validate_simulation_baseline.py`](validate_simulation_baseline.py)

Harness: simulate each script in this repo and the baseline, then compare canonical waveform-report lines.

```
uv run python scripts/validate_simulation_baseline.py --list-folders
uv run python scripts/validate_simulation_baseline.py --folder Single-Fixed-Transmon --print-notes
```

### [`simulate_waveform_runner.py`](simulate_waveform_runner.py)

Headless QCA simulate helper used by the harness. Emits waveform-report JSON (stdout or `--output`). Waits on OPX1000 configs only.

```
uv run python scripts/simulate_waveform_runner.py path/to/script.py --duration 10000
```

### [`validation_matrix.py`](validation_matrix.py)

Folder presets and script lists for [VALIDATION.md](../VALIDATION.md). Imported by the harness; not a standalone CLI.
