"""Synthetic QUA 2 script used to smoke-test the emulate-based validation harness.

This is **not** a real QCA calibration script. Today's `Quantum-Control-Applications/
Superconducting/**` scripts are not yet QUA 2-shaped (no `@shot`, config still uses
QUA 1.4.0 keys) — see docs/plans/qua-2.0-migration.md for that separate effort.

This fixture is a minimal, valid QUA 2 program + config (modeled on
`qua2-wheels/test_code.py`) used only to exercise
`scripts/emulate_waveform_runner.py` end-to-end, independent of any real QCA script.
"""

from qm.qua import *
from qm import QuantumMachinesManager

qop_ip = "127.0.0.1"
qop_port = None
cluster_name = "smoke-test"

config = {
    "controllers": {
        "con1": {
            "fems": {
                1: {
                    "type": "LF",
                    "analog_outputs": {
                        1: {"delay": 36, "sampling_rate": 1e9, "output_mode": "amplified"},
                        2: {"delay": 36, "sampling_rate": 1e9, "output_mode": "amplified"},
                        3: {"delay": 36, "sampling_rate": 1e9, "output_mode": "amplified"},
                    },
                },
            },
        },
    },
    "elements": {
        "qe_single": {
            "single_input": {"port": ("con1", 1, 1)},
            "intermediate_frequency": 100e6,
            "operations": {"pulse_single": "pulse_single"},
        },
        "qe_mixed": {
            "mix_inputs": {
                "I": ("con1", 1, 2),
                "Q": ("con1", 1, 3),
                "imbalance_correction": [1.0, 0.0, 0.0, 1.0],
            },
            "intermediate_frequency": 100e6,
            "operations": {"pulse_mixed": "pulse_mixed"},
        },
    },
    "pulses": {
        "pulse_single": {"operation": "control", "length": 400, "waveform": "wf_single"},
        "pulse_mixed": {"operation": "control", "length": 800, "waveform": "wf_mixed"},
    },
    "waveforms": {
        "wf_single": {"type": "constant", "sample": 0.3},
        "wf_mixed": {"type": "constant", "sample": 0.2 + 0.1j},
    },
}


@shot
def play_two(a: fixed):
    play("pulse_single" * amp(a), "qe_single")
    play("pulse_mixed", "qe_mixed")


with program() as qua2_emulate_smoke:
    with for_(0.1, 1.0, 0.2) as a:
        play_two(a)

qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name)
