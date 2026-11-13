"""Runs a calibration node file up through `create_qua_program`, and no further.

Why this exists: a `QualibrationNode` file is not lazily imported. Every
`@node.run_action` fires the instant the module executes. With
default parameters that means a plain `import`/`exec` of a node file walks
straight through `execute_qua_program`, which opens a real connection to a
Quantum Machines Manager and tries to fetch results from a real job.

To stop after the nodes we want to execute (building the QUA program), we patch
`ActionManager.run_action` to raise a sentinel right after the action named 
`create_qua_program` finishes. Every node script in this repo names that action 
identically, so this works without having to enumerate the different 
simulate/execute/analysis action names each node happens to use.

`machine.connect()` is separately patched (in conftest.py) to raise instead
of silently no-op. In the normal case it's never reached because we stop
before `simulate_qua_program`/`execute_qua_program` even run; the patch exists
so a bug in this interception -- or a node that calls `connect()` from inside
`create_qua_program` itself -- fails loudly right where it happens, instead of
hanging or failing confusingly a few frames later inside `qm_session`.
"""

from __future__ import annotations

import runpy
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from qualibrate.core.qualibration_node import QualibrationNode
from qualibrate.core.runnables.run_action.action_manager import ActionManager

_STOP_AFTER_ACTION = "create_qua_program"


class ProgramBuilt(Exception):
    """Raised to unwind the node file's module-level execution right after
    `create_qua_program` finishes, before any later action can run."""

    def __init__(self, node: QualibrationNode) -> None:
        super().__init__(f"stopped after '{_STOP_AFTER_ACTION}' for node {node.name!r}")
        self.node = node


@contextmanager
def _intercept_after_create_qua_program() -> Iterator[None]:
    original_run_action = ActionManager.run_action

    def patched_run_action(self: ActionManager, action_name: str, node: QualibrationNode, *args, **kwargs):
        result = original_run_action(self, action_name, node, *args, **kwargs)
        if action_name == _STOP_AFTER_ACTION:
            raise ProgramBuilt(node)
        return result

    ActionManager.run_action = patched_run_action
    try:
        yield
    finally:
        ActionManager.run_action = original_run_action


def run_node_up_to_program(node_file: Path) -> QualibrationNode:
    """Execute `node_file` and return the node right after its QUA program is built.

    Raises `AssertionError` if the file never reaches `create_qua_program`
    (e.g. the action was renamed, or default parameters skip it). Any
    genuine error raised *inside* `create_qua_program` propagates unchanged
    so it shows up as a normal test failure.
    """
    with _intercept_after_create_qua_program():
        try:
            runpy.run_path(str(node_file), run_name="__main__")
        except ProgramBuilt as stop:
            return stop.node

    raise AssertionError(
        f"{node_file.name}: ran to completion without ever running '{_STOP_AFTER_ACTION}'. "
        "The action may have been renamed/removed, or default parameters skip it -- "
        "this node needs a look, not a known_broken.txt entry."
    )
