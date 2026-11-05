# Review checklist

Reviewers reject PRs on the points below. Check them before opening a PR, and use them when reviewing.
Black is enforced by CI. Run `uv run ruff check .` locally; ruff is not a CI job. Formatting and lint are not repeated here.

## Physics and measurement
- The description says exactly what the quantity is and what it is **not** (e.g. η is not readout fidelity), and names the confounders that move it.
- Prerequisites and *State update* in the description match the code.
- Multiplexing is a deliberate choice. If neighbouring resonators/qubits play at the same time, say whether that crosstalk is intended or must be avoided.
- Every qubit/resonator that affects the result starts in a known state (reset the driven qubit too, not only the measured one).
- Resonator depletion: waits are long enough, or leftover photons are handled explicitly.
- Operation order is correct: e.g. `update_frequency` before `reset`/`play` that should use it.
- For a sweep shared across qubits/pairs, the axis is valid for every target, not only the first.
- Units are right and labelled (ns vs µs, Hz vs MHz); no "a.u." for quantities with units.
- Error bars propagate correctly (prefer `uncertainties`); a result whose stderr exceeds the value fails.
- New experiments cite a reference (paper/thesis).

## Analysis, outcomes and state update
- `success` can actually be `False`. A criterion that is always true is a bug.
- Ambiguous or untrusted fits are `failed` and do not update state.
- `update_state` writes only what the run calibrated. Never reset an unrelated prior calibration (e.g. integration weights on an amplitude-only run).
- Coupled updates (e.g. x180 → x90) are explicit and listed under *State update*.
- Temporary QUAM changes for the sweep are tracked and reverted.
- Anything the analysis needs is saved in `node.results`, not only `node.namespace`, so `load_data_id` reproduces the run.
- Dataset variable names are persisted — no typos (`artifitial_detuning`).
- Fits work for shaped (non-square) pulses, or the limitation is stated.

## QUA program
- Use the QUAM channel API (`resonator.measure`, `resonator.measure_accumulated`, `qubit.reset`, macros) instead of raw `measure(...)` re-implementations.
- Use QUA control flow (`switch_`/`case_`, iterables) instead of hand-written repeated cases.
- Durations respect the 4 ns granularity.
- Compiler-heavy nodes are tested multiplexed/non-multiplexed and with/without active reset.
- Don't hard-code one platform's limits (LF-FEM gain range) in a node that also supports OPX+; don't reference specific measurement macros in generic nodes.

## Code hygiene
- No unused node parameters or tracked updates; no commented-out code; use `node.log`, not `print`.
- One definition per constant/sequence — import it, don't copy it between node and utils. Shared logic between sibling nodes (e.g. 37a/37b) is imported, not copy-pasted.
- Code lives at the right level: one node → `calibration_utils/<node_name>/`; several nodes → `common_utils/`; generic → upstream library (see AGENTS.md *Layout*).
- Keep `Parameters` thin: only what a user should tune.
- Telemetry is kept: nodes call `instrument_calibration_node(node, extra_attributes=["qubits"])`; QCA scripts use the `trace_*` wrappers (see AGENTS.md *Conventions*).
- Public helpers have type hints and a docstring with all arguments and a short usage example; expose them via `__init__.py`.
- The PR only touches files it needs: no unrelated reformatting, no WIP from another PR.
