# Installing qua-emulator

This bundle contains two wheels that are not available on public PyPI:

- `qua_emulator-*.whl` — the emulator itself
- `qm_qua-*.whl` — the QUA SDK it depends on

All other dependencies (numpy, scipy, and qm-qua's own dependencies) are public, so
they are fetched from PyPI during installation.

## Requirements

- **Internet access** (to fetch the public dependencies from PyPI).
- **Python 3.9–3.11** per wheel metadata (see note below).
- A virtual environment is recommended.

### Python 3.14 verification (qua-libs-superconducting branch QL-983-qua2)

Tested with **Python 3.14.5** via `uv sync` and import checks in this repo:

| Package | Wheel metadata | Result on 3.14.5 |
|---------|----------------|-------------------|
| `qm-qua` 2.0.0.dev5 | `>=3.9,<3.14` | Installs and imports OK |
| `qua-emulator` 0.2.13 | `>=3.9,<3.12` | Installs and imports OK |

Wheel `Requires-Python` metadata is conservative; uv resolves and installs both on 3.14 in this project. For production use outside this repo, prefer Python 3.11–3.13 until wheels declare 3.14 support explicitly.

## Install

From the folder containing these wheels:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --find-links . qua-emulator
```

`--find-links .` makes pip use the local `qua-emulator` and `qm-qua` wheels; everything
else resolves normally from PyPI. (Do **not** add `--no-index` — that would block PyPI
and the public dependencies would fail to install.)

## Verify

```bash
python -c "from qua_emulator import QuaEmulator; print('qua-emulator OK')"
```
