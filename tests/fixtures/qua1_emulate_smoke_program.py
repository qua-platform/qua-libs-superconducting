"""QUA 1 (qm-qua 1.x) twin of `qua2_emulate_smoke_program.py`.

Same elements, pulses, ports, and sweep as the QUA 2 fixture, written in QUA 1 / 1.4.0
syntax and config schema. It cannot be loaded in this repo's qm-qua 2 environment. The
committed `qua1_emulate_smoke_program.proto.json` is its `export_qua_proto.py` output,
regenerated from the `../qua-libs` Poetry env (qm-qua 1.x):

    cd ../qua-libs && poetry run python ../qua-libs-superconducting/scripts/export_qua_proto.py \\
        ../qua-libs-superconducting/tests/fixtures/qua1_emulate_smoke_program.py \\
        --output ../qua-libs-superconducting/tests/fixtures/qua1_emulate_smoke_program.proto.json

The explicit `align()` per iteration mirrors the implicit align QUA 2 places around each
`@shot` call, so both fixtures describe the same pulse schedule.
"""

from qm.qua import *
from qm import QuantumMachinesManager

qop_ip = "127.0.0.1"
qop_port = None
cluster_name = "smoke-test"

config = {
    "controllers": {
        "con1": {
            "type": "opx1000",
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
            "singleInput": {"port": ("con1", 1, 1)},
            "intermediate_frequency": 100e6,
            "operations": {"pulse_single": "pulse_single"},
        },
        "qe_mixed": {
            "mixInputs": {
                "I": ("con1", 1, 2),
                "Q": ("con1", 1, 3),
                "lo_frequency": 5e9,
                "mixer": "mixer_qe_mixed",
            },
            "intermediate_frequency": 100e6,
            "operations": {"pulse_mixed": "pulse_mixed"},
        },
    },
    "pulses": {
        "pulse_single": {
            "operation": "control",
            "length": 400,
            "waveforms": {"single": "wf_single"},
        },
        "pulse_mixed": {
            "operation": "control",
            "length": 800,
            "waveforms": {"I": "wf_mixed_i", "Q": "wf_mixed_q"},
        },
    },
    "waveforms": {
        "wf_single": {"type": "constant", "sample": 0.3},
        "wf_mixed_i": {"type": "constant", "sample": 0.2},
        "wf_mixed_q": {"type": "constant", "sample": 0.1},
    },
    "mixers": {
        "mixer_qe_mixed": [
            {"intermediate_frequency": 100e6, "lo_frequency": 5e9, "correction": [1.0, 0.0, 0.0, 1.0]},
        ],
    },
}


with program() as qua1_emulate_smoke:
    a = declare(fixed)
    with for_(a, 0.1, a < 1.0, a + 0.2):
        play("pulse_single", "qe_single", amplitude_scale=a)
        play("pulse_mixed", "qe_mixed")
        align()

qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name)
