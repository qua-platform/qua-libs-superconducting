# Contributing

This repository contains QUA examples and calibration graphs for
superconducting transmons. Contributions are welcome — there are several ways
to help.

## Opening an issue

The easiest way to contribute is to open an issue: report a problem with an
example, ask a question, or propose something to add.

## Contributing code

1. Fork the repository and create a branch.
2. Make your changes.
3. Run the checks under *Development* below.
4. Open a Pull Request back to the main repository.
5. A maintainer reviews it and merges once it's ready. Ask for help at any step.

### Changelog

Notable changes belong in [CHANGELOG.md](CHANGELOG.md) under `## [Unreleased]`, following [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Include changelog updates in the same PR or commit as the change they describe.

## Development

This repo uses [uv](https://docs.astral.sh/uv/) and targets Python 3.10–3.14
(uv will fetch a suitable interpreter). **CI uses Python 3.14.** QUA code targets
**qm-qua 1.4.0**; see [docs/plans/qua-1.4.0-migration.md](docs/plans/qua-1.4.0-migration.md)
for iterables, auto-streaming, config split, and other migration conventions, and
[docs/plans/qua-1.4.0-migration-runbook.md](docs/plans/qua-1.4.0-migration-runbook.md)
for the step-by-step playbook (all QCA modalities, new-repo bootstrap).

Create a local environment — installs the runtime dependencies and dev tools into `.venv`:

```
uv sync
```

### Formatting — black

Code is formatted with [black](https://black.readthedocs.io/) (line length 120),
and CI enforces it. The legacy `Quantum-Control-Applications/` tree is excluded
(see `[tool.black]` in `pyproject.toml`):

```
uv run black .          # format in place
uv run black --check .  # check only (what CI runs)
```

### Linting — ruff

```
uv run ruff check .         # lint
uv run ruff check --fix .   # apply safe fixes
```

The QUA `from qm.qua import *` idiom and single-letter physics names (`I`, `Q`,
…) are intentionally ignored; see `[tool.ruff]` in `pyproject.toml`.

### Calibration package — `qualibration_graphs/superconducting`

The installable calibration package has its own build and tests:

```
cd qualibration_graphs/superconducting
uv build        # build sdist + wheel
uv run pytest -q
```

Portable QCA migration grep gates (repo root):

```
uv run pytest tests/test_qca_migration_gates.py -q
```

Note: a full test run that imports the package installs `quam-builder` and
`qualibration-libs` from git; see the `test` job notes in
`.github/workflows/ci.yml`.

## License & CLA

Contributions are subject to this project's license and a Contributor License
Agreement. The exact terms for the split repositories are still being finalized;
until then, please reach out at <info@quantum-machines.co> with any licensing
questions.
