# AGENTS.md — Superconducting migration notes

This directory is **fork-local**: validation matrix, results, inventories. Do **not** copy migrators here.

## Invoke the core kit

```
export QCA_MODALITY=Superconducting
uv run python ../qua-libs-core/qua141_migration/migrate_amp_to_amplitude_scale.py --repo . --modality Superconducting --dry-run
uv run python ../qua-libs-core/qua141_migration/validate_simulation_baseline.py --repo . --list-folders
QCA_REPO=. QCA_MODALITY=Superconducting uv run pytest ../qua-libs-core/qua141_migration/tests/test_qca_migration_gates.py
```

Shared conventions: `../qua-libs-core/qua141_migration/AGENTS.md` and the runbook under `../qua-libs-core/qua141_migration/docs/`.

## Keep-manual (already migrated)

QCA here is on 1.3.1/1.4.0. Dry-run migrators should no-op. Nested 2D sweeps, custom stream processing, and similar stay manual — see the core runbook keep-manual list.

## Validation

Fill [`VALIDATION.md`](VALIDATION.md) from harness `--print-notes`. Results under `validation_results/` (gitignored). Baseline `../qua-libs` @ `QL-1212-validation`. Requires CS rack network (see VALIDATION.md).
