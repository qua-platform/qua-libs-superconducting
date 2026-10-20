# Contributing

This repository contains QUA examples and calibration graphs for
superconducting transmons. Contributions are welcome — there are several ways
to help.

## Opening an issue

The easiest way to contribute is to open an issue: report a problem with an
example, ask a question, or propose something to add.

## Contributing code

Daily work lands on **`develop`**. `main` is updated only by merging `develop`
when a batch of work is ready to publish.

1. Fork the repository (or use a clone) and create a branch from `develop`.
2. Make your changes.
3. Run the checks under *Development* below.
4. Open a Pull Request targeting **`develop`**.
5. A maintainer reviews it and merges once it's ready. Ask for help at any step.

Do not push commits directly to `main`. Do not rebase or force-push `main`.

## Merging to main

This repository is not a versioned PyPI package. Promoting work still goes
through a Pull Request **`develop` → `main`**.

1. On `develop`, move notes from `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md)
   into a new `## [YYYY-MM-DD]` section with a non-empty body.
2. Open a Pull Request **`develop` → `main`**. Merge it once CI is green. The
   `changelog` job (PRs and pushes to `main` only) requires `CHANGELOG.md` to
   differ from current `main` and to add that dated section.

## Changelog

Keep [`CHANGELOG.md`](CHANGELOG.md) in Keep a Changelog style. Accumulate work
under `## [Unreleased]` on `develop`. Each merge to `main` needs a new dated
heading; the `changelog` CI job fails without one.

## Development

This repo uses [uv](https://docs.astral.sh/uv/) and targets Python 3.10–3.14
(uv will fetch a suitable interpreter). **CI uses Python 3.14.** QUA code targets
**qm-qua >=1.4.1,<2.0**; see the shared kit in sibling `qua-libs-core`
([guide](../qua-libs-core/qua141_migration/docs/qua-1.4.0-migration.md),
[runbook](../qua-libs-core/qua141_migration/docs/qua-1.4.0-migration-runbook.md))
and this repo’s [`qua141_migration/`](qua141_migration/).

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

### Tests

Repo-root checks (changelog gate):

```
uv run pytest tests
```

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
