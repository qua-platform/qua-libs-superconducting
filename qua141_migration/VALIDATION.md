Here we collect the results regarding the validation procedure of this branch.

Below one can find tables with the files that have been tested and whose results have been compared with the ones obtained using their original version in [qua-libs](https://github.com/qua-platform/qua-libs) (branch **`QL-1212-validation`**).

The set of tested scripts collectively covers these migration pillars (not every script hits all four).

| Migration pillar | What to verify |
|---|---|
| **QUA iterables (1.3.1)** | `QuaIterable` / `QuaIterableRange` replace nested `for_` + `from_array` sweep loops |
| **Streaming API (1.3.1)** | `declare_output_stream()` replaces `declare_stream()`; `declare_with_stream(..., average_axes=["shots"])` replaces manual `save(I, I_st)` + `.buffer().average()` in `stream_processing()` |
| **Config split (QOP>=3.5, required in QOP 4.0)** | `controller_config` + `logical_config`; execute via `open_qm(controller_config)` + `execute(..., config=logical_config)`; simulate via merged `config` |
| **`amp()` removal (1.4.0)** | `play(..., amplitude_scale=...)` / `measure(..., amplitude_scale=...)` instead of `"pulse" * amp(x)` |

## Scope

We validate **5 representative QUA scripts per top-level folder** under `Quantum-Control-Applications/Superconducting/` (**25 scripts total** across five documented folders). Use Case subfolders are not given separate tables. Scripts for `Two-Flux-Tunable-Coupled-Transmons` live under `Standard Configuration/` (that folder has no root-level QUA examples).

Baseline for comparison: [`../qua-libs`](../qua-libs) checked out on branch **`QL-1212-validation`**, same relative path under `Quantum-Control-Applications/Superconducting/`.

## Script selection

Scripts are chosen to maximize **distinct QUA program structure** across the 25 entries, not just distinct folder names.

- **Dedup rule:** reject any candidate whose line-level similarity to a script already in the matrix is **≥90%** (full-file `SequenceMatcher` ratio, same method as the overlap audit).
- **Per-folder constraint:** each folder keeps 5 scripts; migration pillars are verified **across the full 25**, not in every script.

## How to run

0. Ensure [`../qua-libs`](../qua-libs) is on branch **`QL-1212-validation`**. Confirm CS rack network access (see **Network prerequisites** below) before running the harness.
1. Set `simulate = True` in the script (most default to `False`; the 3D-storage-cavity folder and some `00_hello_qua.py` scripts default to `True`).
2. Run each side from **its own** script directory so `from configuration import *` resolves, using the runtime in **Runtime environments** below (do not run baseline scripts through the migrated `uv` env or vice versa).
3. Compare the compiled job / waveform report structure against the baseline script at the same relative path.
4. On frequency-sweep compile errors (`Expected type int but got fixed`), add `.astype(int)` to sweep arrays before passing them to `QuaIterable`.
5. Simulations use the CS rack cluster configured in each folder’s `configuration.py` — see **CS rack assignment** below. For **OPX1000/FEM** configs only, call `job.wait_until("Done")` after `qmm.simulate(...)` before pulling samples or the waveform report; legacy OPX/OPX+ configs do not need it.

Automated baseline comparison: sibling [`../qua-libs-core/qua141_migration/validate_simulation_baseline.py`](../qua-libs-core/qua141_migration/validate_simulation_baseline.py) (uses [`simulate_waveform_runner.py`](../qua-libs-core/qua141_migration/simulate_waveform_runner.py) in that same directory). Folder presets live in [validation_matrix.py](validation_matrix.py).

```
uv run python ../qua-libs-core/qua141_migration/validate_simulation_baseline.py --repo . --list-folders
uv run python ../qua-libs-core/qua141_migration/validate_simulation_baseline.py --repo . --folder Single-Fixed-Transmon --print-notes
```

The **Iterables**, **Streaming API**, **Config split**, and **`amplitude_scale`** columns below are filled by static code review. **Status** and **Notes** are updated only after simulation validation.

## Network prerequisites

Simulation validation is **not offline**. The core [`simulate_waveform_runner.py`](../qua-libs-core/qua141_migration/simulate_waveform_runner.py) opens `QuantumMachinesManager(host=qop_ip, cluster_name=cluster_name)` and calls `qmm.simulate(...)`; **both** the migrated and baseline sides need a live QOP session to the cluster configured in each script’s `configuration*.py`.

| Cluster | IP | When needed |
|---------|-----|-------------|
| **CS_1** | `172.16.33.101` | OPX+ configs (default `configuration.py`, Octave-on-`con1`, Use Case mixer configs) |
| **CS_3** | `172.16.33.115` | OPX1000 FEM configs |

Connect to the CS rack (VPN or on-site network as applicable). **Preflight:** `ping -c 1 172.16.33.101` and `ping -c 1 172.16.33.115` before running [`validate_simulation_baseline.py`](scripts/validate_simulation_baseline.py). If ping fails, fix network access before debugging waveform diffs.

**Cursor / sandbox:** agent shell runs need **`full_network`** when invoking the validation harness — the default sandbox blocks QOP gRPC and produces misleading `QMConnectionError` failures.

## CS rack assignment

Superconducting QCA configuration files target two Customer Success rack clusters. Set `qop_ip` and `cluster_name` in the relevant `configuration*.py` before connecting to hardware. Migrated configs in this repo and baseline configs on `../qua-libs` branch **`QL-1212-validation`** use the same CS_1 / CS_3 targets.

| CS server | IP | Platform | Hardware | Used by |
|-----------|-----|----------|----------|---------|
| **CS_1** | `172.16.33.101` | OPX+ | `con1`, `con2`, Octave `oct1` | Default `configuration.py`; Octave-on-`con1` variants; all Use Case mixer configs |
| **CS_3** | `172.16.33.115` | OPX1000 | `con1`; MW-FEM 1–2; LF-FEM 3/5/8; Octave | All OPX1000 FEM variants (`configuration_with_lf_fem*`, `configuration_with_mw_fem*`, `configuration_lf_fem*`, `configuration_mw_fem*`) |

**Assignment rule:** if `controller_config` contains `"type": "opx1000"`, use **CS_3**; otherwise use **CS_1** (OPX+ with external mixers and/or Octave on `con1`).

| Config filename pattern | CS server | LF FEM slot (CS_3 only) |
|-------------------------|:---------:|-------------------------|
| `configuration.py` | CS_1 | — |
| `configuration_with_octave.py` | CS_1 | — |
| Use Case `configuration.py` / `configuration_SSB.py` | CS_1 | — |
| `configuration_with_lf_fem.py`, `configuration_lf_fem.py` | CS_3 | 5 |
| `configuration_with_mw_fem.py`, `configuration_mw_fem.py` | CS_3 | — (MW-FEM 1) |
| `configuration_with_lf_fem_and_mw_fem.py` | CS_3 | LF 5, MW 1 |
| `configuration_with_lf_fem_and_octave.py`, `configuration_lf_fem_and_octave.py` | CS_3 | 3 |

## Runtime environments

Each baseline comparison uses **two separate Python environments** — one per repo:

| Side | Repo | Runner | QUA version |
|------|------|--------|-------------|
| **Migrated** | `qua-libs-superconducting` | `uv run python <script>` from script directory | `qm-qua>=1.4.1,<2.0` (repo pin) |
| **Baseline** | `../qua-libs` (branch **`QL-1212-validation`**) | `poetry run python <script>` from same relative script directory | `qm-qua>=1.2.0` (qua-libs Poetry env) |

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
| `Single-Fixed-Transmon/04a_resonator_spectroscopy.py` | yes | yes | yes | — | fail | `simulate=True`; waveform mismatch — counts match (12 analog, 6 digital, 12 ADC) but 36 diff lines; migrated script imports `configuration_with_mw_fem` (CS_3 / OPX1000, `%mw_ranged` pulses, port 1) while the baseline uses `configuration.py` |
| `Single-Fixed-Transmon/05_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (12 analog, 6 digital, 12 ADC); 0 diff lines |
| `Single-Fixed-Transmon/08b_power_rabi.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `Single-Fixed-Transmon/08c_power_rabi_error_amplification.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (2 analog, 1 digital, 2 ADC); 0 diff lines |

### 3D-storage-cavity

For these tests we used the OPX `CS_1` (IP: 172.16.33.101).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `3D-storage-cavity/00_selective_pulse_power_rabi.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/01_storage_spectroscopy.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (6 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/03a_number_splitting_spectroscopy_w_displacement.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (6 analog, 1 digital, 2 ADC); 0 diff lines |
| `3D-storage-cavity/06a_qubit_AC_Stark_shift_from_readout_pumping.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 0 digital, 0 ADC); 0 diff lines |
| `3D-storage-cavity/09_swapping.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (14 analog, 1 digital, 2 ADC); 0 diff lines |

### Single-Flux-Tunable-Transmon

For these tests we used the OPX `CS_1` (IP: 172.16.33.101).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Single-Flux-Tunable-Transmon/05b_resonator_spectroscopy_vs_flux.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (12 analog, 6 digital, 12 ADC); 0 diff lines |
| `Single-Flux-Tunable-Transmon/06b_qubit_spectroscopy_vs_flux.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `Single-Flux-Tunable-Transmon/07a_rabi_chevron_duration.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `Single-Flux-Tunable-Transmon/07b_rabi_chevron_amplitude.py` | yes | yes | yes | yes (`play`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |
| `Single-Flux-Tunable-Transmon/08a_time_rabi.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (4 analog, 1 digital, 2 ADC); 0 diff lines |

### Two-Fixed-Coupled-Transmons

For `00_hello_qua.py` we used OPX `CS_3` (IP: `172.16.33.115`, LF-FEM + Octave / OPX1000). For the other four scripts we used OPX `CS_1` (IP: `172.16.33.101`).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Two-Fixed-Coupled-Transmons/00_hello_qua.py` | — | — | yes | — | pass | `simulate=True`; waveform report matches baseline (4 analog, 0 digital, 0 ADC); 0 diff lines; uses `configuration_lf_fem_and_octave` |
| `Two-Fixed-Coupled-Transmons/03_resonator_spectroscopy_single.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (26 analog, 13 digital, 26 ADC); 0 diff lines |
| `Two-Fixed-Coupled-Transmons/04_resonator_spectroscopy_multiplexed.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (52 analog, 26 digital, 52 ADC); 0 diff lines |
| `Two-Fixed-Coupled-Transmons/05_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (52 analog, 26 digital, 52 ADC); 0 diff lines |
| `Two-Fixed-Coupled-Transmons/08_power_rabi.py` | yes | yes | yes | yes (`play`, `measure`) | pass | `simulate=True`; waveform report matches baseline (4 analog, 2 digital, 4 ADC); 0 diff lines |

### Two-Flux-Tunable-Coupled-Transmons (`Standard Configuration/`)

For these tests we used the OPX `CS_1` (IP: `172.16.33.101`).

| Script | Iterables | Streaming API | Config split | `amplitude_scale` | Status | Notes |
|--------|:---------:|:-------------:|:------------:|:-----------------:|:------:|-------|
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/04_resonator_spectroscopy_single.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (14 analog, 7 digital, 14 ADC); 0 diff lines |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/05_resonator_spectroscopy_multiplexed.py` | yes | yes | yes | — | pass | `simulate=True`; waveform report matches baseline (28 analog, 14 digital, 28 ADC); 0 diff lines |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/06_resonator_spectroscopy_vs_amplitude.py` | yes | yes | yes | yes (`measure`) | pass | `simulate=True`; waveform report matches baseline (28 analog, 14 digital, 28 ADC); 0 diff lines |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/08_qubit_spectroscopy_vs_flux_simultaneous.py` | yes | yes | yes | yes (`play`, `measure`) | pass | `simulate=True`; waveform report matches baseline (16 analog, 4 digital, 8 ADC); 0 diff lines; dual-qubit flux spectroscopy |
| `Two-Flux-Tunable-Coupled-Transmons/Standard Configuration/21_CZ.py` | yes | yes | yes | yes (`play`, `measure`) | pass | `simulate=True`; waveform report matches baseline (27 analog, 6 digital, 12 ADC); 0 diff lines; flux-driven two-qubit calibration |

