# AGENTS.md

QUA programs for **superconducting qubits** on Quantum Machines hardware (OPX).

- Pin: `qm-qua==1.4.0`
- QCA folder: `Quantum-Control-Applications/Superconducting`
- Local migration notes: [`qua141_migration/AGENTS.md`](qua141_migration/AGENTS.md)
- Shared kit: sibling `qua-libs-core` branch `QL-1212-qua141-py314` — [`qua141_migration/AGENTS.md`](../qua-libs-core/qua141_migration/AGENTS.md)

Official QUA docs: https://docs.quantum-machines.co/latest/

## Layout

| Path | Role |
|------|------|
| `Quantum-Control-Applications/` | Standalone example/calibration scripts |
| `qualibration_graphs/superconducting/` | QUAlibrate calibration nodes |
| `Tutorials/` | Introductory QUAlibrate tutorial |
| `qua141_migration/` | Superconducting-only matrix, VALIDATION.md, inventories |

## Python vs QUA

- **Python** (outside `with program()`): setup, parameters, plotting, data handling, `QuantumMachinesManager`.
- **QUA** (inside `with program()`): real-time pulse sequences — `declare`, `play`, `measure`, `wait`, `align`, `for_`, `if_`, `declare_output_stream`, `declare_with_stream`, iterables.

Do not rewrite QUA constructs as plain Python loops or NumPy when they must run on the OPX in real time.

Related docs: [QUAM](https://qua-platform.github.io/quam/), [QUAlibrate](https://qualibrate-docs.quantum-machines.co/), [py-qua-tools](https://github.com/qua-platform/py-qua-tools).

## Conventions

- `from qm.qua import *` is standard; do not flag it as a lint issue.
- Match existing patterns in the nearest folder (standalone script vs qualibration node).
- Format/lint: `uv run black .` and `uv run ruff check .` per [CONTRIBUTING.md](CONTRIBUTING.md).
- Prefer iterables + auto-streaming; `declare_output_stream()` not `declare_stream()`. Frequency arrays for `update_frequency` must be `.astype(int)`.
- Config split: `open_qm(controller_config)`; `execute`/`compile` with `logical_config`. Simulate with `qmm.simulate(merge_qua_config(...), ...)` — never `open_qm` before simulate. `mixers` is controller config. Prefer `from qua_libs_core.qua_config import merge_qua_config`.
- Do not use `pulse * amp(scale)`. Pass `amplitude_scale=` to `play`/`measure`. Inline multiplexed readout must pass `amplitude_scale=1`.
- Do not use `add_to_queue(..., overrides=...)`. Prefer `qm.execute(program, config=logical_config)`.
- Do not pass literal `None` as the third argument to `measure()`; omit it.
- After `qmm.simulate(...)`, call `job.wait_until("Done")` before samples only for OPX1000/FEM configs.

## Changelog

[CHANGELOG.md](CHANGELOG.md) follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Before a commit, add user-visible work under `## [Unreleased]` (`Added` / `Changed` / `Fixed`, …). Skip whitespace-only or comment-only changes. Include `CHANGELOG.md` in the same commit as the functional change.

## Superconducting validation

See [`qua141_migration/VALIDATION.md`](qua141_migration/VALIDATION.md). Baseline: sibling `../qua-libs` branch `QL-1212-validation`. Harness lives in qua-libs-core; CS rack IPs stay in this repo’s VALIDATION.md.
