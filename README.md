# qua-libs-superconducting

Superconducting qubit examples and calibration graphs, split from [qua-libs](https://github.com/qua-platform/qua-libs).

## Contents

- `Quantum-Control-Applications/Superconducting/` — QCA scripts (transmon setups, use cases)
- `qualibration_graphs/superconducting/` — QUAlibrate calibration nodes and QUAM config
- `Tutorials/intro-to-QUAlibrate/` — introductory QUAlibrate tutorial (optional inclusion)

## Known issues / TODO

- [ ] Document structure and how QCA vs qualibration_graphs relate
- [ ] Explain how to run examples (hardware, simulation, QUAlibrate web UI)
- [ ] Define root-level dependencies vs per-subproject dependencies
- [ ] **Duplicate package name:** both `qualibration_graphs/superconducting/pyproject.toml` and `Tutorials/intro-to-QUAlibrate/pyproject.toml` declare `name = "superconducting-calibrations"`. Resolve before publishing to PyPI.
- [ ] `qualibration_graphs/superconducting/pyproject.toml` references `readme = "../README.md"` — see `qualibration_graphs/README.md` (placeholder replacing the shared parent readme from monolithic qua-libs)
