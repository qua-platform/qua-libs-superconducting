# Tests — superconducting-calibrations

Static gate for the [QUA 1.3.1 / 1.4.0 migration](../../../docs/plans/qua-1.4.0-migration.md) of
**calibration nodes** under `calibrations/`.

Despite the filename, `test_qua_compile.py` does **not** call the QM compiler (`qm.compile()`).
It checks Python syntax, module imports, qm-qua 1.3.1 API availability, and that deprecated
`declare_stream()` has been removed from calibration nodes.

## Test files

| File | Path | Role |
|------|------|------|
| `test_qua_compile.py` | `qualibration_graphs/superconducting/tests/test_qua_compile.py` | QUA 1.3.1 migration gate (main suite) |
| `test_config_split.py` | `qualibration_graphs/superconducting/tests/test_config_split.py` | QUA 1.4.0 config split + queue deprecation gates |
| `test_no_deprecated_amp.py` | `qualibration_graphs/superconducting/tests/test_no_deprecated_amp.py` | QUA 1.4.0 `amp()` deprecation grep gate |
| `test_qca_migration_gates.py` | `tests/test_qca_migration_gates.py` | Portable QCA migration gates (`QCA_MODALITY` env) |
| `test_smoke.py` | `qualibration_graphs/superconducting/tests/test_smoke.py` | Package import smoke test |
| `conftest.py` | `qualibration_graphs/superconducting/tests/conftest.py` | Stubs QualibrationNode run_actions and hardware I/O during import checks; redirects `Quam.load()` to the calibration package directory |

## Tests in `test_qua_compile.py`

Discovery scans `calibrations/` recursively for `.py` files that contain `create_qua_program`
(currently ~39 calibration nodes).

| Test | What it checks |
|------|----------------|
| `test_qm_extensions_importable` | qm-qua 1.3.1 APIs import: `declare_output_stream`, `declare_with_stream`, `QuaIterable`, `QuaIterableRange` |
| `test_calibration_module_syntax` | Parametrized: `ast.parse()` on each discovered calibration file |
| `test_calibration_module_imports` | Parametrized: `exec_module()` on each file; skips individual files on missing optional deps. [`conftest.py`](conftest.py) stubs `QualibrationNode.run_action` and hardware helpers so import checks do not connect to a QOP or run analysis |
| `test_no_deprecated_declare_stream_in_calibrations` | Fails if any calibration file still contains `declare_stream(` |

**Scope limits:**

- Only scans `calibrations/` (not `Quantum-Control-Applications/`).
- Does not run QUA simulation or `qm.compile()`.

## Tests in `test_smoke.py`

| Test | What it checks |
|------|----------------|
| `test_package_importable` | Skips unless `quam_config` is installed |

## Running locally

**Prerequisites:** Python 3.10–3.14 (CI uses 3.14). `pytest` is declared in the workspace
member dev group ([`pyproject.toml`](../pyproject.toml)), not the repo root — sync dev deps
before using `uv run pytest`.

```bash
# From repo root
uv sync --python 3.14
uv sync --package superconducting-calibrations --group dev   # installs pytest
```

```bash
# Full suite (from repo root)
uv run pytest qualibration_graphs/superconducting/tests/ -q

# Compile gate only
uv run pytest qualibration_graphs/superconducting/tests/test_qua_compile.py -q
```

From the calibration package directory:

```bash
cd qualibration_graphs/superconducting
uv run pytest -q
uv run pytest tests/test_qua_compile.py -q
```

## CI

See [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml).

| Job | Command | Scope |
|-----|---------|-------|
| `test` | `uv sync --python 3.14` then `uv run pytest -q` | All tests in `tests/` |
| `qua-compile` | `uv sync --python 3.14` then `uv run pytest tests/test_qua_compile.py -q` | `test_qua_compile.py` only |
| `qca-migration-gates` | `uv sync --python 3.14` then `QCA_MODALITY=Superconducting uv run pytest tests/test_qca_migration_gates.py -q` | Portable QCA grep gates (repo root) |

Both jobs install workspace dependencies from the repo root, then run pytest from
`qualibration_graphs/superconducting/`.
