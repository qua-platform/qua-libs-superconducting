## [Unreleased]

### Changed

- Sync superconducting calibrations from `qua-platform/qua-libs` main (`7758a3b0`); re-applied `qua_libs_core.telemetry` on Qualibration nodes after upstream copy.

### Fixed

- Repair telemetry hook placement and run black on calibration nodes so CI formatting passes.

## [2026-09-25]

### Added

- Instrument QCA scripts and Qualibrate nodes with `qua_libs_core.telemetry`.
- Pin `qua-libs-core` to PyPI `>=0.3.0,<0.4`.
- `develop` integration branch, CI on `develop` and `main`, and a changelog check on merges to `main`.
