from qm.qua import *
from qua_emulator import QuaEmulator
from qua_emulator.plot import plot_state

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
    "mixers": {
        "mixer1": [
            {
                "intermediate_frequency": 100e6,
                "lo_frequency": 5e9,
                "correction": [1.0, 0.0, 0.0, 1.0],
            }
        ],
    },
    "elements": {
        "qe_single": {
            "singleInput": {"port": ("con1", 1, 1)},
            "intermediate_frequency": 100e6,
            "operations": {
                "pulse_single": "pulse_single",
            },
        },
        "qe_mixed": {
            "mixInputs": {
                "I": ("con1", 1, 2),
                "Q": ("con1", 1, 3),
                "mixer": "mixer1",
                "lo_frequency": 5e9,
            },
            "intermediate_frequency": 100e6,
            "operations": {
                "pulse_mixed": "pulse_mixed",
            },
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
def play_two(a):
    play("pulse_single" * amp(a), "qe_single")
    play("pulse_mixed", "qe_mixed")

with program() as prog:
    a = declare(fixed)
    with for_(0.1, 1.0, 0.2) as a:
        play_two(a)

state = QuaEmulator().emulate(prog, config)
plot_state(state)

