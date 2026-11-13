## [Unreleased]

### Added

- Shared **1Q/2Q RB** utilities (`calibration_utils/common_utils/rb/`), RB node updates (11a/11b, 37a/37b), and pytest coverage from `qua-platform/qua-libs` main (`84edacd3`).
- G/e/f confusion matrix support in **15_iq_blobs_gef** (`08dd3372`).
- Readout calibration nodes **23c–23f** (depletion validation, optimal integration weights, DRACHMA zeta/kappa) and supporting `calibration_utils` from `qua-platform/qua-libs` main (`878b2a8d`).
- Nightly smoke test that builds every superconducting calibration node's QUA program and hardware config on a hardware-free QUAM. Nodes that need prior calibration data are listed in `smoke_tests/known_broken.txt` with the error each is expected to raise; a different error, or a listed node that now builds, fails the job.

### Changed

- Sync superconducting calibrations from `qua-platform/qua-libs` main (`7758a3b0`); re-applied `qua_libs_core.telemetry` on Qualibration nodes after upstream copy.
- Pin `qua-libs-core` to `>=0.5.1,<0.6` in the workspace, the calibration package, and the intro-to-QUAlibrate tutorial. Pin `quam-builder` to git tag `v0.6.0` in the calibration package only; the tutorial's `quam-builder` dependency stays an unpinned git URL.

### Fixed

- Repair telemetry hook placement and run black on calibration nodes so CI formatting passes.

## [2026-09-25]

### Added

- Instrument QCA scripts and Qualibrate nodes with `qua_libs_core.telemetry`.
- Pin `qua-libs-core` to PyPI `>=0.3.0,<0.4`.
- `develop` integration branch, CI on `develop` and `main`, and a changelog check on merges to `main`.
