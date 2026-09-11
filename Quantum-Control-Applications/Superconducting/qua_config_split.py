"""Split and merge QUA configuration dicts (controller vs logical).

Canonical implementation: ``qua_libs_core.qua_config``. This module re-exports
that API and keeps a local copy if the pinned core branch is not installed yet.
"""

from __future__ import annotations

from typing import Any

try:
    from qua_libs_core.qua_config import (  # noqa: F401
        CONTROLLER_KEYS,
        LOGICAL_KEYS,
        merge_qua_config,
        split_qua_config,
    )
except ImportError:  # pragma: no cover - until qua-libs-core QL-1212-qua141-py314 is installed
    CONTROLLER_KEYS = ("controllers", "octaves", "mixers")
    LOGICAL_KEYS = (
        "oscillators",
        "elements",
        "integration_weights",
        "waveforms",
        "digital_waveforms",
        "pulses",
    )

    def split_qua_config(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        controller_config = {key: config[key] for key in CONTROLLER_KEYS if key in config}
        logical_config = {key: config[key] for key in LOGICAL_KEYS if key in config}
        return controller_config, logical_config

    def merge_qua_config(controller_config: dict[str, Any], logical_config: dict[str, Any]) -> dict[str, Any]:
        return {**controller_config, **logical_config}
