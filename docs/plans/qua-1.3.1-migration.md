# QUA 1.3.1 Migration Guide

Living reference for migrating this repository to **qm-qua 1.3.1** with
[Iterables & Auto-Streaming](https://docs.quantum-machines.co/1.3.1/docs/Guides/qua_iterables/).

Release notes: [qm-qua 1.3.1](https://docs.quantum-machines.co/1.3.1/docs/Releases/qm_qua_releases/)

## Baseline audit

| Metric | Count |
|--------|------:|
| Python files with `with program()` | 227 |
| — `Quantum-Control-Applications/` | 187 |
| — `qualibration_graphs/superconducting/` | 39 |
| — `Tutorials/intro-to-QUAlibrate/` | 1 |
| Files using `stream_processing` | ~218 |
| Nested `for_` loop migration candidates | ~180 |
| Shared `macros.py` helpers | 7 |

## Compatibility (1.3.1)

| Old API | Replacement |
|---------|-------------|
| `declare_stream()` | `declare_output_stream()` |
| `declare_external_stream()` | `declare_input_stream()` / `declare_output_stream()` |
| `send_to_external_stream()` | `send_to_stream()` |
| `receive_from_external_stream()` | `receive_from_stream()` |

Use `PythonIterable` / `PythonIterableRange` (not deprecated `NativeIterable*`).

## When to migrate vs keep manual streams

| Pattern | Action |
|---------|--------|
| `shots × sweep × measure(I,Q)` + `.buffer().average()` | **Migrate** to iterables |
| 2D aligned sweeps | **Migrate** with nested iterables or `QuaProduct` |
| RB, tomography, custom `.map()` chains | **Keep manual** |
| IQ blobs (`.save_all()`) | **Keep manual** |
| Cryoscope / ADC streams | **Keep manual** |

## Tier A migration template

Reference node: [`02a_resonator_spectroscopy.py`](../../qualibration_graphs/superconducting/calibrations/1Q_calibrations/02a_resonator_spectroscopy.py)

**Before:**

```python
I, I_st, Q, Q_st, n, n_st = node.machine.declare_qua_variables()
df = declare(int)
with for_(n, 0, n < n_avg, n + 1):
    save(n, n_st)
    with for_(*from_array(df, dfs)):
        ...
        save(I[i], I_st[i])
with stream_processing():
    I_st[i].buffer(len(dfs)).average().save(f"I{i + 1}")
```

**After:**

```python
from qm.qua.extensions import QuaIterable, QuaIterableRange

with program() as node.namespace["qua_program"]:
    n = declare(int)
    n_st = declare_output_stream()

    for multiplexed_qubits in qubits.batch():
        ...
        for shot in QuaIterableRange("shots", n_avg):
            assign(n, shot)
            save(n, n_st)
            for df in QuaIterable("detuning", dfs):
                for i, qubit in multiplexed_qubits.items():
                    I = declare_with_stream(fixed, f"I{i + 1}", average_axes=["shots"])
                    Q = declare_with_stream(fixed, f"Q{i + 1}", average_axes=["shots"])
                    ...

    with stream_processing():
        n_st.save("n")
```

## Phased rollout

1. **Phase 0** — Pin `qm-qua>=1.3.1`, CI on Python 3.14, compile tests — **done**
2. **Phase 1** — Qualibration Tier A nodes (~25–30) — **done**
3. **Phase 2** — Inline stream declarations in qualibration hybrids (removed `declare_qua_variables` from Tier A sweep nodes) — **done**
4. **Phase 3** — Qualibration Tier B (RB, CZ, IQ, cryoscope keep-manual; hybrids 00, 19_zz, CZ 31–33 migrated) — **done**
5. **Phase 4** — Tutorial (`time_of_flight.py`, `node_anatomy.ipynb` prose aligned with ToF pattern) — **done**
6. **Phase 5** — `Quantum-Control-Applications/` folder-by-folder — **done**

## Completion checklist (2026-07-22)

Full file inventory: [`qua-1.3.1-migrated-files.md`](qua-1.3.1-migrated-files.md)

| Criterion | Status |
|-----------|--------|
| No executable `.py` uses `declare_stream()` | Pass — grep gate in `test_qua_compile.py`; notebook/readme compat-only references updated |
| Sweep scripts use `QuaIterable` + `declare_with_stream(..., average_axes=["shots"])` | Pass — all `shots × sweep × measure(I,Q) + .buffer().average()` scripts migrated |
| Keep-manual scripts use `declare_output_stream` + manual `stream_processing()` | Pass — RB, tomography, IQ blobs, cryoscope, ADC/ToF, readout optimization, frequency tracking |
| Qualibration nodes: no deprecated stream APIs | Pass — 39 calibration nodes syntax-checked; hybrid nodes inline `declare_with_stream` |
| `test_qm_extensions_importable` + syntax + `declare_stream` gate | Pass locally |
| Import/exec of calibration modules (`Quam.load()`) | Requires local QUAM state (e.g. `quam_state/state.json`); CI must provide state path |

### Qualibration graph (39 nodes)

| Category | Nodes | Iterable migration |
|----------|-------|-------------------|
| Tier A sweeps | 02a–06b, 08a–10b, 12–14, 17, 19_zz, CZ 31–33, … | **Migrated** — inline `declare_with_stream`, `n_st.save("n")` |
| Keep-manual | 11a, 11b, 16a, 16b, 18, 30, 35, 36 | **Compat only** — still use `declare_qua_variables()` + manual buffers |
| ADC / ToF | 01a, 01b | **Compat only** — `QuaIterableRange` for shots optional; ADC streams manual |
| IQ blobs | 07, 15 | **Compat only** — manual `.save_all()` streaming |

### Quantum-Control-Applications (187 scripts)

| Folder | Sweep migration | Notes |
|--------|----------------|-------|
| Single-Fixed-Transmon | Done | Templates: `04a`, `05` (2D) |
| Single-Flux-Tunable-Transmon | Done | Includes Use Case 4 phase-modulated 2D sweep |
| Two-Fixed-Coupled-Transmons | Done | Multiplexed `I1`…`Q2` via `declare_with_stream` |
| Two-Flux-Tunable Standard Configuration | Done | |
| 3D-storage-cavity | Done | |
| Use-case subfolders | Done | RB/tomography/cryoscope/IQ/ADC left manual per table above |

**Keep-manual QCA patterns (~67 scripts):** filenames/content matching RB (`16*`), tomography (`19_state`, `20_state`, Use Case tomography), cryoscope (`17_cryoscope*`, Use Case cryoscope), IQ blobs (`10*readout*`, `11_IQ`), raw ADC (`02_raw_adc*`), time-of-flight (`03_time_of_flight*`), frequency tracking, readout weight optimization with custom `.map()` chains.

### Permanently excluded from iterables

- Randomized benchmarking (standard + interleaved + use-case RB)
- State / process tomography
- IQ blob calibration (`.save_all()`)
- Cryoscope / cryoscope amplitude calibration
- Raw ADC traces and time-of-flight (manual `.input1().average().save(...)`)
- Readout frequency/duration/weight optimization with non-uniform stream chains
- Cross-resonance calibration scripts with nested manual buffers
- Google DRAG detuning sweeps (Use Case 2 — Python outer loop over config, 1D iter sweep inside)

## Testing

- **Compile gate:** `qualibration_graphs/superconducting/tests/test_qua_compile.py`
- **Simulation smoke:** enable `node.parameters.simulate` locally
- **CI:** `.github/workflows/ci.yml` — `qua-compile` job after `uv sync`

## Risks

- `PythonIterable` may suffix stream names (`I_0` vs `I1`) — use explicit stream names in `declare_with_stream`
- Multiplexed qubits: keep Python batch loop; declare per-qubit streams with `f"I{i+1}"`
- `XarrayDataFetcher` expects stream `"n"` for progress — declare `n = declare(int)` and `n_st = declare_output_stream()`, then `assign(n, shot)` / `save(n, n_st)` each shot

## Controller / logical config split (qm-qua 1.4.0)

Since QOP 3.5, the QUA configuration is split into a **controller config** (physical hardware) and a **logical config** (elements, pulses, waveforms). See [Configuration](https://docs.quantum-machines.co/latest/docs/Introduction/config/) and [qm-qua 1.4.0 release notes](https://docs.quantum-machines.co/1.4.0/docs/Releases/qm_qua_releases/).

**Requirements:** qm-qua **1.4.0** + QOP **≥ 3.5.1** for per-job logical config on execute/compile.

| Part | Keys |
|------|------|
| Controller config | `controllers`, `octaves`, `mixers` |
| Logical config | `elements`, `pulses`, `waveforms`, `digital_waveforms`, `integration_weights`, `oscillators` |

Helpers: [`qua_config_split.py`](../../Quantum-Control-Applications/Superconducting/qua_config_split.py) (QCA) and [`calibration_utils/qua_config_split.py`](../../qualibration_graphs/superconducting/calibration_utils/qua_config_split.py) (qualibration).

### configuration.py template

```python
from qua_config_split import merge_qua_config

controller_config = {
    "controllers": { ... },
    "mixers": { ... },
    # "octaves": { ... },  # when present
}
logical_config = {
    "elements": { ... },
    "pulses": { ... },
    "waveforms": { ... },
    "digital_waveforms": { ... },
    "integration_weights": { ... },
}
config = merge_qua_config(controller_config, logical_config)  # transitional alias for simulate / data export
```

Do not include a top-level `"version"` key (removed in qm-qua 1.2.3).

### Runtime — execute / compile

Open the QM with the controller config only; pass logical config per job:

```python
qm = qmm.open_qm(controller_config)
job = qm.execute(program, config=logical_config)
program_id = qm.compile(program, config=logical_config)
```

### Runtime — simulation (no open_qm)

Per the [OPX Simulator](https://docs.quantum-machines.co/latest/docs/Guides/simulator/), call `simulate()` on the manager — **do not** open a QM (avoids reserving OPX ports on shared clusters):

```python
job = qmm.simulate(config, program, SimulationConfig(duration=...))  # config = merge_qua_config(...)
job.wait_until("Done")
```

### Qualibration node template

```python
from calibration_utils.qua_config_split import split_qua_config

config = node.machine.generate_config()
controller_config, logical_config = split_qua_config(config)
with qm_session(qmm, controller_config, timeout=...) as qm:
    job = qm.execute(node.namespace["qua_program"], config=logical_config)
```

For `simulate_qua_program`, keep using `simulate_and_plot(qmm, config, ...)` with the merged config (no `open_qm`).

### Runtime config mutations

| Target | Sub-dict |
|--------|----------|
| DC offsets, port filters | `controller_config["controllers"]` |
| Mixer corrections | `controller_config["mixers"]` |
| Elements, pulses, IF in elements | `logical_config` |

### Completion checklist (config split)

| Criterion | Status |
|-----------|--------|
| All `configuration*.py` export `controller_config` + `logical_config` | Pending |
| Execute path: `open_qm(controller_config)` + `execute(..., config=logical_config)` | Pending |
| Simulate path: `qmm.simulate(config, ...)` without `open_qm` | Pending |
| Qualibration nodes split `generate_config()` at execute time | Pending |
| Grep gate in `test_config_split.py` | Pending |
