Here we collect the results regarding the validation procedure of this branch.

Below one can find tables with the files that have been tested and whose results have been compared with the ones obtained using their original version in [qua-libs](https://github.com/qua-platform/qua-libs) (main branch, commit 30823059).

The set of tested scripts collectively covers these migration pillars (not every script hits all four).

| Migration pillar | What to verify |
|---|---|
| **QUA iterables (1.3.1)** | `QuaIterable` / `QuaIterableRange` replace nested `for_` + `from_array` sweep loops |
| **Streaming API (1.3.1)** | `declare_output_stream()` replaces `declare_stream()`; `declare_with_stream(..., average_axes=["shots"])` replaces manual `save(I, I_st)` + `.buffer().average()` in `stream_processing()` |
| **Config split (QOP>=3.5, required in QOP 4.0)** | `controller_config` + `logical_config`; execute via `open_qm(controller_config)` + `execute(..., config=logical_config)`; simulate via merged `config` |
| **`amp()` removal (1.4.0)** | `play(..., amplitude_scale=...)` / `measure(..., amplitude_scale=...)` instead of `"pulse" * amp(x)` |

## Scope

We validate **5 representative QUA scripts per top-level folder** under `Quantum-Control-Applications/Superconducting/` (**25 scripts total**). Use Case subfolders are not given separate tables. Scripts for `Two-Flux-Tunable-Coupled-Transmons` live under `Standard Configuration/` (that folder has no root-level QUA examples).

Baseline for comparison: same relative path under `../qua-libs/Quantum-Control-Applications/Superconducting/`.

## Script selection

Scripts are chosen to maximize **distinct QUA program structure** across the 25 entries, not just distinct folder names.

- **Dedup rule:** reject any candidate whose line-level similarity to a script already in the matrix is **≥90%** (full-file `SequenceMatcher` ratio, same method as the overlap audit).
- **Per-folder constraint:** each folder keeps 5 scripts; migration pillars are verified **across the full 25**, not in every script.

## How to run

1. Set `simulate = True` in the script (most default to `False`; the 3D-storage-cavity folder and some `00_hello_qua.py` scripts default to `True`).
2. Run each side from **its own** script directory so `from configuration import *` resolves, using the runtime in **Runtime environments** below (do not run baseline scripts through the migrated `uv` env or vice versa).
3. Compare the compiled job / waveform report structure against the baseline script at the same relative path.
4. On frequency-sweep compile errors (`Expected type int but got fixed`), add `.astype(int)` to sweep arrays before passing them to `QuaIterable`.
5. Simulations use the OPX cluster configured in each folder’s `configuration.py` (e.g. `CS_1` at IP `172.16.33.101`).

Automated baseline comparison: [scripts/validate_simulation_baseline.py](scripts/validate_simulation_baseline.py) (uses [scripts/simulate_waveform_runner.py](scripts/simulate_waveform_runner.py) headlessly, compares canonical lines from `waveform_report.to_dict()` with timestamps normalized to the first pulse). Folder presets and script lists live in [scripts/validation_matrix.py](scripts/validation_matrix.py) (see `--list-folders`).

The **Iterables**, **Streaming API**, **Config split**, and **`amplitude_scale`** columns below are filled by static code review. **Status** and **Notes** are updated only after simulation validation.

## Runtime environments

Each baseline comparison uses **two separate Python environments** — one per repo:

| Side | Repo | Runner | QUA version |
|------|------|--------|-------------|
| **Migrated** | `qua-libs-superconducting` | `uv run python <script>` from script directory | `qm-qua==1.4.0` (repo pin) |
| **Baseline** | `../qua-libs` | `poetry run python <script>` from same relative script directory | `qm-qua>=1.2.0` (qua-libs Poetry env) |

Each side uses its own `configuration.py` and `macros.py`. Example harness invocation (any VALIDATION folder):

```bash
cd qua-libs-superconducting
uv run python scripts/validate_simulation_baseline.py --folder Single-Fixed-Transmon --print-notes
uv run python scripts/validate_simulation_baseline.py --list-folders
```

Legacy ad-hoc paths (same as `--folder 3D-storage-cavity`):

```bash
uv run python scripts/validate_simulation_baseline.py \
  --baseline-root ../qua-libs/Quantum-Control-Applications/Superconducting/3D-storage-cavity \
  --baseline-repo ../qua-libs \
  --baseline-runner "poetry run python" \
  --migrated-root Quantum-Control-Applications/Superconducting/3D-storage-cavity \
  --migrated-runner "uv run python"
```

## Results

### Single-Fixed-Transmon

For these tests we used the OPX `CS_1_con1` (IP: 172.16.33.101).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Single-Fixed-Transmon/00_hello_qua.py` | — | — | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (758 analog, 0 digital, 0 ADC); 0 diff lines |
| `Single-Fixed-Transmon/04a_resonator_spectroscopy.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (12 analog, 6 digital, 12 ADC); 0 diff lines |
| `Single-Fixed-Transmon/05_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (12 analog, 6 digital, 12 ADC); 0 diff lines |
| `Single-Fixed-Transmon/08b_power_rabi.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `Single-Fixed-Transmon/08c_power_rabi_error_amplification.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (2 analog, 1 digital, 2 ADC); 0 diff lines |

### 3D-storage-cavity

For these tests we used the OPX `CS_1` (IP: 172.16.33.101).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `3D-storage-cavity/01_storage_spectroscopy.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (6 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/00_selective_pulse_power_rabi.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/06a_qubit_AC_Stark_shift_from_readout_pumping.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 0 digital, 0 ADC); 0 diff lines |
| `3D-storage-cavity/03a_number_splitting_spectroscopy_w_displacement.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (6 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/09_swapping.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (14 analog, 1 digital, 2 ADC); 0 diff lines |

### Single-Flux-Tunable-Transmon

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Single-Flux-Tunable-Transmon/07a_rabi_chevron_duration.py` | yes | yes | yes | — | pending | 2D time×detuning sweep |
| `Single-Flux-Tunable-Transmon/05b_resonator_spectroscopy_vs_flux.py` | yes | yes | yes | — | pending | Flux-specific 2D resonator spectroscopy |
| `Single-Flux-Tunable-Transmon/06b_qubit_spectroscopy_vs_flux.py` | yes | yes | yes | yes (`play`) | pending | |
| `Single-Flux-Tunable-Transmon/07b_rabi_chevron_amplitude.py` | yes | yes | yes | yes (`play`) | pending | 2D chevron amplitude calibration |
| `Single-Flux-Tunable-Transmon/08a_time_rabi.py` | yes | yes | yes | — | pending | Duration sweep (complements amplitude calibrations) |

### Two-Fixed-Coupled-Transmons

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Two-Fixed-Coupled-Transmons/00_hello_qua.py` | — | — | yes | — | pending | Uses `configuration_lf_fem_and_octave` |
| `Two-Fixed-Coupled-Transmons/03_resonator_spectroscopy_single.py` | yes | yes | yes | — | pending | |
| `Two-Fixed-Coupled-Transmons/04_resonator_spectroscopy_multiplexed.py` | yes | yes | yes | — | pending | |
| `Two-Fixed-Coupled-Transmons/05_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pending | |
| `Two-Fixed-Coupled-Transmons/08_power_rabi.py` | yes | yes | yes | yes (`play`) | pending | |

### Two-Flux-Tunable-Coupled-Transmons (`Standard Configuration/`)

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/08_qubit_spectroscopy_vs_flux_simultaneous.py` | yes | yes | yes | yes (`play`) | pending | dual-qubit flux spectroscopy |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/04_resonator_spectroscopy_single.py` | yes | yes | yes | — | pending | |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/05_resonator_spectroscopy_multiplexed.py` | yes | yes | yes | — | pending | |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/06_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pending | |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/21_CZ.py` | yes | yes | yes | yes (`play`) | pending | flux-driven two-qubit calibration |

