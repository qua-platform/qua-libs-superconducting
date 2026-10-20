"""
A simple sandbox to showcase different QUA functionalities during the installation.
"""

from qm.qua import *
from qm import QuantumMachinesManager, SimulationConfig
from qua_libs_core.telemetry import (
    start_qca_telemetry,
    trace_execute,
    trace_get_simulated_samples,
    trace_open_qm,
    trace_qmm,
    trace_simulate,
)
from configuration_lf_fem_and_octave import *

###################
# The QUA program #
###################
with program() as PROGRAM:
    play("cw", "rr1")
    play("cw", "q2_xy")

#####################################
#  Open Communication with the QOP  #
#####################################
telemetry = start_qca_telemetry(__file__)

qmm = trace_qmm(QuantumMachinesManager)(host=qop_ip, port=qop_port, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################

simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=1_000)  # In clock cycles = 4ns
    # Start simulation (non-blocking on OPX1000; wait before pulling results)
    job = trace_simulate(qmm.simulate)(config, PROGRAM, simulation_config)
    # Wait until the simulation is done
    job.wait_until("Done")
    # Get the simulated samples
    samples = trace_get_simulated_samples(job.get_simulated_samples)()
    # Plot the simulated samples
    samples.con1.plot()
    # Get the waveform report object
    waveform_report = job.get_simulated_waveform_report()
    # Cast the waveform report to a python dictionary
    waveform_dict = waveform_report.to_dict()
    # Visualize and save the waveform report
    waveform_report.create_plot(samples, plot=True, save_path=str(Path(__file__).resolve()))
else:
    # Open a quantum machine to execute the QUA program
    qm = trace_open_qm(qmm.open_qm)(controller_config)

    # Send the QUA program to the OPX, which compiles and executes it - Execute does not block python!
    job = trace_execute(qm.execute)(PROGRAM, config=logical_config)

telemetry.end()
