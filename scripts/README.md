# Scripts

Tooling for QUA 1.3.1 / 1.4.0 migration, modality-repo bootstrap, and Superconducting simulation validation.

Run Python tools from the **repo root** with `uv run python scripts/<name>.py` unless noted. Bulk migrators accept `--modality` / `--qca-root` (or `$QCA_MODALITY`) via [`migration_paths.py`](migration_paths.py). Prefer `--dry-run` before applying.

Related docs: [migration runbook](../docs/plans/qua-1.4.0-migration-runbook.md), [migration guide](../docs/plans/qua-1.4.0-migration.md), [VALIDATION.md](../VALIDATION.md), [bootstrap manifest](../docs/bootstrap/MANIFEST.md).

## Shared helpers

### [`migration_paths.py`](migration_paths.py)

Shared `--modality` / `--qca-root` / `$QCA_MODALITY` resolution for bulk migration scripts. Not a standalone CLI.

### [`qca_script_loader.py`](qca_script_loader.py)

Shared QCA script prelude loader (`load_program_namespace`, plus the `--set NAME=EXPR` override helpers) used by `simulate_waveform_runner.py`, `emulate_waveform_runner.py`, and `export_qua_proto.py`. Not a standalone CLI.

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

Automated waveform/schedule comparison against sibling [`../qua-libs`](https://github.com/qua-platform/qua-libs) on branch `QL-1212-validation`. With the default `simulate` backends both sides need CS rack network access. On the QUA 2 branch, `--baseline-backend emulate --migrated-backend emulate` runs both sides through `qua_evaluator.QuaEvaluator` (source [`../qua-evaluator`](../../qua-evaluator), wheel `qua2-wheels/qua_evaluator-1.0.4-py3-none-any.whl`) and needs no rack. Full usage: [VALIDATION.md](../VALIDATION.md). Modality forks can skip these unless they maintain their own `VALIDATION.md`.

### [`validate_simulation_baseline.py`](validate_simulation_baseline.py)

Harness: run each script in this repo and the baseline, then compare canonical lines. Both sides default to `qmm.simulate()`. For the QUA 2 branch, `--baseline-backend emulate --migrated-backend emulate` evaluates the original as QUA 1 (built in the baseline Poetry env with `export_qua_proto.py`) and this repo's script as QUA 2, then diffs the two pulse schedules. `--set n_avg=2` shrinks loops on both sides, because the evaluator unrolls every iteration. `--migrated-backend emulate` alone keeps a simulator baseline; the two report formats differ, so it cannot pass. See [VALIDATION.md § QUA 2 branch](../VALIDATION.md#qua-2-branch-emulator-based-validation-experimental) for current status (blocked pending per-script QUA 2 migration) and caveats.

```
uv run python scripts/validate_simulation_baseline.py --list-folders
uv run python scripts/validate_simulation_baseline.py --folder Single-Fixed-Transmon --print-notes
uv run python scripts/validate_simulation_baseline.py --folder Single-Fixed-Transmon \
  --baseline-backend emulate --migrated-backend emulate --set n_avg=2
```

### [`simulate_waveform_runner.py`](simulate_waveform_runner.py)

Headless QCA simulate helper used by the harness (`qmm.simulate()`). Emits waveform-report JSON (stdout or `--output`). Waits on OPX1000 configs only.

```
uv run python scripts/simulate_waveform_runner.py path/to/script.py --duration 10000
```

### [`emulate_waveform_runner.py`](emulate_waveform_runner.py)

Headless QCA emulate helper used by the harness (`QuaEvaluator().evaluate()`, QUA 2 branch). Evaluates a QUA 2 script directly, or with `--from-proto` an `export_qua_proto.py` envelope (e.g. a QUA 1 original) using the envelope's dialect. Emits a pulse-schedule JSON (stdout or `--output`); no live QOP session needed. Scripts not yet migrated to QUA 2 report a `_blocked` payload (reason + detail) instead of crashing. `--set NAME=EXPR` rewrites a top-level assignment before loading.

```
uv run python scripts/emulate_waveform_runner.py path/to/script.py --set n_avg=2 --length-ns 40000
uv run python scripts/emulate_waveform_runner.py --from-proto envelope.json --output report.json
```

### [`export_qua_proto.py`](export_qua_proto.py)

Builds a QCA script's QUA program and config with whatever `qm-qua` is installed, and writes them as base64 protobuf bytes in a JSON envelope (`dialect`, `program`, `config`). Nothing is sent to a QOP server. Run it in the `../qua-libs` Poetry env (qm-qua 1.x) so the QUA 1 originals can be evaluated in this repo's qm-qua 2 env. The harness calls it for `--baseline-backend emulate`.

```
cd ../qua-libs && poetry run python ../qua-libs-superconducting/scripts/export_qua_proto.py \
  Quantum-Control-Applications/Superconducting/Single-Fixed-Transmon/08b_power_rabi.py \
  --set n_avg=2 --output /tmp/08b_power_rabi.proto.json
```

### [`validation_matrix.py`](validation_matrix.py)

Folder presets and script lists for [VALIDATION.md](../VALIDATION.md). Imported by the harness; not a standalone CLI.
