"""Builds a small, hardware-free QUAM state used only by the overnight smoke tests.

This mirrors the repo's own `quam_config/generate_quam.py` +
`quam_config/populate_quam_lf_mw_fems.py` workflow (3 qubits in a chain, both
CZ flux-pulse shapes, standard single-qubit gate set), just trimmed down and
made non-interactive so it can run unattended in CI.

It is deliberately *not* a faithful stand-in for a real chip. Gaps in this fake
machine (missing pulses, unset scalar fields, CZ routing) are filled with dummy
values below. What is NOT simulated in this file: nodes that gate on another node's output.
Those stay in `known_broken.txt`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from qualang_tools.units import unit
from qualang_tools.wirer import Connectivity, Instruments, allocate_wiring
from qualang_tools.wirer.wirer.channel_specs import mw_fem_spec
from qualibrate import QualibrationNode
from quam.components.pulses import DragCosinePulse, SquarePulse
from quam_builder.architecture.superconducting.custom_gates.flux_tunable_transmon_pair.two_qubit_gates import (
    CZGate,
)
from quam_builder.builder.qop_connectivity import build_quam_wiring
from quam_builder.builder.superconducting import build_quam
from quam_builder.builder.superconducting.add_default_pulses import add_DragCosine_pulses
from quam_builder.common.pulses import FlatTopGaussianPulse
from quam_config import Quam

try:
    from quam_builder.common.pulses import DrachmaReadoutPulse
except ImportError:  # quam-builder < 0.5.0 has no DrachmaReadoutPulse
    DrachmaReadoutPulse = None

QUBIT_IDS = [1, 2, 3]
QUBIT_PAIRS = [(1, 2), (2, 3)]


def _qubit_id(name: str) -> int:
    return int(str(name).removeprefix("q"))


def install_default_qubit_groups() -> None:
    """Give nodes a `qubit_groups` value when they were constructed without one.

    Some nodes default that parameter to None and then refuse to build. The value
    is not stored on the QUAM; it has to be set on the node before its module-level
    actions run. Deriving it here keeps the chain next to the wiring that makes
    the consecutive pairs real.
    """
    # build_fake_quam can run more than once in a process. Wrapping twice would
    # nest this patch.
    if getattr(QualibrationNode.__init__, "_smoke_fills_qubit_groups", False):
        return
    original_init = QualibrationNode.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        parameters = getattr(self, "parameters", None)
        if parameters is None or getattr(parameters, "qubit_groups", "absent") is not None:
            return
        names = [f"q{i}" for i in QUBIT_IDS if f"q{i}" in self.machine.qubits]
        parameters.qubit_groups = ["-".join(names)]

    patched_init._smoke_fills_qubit_groups = True
    QualibrationNode.__init__ = patched_init


def _seed_static_placeholders(qubit) -> None:
    """Fill static config the populate script leaves empty but that nodes read as plain fields.

    Rule of thumb: seed a value only if the node would otherwise die on an incidental `None`
    or a missing operation (a gap in *our* fake machine). Do NOT seed outputs of another
    calibration node that the node explicitly gates on. Those stay in `known_broken.txt`.
    """
    # Operations that a calibration would normally create or tune.
    qubit.xy.operations["EF_x180"] = DragCosinePulse(
        amplitude=0.1,
        length=40,
        alpha=0.0,
        anharmonicity=qubit.get_reference() + "/anharmonicity",
        axis_angle=0.0,
        detuning=0,
    )
    qubit.resonator.operations["const"] = SquarePulse(length=1000, amplitude=0.05)
    if DrachmaReadoutPulse is not None:  # quam-builder >= 0.5.0 (pinned to v0.6.0)
        qubit.resonator.operations["readout_drachma"] = DrachmaReadoutPulse(
            length=2000,
            amplitude=0.05,
            kappa_ground_hz=5e5,
            kappa_excited_hz=5e5,
            detuning_ground_hz=-5e5,
            detuning_excited_hz=5e5,
        )

    # Plain scalar fields that default to None; programs only need them to be numbers.
    qubit.chi = 0.5e6
    qubit.resonator.GEF_frequency_shift = -1e6
    qubit.resonator.gef_centers = [[0.0, 0.0], [0.1, 0.0], [0.2, 0.0]]  # (I, Q) of g, e, f
    readout = qubit.resonator.operations["readout"]
    readout.threshold = 0.0  # active-reset / state-discrimination threshold
    readout.rus_exit_threshold = 0.0


def build_fake_quam(state_path: Path) -> Path:
    """Build and save a minimal 3-qubit, 2-pair QUAM state at `state_path`.

    Callers must set the `QUAM_STATE_PATH` env var to `state_path` *before*
    calling this (quam-builder's wiring/build helpers read/write through
    `Quam.load()`/`machine.save()`, which resolve the state path from that
    env var).
    """
    instruments = Instruments()
    instruments.add_mw_fem(controller=1, slots=[1, 2])
    instruments.add_lf_fem(controller=1, slots=[3])

    resonator_channel = mw_fem_spec(con=1, slot=1, in_port=1, out_port=1)
    drive_channel = mw_fem_spec(con=1, slot=1, in_port=None, out_port=None)

    connectivity = Connectivity()
    connectivity.add_resonator_line(qubits=QUBIT_IDS, constraints=resonator_channel)
    connectivity.add_qubit_drive_lines(qubits=QUBIT_IDS, constraints=drive_channel)
    connectivity.add_qubit_flux_lines(qubits=QUBIT_IDS)
    connectivity.add_qubit_pair_flux_lines(qubit_pairs=QUBIT_PAIRS)
    allocate_wiring(connectivity, instruments)

    machine = Quam()
    build_quam_wiring(connectivity, host_ip="127.0.0.1", cluster_name="smoke", quam_instance=machine)
    machine = Quam.load()
    build_quam(machine)

    u = unit(coerce_to_integer=True)

    resonator_freqs = np.array([4.395, 4.412, 4.429]) * u.GHz
    resonator_lo = 4.3 * u.GHz
    for qubit in machine.qubits.values():
        k = _qubit_id(qubit.name) - 1
        qubit.resonator.f_01 = float(resonator_freqs[k])
        qubit.resonator.RF_frequency = qubit.resonator.f_01
        qubit.resonator.opx_output.upconverter_frequency = resonator_lo
        qubit.resonator.opx_input.band = 1
        qubit.resonator.opx_output.band = 1

    xy_freqs = np.array([6.012, 6.421, 6.833]) * u.GHz
    xy_los = np.array([6.0, 6.1, 6.5]) * u.GHz
    anharmonicities = np.array([150, 200, 180]) * u.MHz
    for qubit in machine.qubits.values():
        k = _qubit_id(qubit.name) - 1
        qubit.f_01 = float(xy_freqs[k])
        qubit.xy.RF_frequency = qubit.f_01
        qubit.xy.opx_output.upconverter_frequency = float(xy_los[k])
        qubit.xy.opx_output.band = 1
        qubit.grid_location = f"{k},0"
        qubit.anharmonicity = float(anharmonicities[k])

    for qubit in machine.qubits.values():
        if hasattr(qubit, "z"):
            qubit.z.opx_output.output_mode = "amplified"
            qubit.z.opx_output.upsampling_mode = "pulse"

    for q in machine.qubits:
        machine.qubits[q].resonator.operations["readout"].length = int(2.5 * u.us)
        machine.qubits[q].resonator.depletion_time = int(2.5 * u.us)
        machine.qubits[q].resonator.operations["readout"].amplitude = 0.05
        machine.qubits[q].xy.operations["saturation"].length = int(20 * u.us)
        machine.qubits[q].xy.operations["saturation"].amplitude = 0.1
        add_DragCosine_pulses(
            machine.qubits[q],
            amplitude=0.1,
            length=40,
            anharmonicity=machine.qubits[q].get_reference() + "/anharmonicity",
            alpha=0.0,
            detuning=0,
        )
        if hasattr(machine.qubits[q], "z"):
            machine.qubits[q].z.flux_point = "joint"
        _seed_static_placeholders(machine.qubits[q])

    for control_id, target_id in QUBIT_PAIRS:
        pair_id = f"q{control_id}-{target_id}"
        # Control = the higher-f01 qubit, exactly as `populate_quam_lf_mw_fems.py` does.
        ids = sorted(
            (control_id, target_id),
            key=lambda i: machine.qubits[f"q{i}"].f_01,
            reverse=True,
        )
        if pair_id not in machine.qubit_pairs:
            control = machine.qubits[f"q{ids[0]}"].get_reference()
            target = machine.qubits[f"q{ids[1]}"].get_reference()
            pair = machine.qubit_pair_type(id=pair_id, qubit_control=control, qubit_target=target)
            machine.qubit_pairs[pair_id] = pair
            if pair_id not in machine.active_qubit_pair_names:
                machine.active_qubit_pair_names.append(pair_id)

        pair = machine.qubit_pairs[pair_id]
        # CZ via |11> <-> |20> in the high-frequency qubit: if the detuning exceeds the control's
        # anharmonicity the control (high-f) moves, otherwise the target does. Same rule as the
        # populate script and `QubitRoles.resolve`, so the flux pulses land on the right Z line.
        delta = pair.qubit_control.f_01 - pair.qubit_target.f_01
        pair.moving_qubit = "control" if delta > abs(pair.qubit_control.anharmonicity) else "target"
        moving_qubit = pair.qubit_control if pair.moving_qubit == "control" else pair.qubit_target

        cz_pulse = SquarePulse(length=100, amplitude=0.1, id="cz_unipolar_pulse")
        cz = CZGate(flux_pulse_qubit=cz_pulse, coupler_flux_pulse=None)
        pair.macros["cz_unipolar"] = cz
        pulse_name = pair.macros["cz_unipolar"].flux_pulse_qubit_label
        moving_qubit.z.operations[pulse_name] = SquarePulse(length=100, amplitude=0.1)

        cz_pulse2 = FlatTopGaussianPulse(amplitude=0.1, flat_length=100, length=124, id="cz_flattop_pulse")
        cz2 = CZGate(flux_pulse_qubit=cz_pulse2, coupler_flux_pulse=None)
        pair.macros["cz_flattop"] = cz2
        pulse_name2 = pair.macros["cz_flattop"].flux_pulse_qubit_label
        moving_qubit.z.operations[pulse_name2] = FlatTopGaussianPulse(amplitude=0.1, flat_length=100, length=124)

    machine.save()
    install_default_qubit_groups()
    return state_path
