# AGENTS.md

QUA programs for **superconducting qubits** on Quantum Machines hardware (OPX).

- Pin: `qm-qua>=1.4.1,<2.0`
- QCA folder: `Quantum-Control-Applications/Superconducting`
- Local migration notes: [`qua141_migration/AGENTS.md`](qua141_migration/AGENTS.md)
- Shared kit: sibling `qua-libs-core` branch `QL-1212-qua141-py314` — [`qua141_migration/AGENTS.md`](../qua-libs-core/qua141_migration/AGENTS.md)

Official QUA docs: https://docs.quantum-machines.co/latest/

This file covers how this repository works. For how to write QUA itself, see the QUA guide for agents: TODO link.

## Layout

| Path | Role |
|------|------|
| `qualibration_graphs/superconducting/calibrations/1Q_calibrations/` | Single-qubit nodes (`NNx_name.py`) and 1Q graphs (`8x`/`9x_calibration_graph_*`) |
| `qualibration_graphs/superconducting/calibrations/CZ_calibrations/` | Two-qubit / CZ nodes and CZ graphs (`98`/`99_*`) |
| `qualibration_graphs/superconducting/calibration_utils/<node_name>/` | Per-node `parameters.py`, `analysis.py`, `plotting.py`, exposed via `__init__.py` |
| `qualibration_graphs/superconducting/calibration_utils/common_utils/` | Helpers shared by several nodes in this repo |
| `qualibration_graphs/superconducting/quam_config/` | `Quam` class, `generate_quam.py`, `populate_quam_*.py`, `wiring_examples/` |
| `qualibration_graphs/superconducting/tests/` | Static gates for calibration nodes (see *Checks*) |
| `Quantum-Control-Applications/` | Standalone example/calibration scripts |
| `Tutorials/` | Introductory QUAlibrate tutorial |
| `qua141_migration/` | Superconducting-only matrix, VALIDATION.md, inventories |
| `scripts/`, `tests/` | Repo tooling and repo-level gates (changelog, QCA migration) |

Where code belongs:
- Used by one node → `calibration_utils/<node_name>/`.
- Used by several nodes in this repo → `calibration_utils/common_utils/`.
- Generic, not superconducting-specific (plotting, data fetching, runtime) → `qualibration-libs`; wiring/connectivity → `quam-builder` or `py-qua-tools`. Don't add it here.

## Writing a calibration node

Start from an existing node (e.g. `1Q_calibrations/04b_power_rabi.py`) and keep its structure; details in [`calibrations/README.md`](qualibration_graphs/superconducting/calibrations/README.md). Must-haves:

- `description` block with what is measured (and what it is not), **Prerequisites**, and **State update** (exact QUAM paths written).
- `instrument_calibration_node(node)` right after the node is created (see *Conventions*).
- Use the QUAM channel API (`qubit.xy.play`, `resonator.measure`, `qubit.reset`, macros) rather than raw `play`/`measure` on element names.
- `analyse_data` sets `node.outcomes[q]` to `"successful"` or `"failed"`, and the success criterion can actually fail.
- `update_state` skips failed targets, runs inside `node.record_state_updates()`, and writes only what this run measured.
- Anything the analysis needs is stored in `node.results`, so `load_data_id` reproduces the run.

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
- Wrap Quantum Machines calls in [`qua_libs_core.telemetry`](https://github.com/qm-labs/qua-libs-core) decorators: `trace_qmm` (`qmm_connect`), `trace_open_qm`, `trace_execute`, `trace_simulate`, and the same for `get_simulated_samples`, fetching, and fits (`trace_get_simulated_samples`, `trace_fetching`, `trace_fit`). Standalone scripts also call `start_qca_telemetry` / `telemetry.end()`. Calibration nodes call `instrument_calibration_node(node)` after the node is created. See [How to add telemetry](https://github.com/qm-labs/qua-libs-core/blob/develop/docs/telemetry/HOW_TO_ADD_TELEMETRY.md).
- Do not use `pulse * amp(scale)`. Pass `amplitude_scale=` to `play`/`measure`. Inline multiplexed readout must pass `amplitude_scale=1`.
- Do not use `add_to_queue(..., overrides=...)`. Prefer `qm.execute(program, config=logical_config)`.
- Do not pass literal `None` as the third argument to `measure()`; omit it.
- After `qmm.simulate(...)`, call `job.wait_until("Done")` before samples only for OPX1000/FEM configs.

## Checks

```bash
uv sync                                                     # repo root
uv sync --package superconducting-calibrations --group dev  # node tests
uv run black --check . && uv run ruff check .
uv run pytest tests                                         # repo-level gates
cd qualibration_graphs/superconducting && uv run pytest -q  # node gates
```

`test_qua_compile.py` only checks syntax, imports and deprecated APIs — it does **not** compile QUA. A changed node also needs a simulation (`node.parameters.simulate = True`) or a hardware run; say which in the PR.

## Review

Full checklist: [REVIEW.md](REVIEW.md). Read it before opening a PR or reviewing one. The most common rejections:

- A success criterion that can never fail; ambiguous or untrusted fits that still update state.
- `update_state` overwriting a prior calibration the run did not measure; coupled updates (x180 → x90) not listed under *State update*.
- A description that doesn't say exactly what is measured and what it is not.
- Unintended multiplexing crosstalk, or a qubit/resonator that affects the result left in an unknown state.
- Analysis inputs kept only in `node.namespace`, so `load_data_id` can't reproduce the run.
- Re-implementing what the QUAM channel API or `qualibration-libs` already provides.
- Copy-pasted logic or constants instead of one definition that is imported.
- Unrelated changes in the PR.

## Changelog

[CHANGELOG.md](CHANGELOG.md) follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Before a commit, add user-visible work under `## [Unreleased]` (`Added` / `Changed` / `Fixed`, …). Skip whitespace-only or comment-only changes. Include `CHANGELOG.md` in the same commit as the functional change.

## Commits and PRs

Write a clear commit message with a subject line and a body. The subject says what changed, in one sentence. The body says why, and any constraint a later reader needs. Do not use a subject-only message.

Branch from and open PRs against **`develop`** (see CONTRIBUTING.md). The PR description says how the change was verified: static tests, simulation, or hardware (which setup, how many qubits, multiplexed or not).

## Superconducting validation

See [`qua141_migration/VALIDATION.md`](qua141_migration/VALIDATION.md). Baseline: sibling `../qua-libs` branch `QL-1212-validation`. Harness lives in qua-libs-core; CS rack IPs stay in this repo’s VALIDATION.md.
