"""Pytest fixtures for calibration-node import tests."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import xarray as xr

PACKAGE_DIR = Path(__file__).resolve().parent.parent


def _noop_run_action(_self: object, *_args: object, **_kwargs: object) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Register run_action handlers without executing them on module import."""

    def decorator(fn: Callable[..., object]) -> Callable[..., object]:
        return fn

    return decorator


@contextmanager
def _mock_qm_session(_qmm: object, _config: object, timeout: object = None) -> Iterator[MagicMock]:
    qm = MagicMock()
    job = MagicMock()
    job.execution_report.return_value = ""
    qm.execute.return_value = job
    yield qm


class _MockDataFetcher:
    t_start = 0

    def __init__(self, _job: object, _sweep_axes: object) -> None:
        pass

    def __iter__(self) -> Iterator[xr.Dataset]:
        yield xr.Dataset()

    def get(self, _key: str, default: object = 0) -> object:
        return default


def _mock_connect(_self: object) -> MagicMock:
    return MagicMock()


def _mock_simulate_and_plot(*_args: object, **_kwargs: object) -> tuple[None, MagicMock, MagicMock]:
    return None, MagicMock(), MagicMock()


def _make_import_safe_quam_load(original_load: Callable[..., object]) -> classmethod:
    def _import_safe_quam_load(cls: type, *args: object, **kwargs: object) -> object:
        if not args and not kwargs:
            return original_load(str(PACKAGE_DIR))
        return original_load(*args, **kwargs)

    return classmethod(_import_safe_quam_load)


@pytest.fixture(autouse=True)
def stub_calibration_execution_during_import(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent QualibrationNode run_actions and hardware I/O during import checks."""
    if request.node.originalname != "test_calibration_module_imports":
        return

    from qualibrate import QualibrationNode
    from quam_config import Quam
    from quam_builder.architecture.superconducting.qpu.base_quam import BaseQuam

    original_quam_load = Quam.load
    monkeypatch.setattr(QualibrationNode, "run_action", _noop_run_action)
    monkeypatch.setattr(Quam, "load", _make_import_safe_quam_load(original_quam_load))
    monkeypatch.setattr(BaseQuam, "connect", _mock_connect)
    monkeypatch.setattr("qualang_tools.multi_user.qm_session", _mock_qm_session)
    monkeypatch.setattr("qualibration_libs.runtime.simulate_and_plot", _mock_simulate_and_plot)
    monkeypatch.setattr("qualibration_libs.data.XarrayDataFetcher", _MockDataFetcher)
    monkeypatch.setattr("qualang_tools.results.progress_counter", lambda *_args, **_kwargs: None)
