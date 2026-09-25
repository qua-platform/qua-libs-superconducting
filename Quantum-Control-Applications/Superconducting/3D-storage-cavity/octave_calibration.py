"""
This file is used to run the Octave automatic mixer calibration.
"""

from qm import QuantumMachinesManager
from qua_libs_core.telemetry import (
    start_qca_telemetry,
    trace_open_qm,
    trace_qmm,
)
from configuration import *

telemetry = start_qca_telemetry(__file__)

qmm = trace_qmm(QuantumMachinesManager)(host=qop_ip, cluster_name=cluster_name, log_level="ERROR")
qm = trace_open_qm(qmm.open_qm)(config)

elements = ["qubit", "resonator", "storage", "qubit_pump"]
for element in elements:
    print("-" * 37 + f" Calibrates {element}")
    qm.calibrate_element(element)  # can provide many IFs for specific LO

telemetry.end()
