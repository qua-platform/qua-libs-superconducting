Here we collect the results regarding the validation procedure of this branch.

Below one can find a table with the files that have been tested and whose results have been compared with the ones obtained using their original version in [qua-libs](https://github.com/qua-platform/qua-libs) (main branch, commit 30823059).

The set of tested scripts collectively covers these migration pillars (not every script hits all four).

| Migration pillar | What to verify |
|---|---|
| **QUA iterables (1.3.1)** | `QuaIterable` / `QuaIterableRange` replace nested `for_` + `from_array` sweep loops |
| **Streaming API (1.3.1)** | `declare_output_stream()` replaces `declare_stream()`; `declare_with_stream(..., average_axes=["shots"])` replaces manual `save(I, I_st)` + `.buffer().average()` in `stream_processing()` |
| **Config split (QOP>=3.5, required in QOP 4.0)** | `controller_config` + `logical_config`; execute via `open_qm(controller_config)` + `execute(..., config=logical_config)`; simulate via merged `config` |
| **`amp()` removal (1.4.0)** | `play(..., amplitude_scale=...)` / `measure(..., amplitude_scale=...)` instead of `"pulse" * amp(x)` |

## Simulated Results
For the first validation tests we used `simulate = True` and the OPX `CS_1_con1` (IP: 172.16.33.101).


| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Single-Fixed-Transmon/00_hello_qua.py` | — | — | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (758 analog waveforms) |
| `Single-Fixed-Transmon/04a_resonator_spectroscopy.py` | yes | yes | yes | — | pass | After `.astype(int)` on frequency sweep; sim compiles (12 analog, 6 digital, 12 ADC acquisitions) |
| `Single-Fixed-Transmon/05_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pass | After `.astype(int)` on `dfs`; sim compiles (12 analog, 6 digital, 12 ADC acquisitions) |
| `Single-Fixed-Transmon/08b_power_rabi.py` | yes | yes | yes | yes (`play`) | pass | Waveform report structure matches baseline (4 analog, 1 digital, 2 ADC acquisitions) |
| `Single-Fixed-Transmon/08c_power_rabi_error_amplification.py` | yes | yes | yes | yes (`play`) | pass | Waveform report structure matches baseline (2 analog, 1 digital, 2 ADC acquisitions) |

Baseline for comparison: same relative path under `../qua-libs/Quantum-Control-Applications/Superconducting/`.

## Executed Results