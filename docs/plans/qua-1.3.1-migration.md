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

1. **Phase 0** — Pin `qm-qua>=1.3.1`, CI on Python 3.14, compile tests
2. **Phase 1** — Qualibration Tier A nodes (~25–30)
3. **Phase 2** — Shared stream utils (`declare_qua_variables`, readout helpers)
4. **Phase 3** — Qualibration Tier B (partial: RB, CZ, IQ, cryoscope)
5. **Phase 4** — Tutorial
6. **Phase 5** — `Quantum-Control-Applications/` folder-by-folder

## Testing

- **Compile gate:** `qualibration_graphs/superconducting/tests/test_qua_compile.py`
- **Simulation smoke:** enable `node.parameters.simulate` locally
- **CI:** `.github/workflows/ci.yml` — `qua-compile` job after `uv sync`

## Risks

- `PythonIterable` may suffix stream names (`I_0` vs `I1`) — use explicit stream names in `declare_with_stream`
- Multiplexed qubits: keep Python batch loop; declare per-qubit streams with `f"I{i+1}"`
- `XarrayDataFetcher` expects stream `"n"` for progress — declare `n = declare(int)` and `n_st = declare_output_stream()`, then `assign(n, shot)` / `save(n, n_st)` each shot
