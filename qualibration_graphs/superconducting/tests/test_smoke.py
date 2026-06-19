"""Smoke-test scaffold for superconducting-calibrations.

Replace with real tests as the calibration nodes gain coverage. The import
check skips unless the package is installed into the test environment; the CI
`test` job runs pytest without the heavy quam-builder / qualibration-libs git
dependencies for now (see the workflow notes for how to enable a full install).
"""

import pytest


def test_package_importable():
    pytest.importorskip("quam_config")
