"""
        STORAGE COHERENT STATE DECAY
This sequence involves sending a cw pulse to the storage cavity (displacing the storage)
and measure after a varying time by applying a selective pi-pulse (x180_long) to qubit and measure the resonator.

The data is post-processed to determine the storage_T1 parameter, which can then be used to adjust
the storage_thermalization_time.

Prerequisites:
    - Identification of the resonator's resonance frequency when coupled to the qubit in question (referred to as "resonator_spectroscopy").
    - Calibration of the IQ mixer connected to the resonator drive line (whether it's an external mixer or an Octave port).
    - Identification of the qubit's resonance frequency (referred to as "qubit_spectroscopy").
    - Calibration of the IQ mixer connected to the qubit drive line (whether it's an external mixer or an Octave port).
    - Having calibrated qubit pi pulse (x180_len) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - Specification of the expected storage_thermalization_time of the storage in the configuration.

Before proceeding to the next node:
    - Update the storage T1 time, labeled as "storage_T1".
"""

from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from qm import QuantumMachinesManager
from qua_libs_core.telemetry import (
    start_qca_telemetry,
    trace_execute,
    trace_fetching,
    trace_get_simulated_samples,
    trace_open_qm,
    trace_qmm,
    trace_simulate,
)
from qm import SimulationConfig
from configuration import *
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.plot import interrupt_on_close
from qualang_tools.loops import from_array
import matplotlib.pyplot as plt
import macros as macros
import numpy as np
import scipy.optimize as spo
from qualang_tools.results.data_handler import DataHandler

##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 500  # The number of averages

t_min = 10000 // 4
t_max = 4000000 // 4
dt = 10000 // 4
durations = np.arange(t_min, t_max, dt)  # Duration time sweep (in clock cycles = 4ns) - minimum is 4 clock cycles

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "durations": durations,
    "config": config,
}

telemetry = start_qca_telemetry(__file__, params=save_data_dict)

###################
# The QUA program #
###################
with program() as Cavity_T1:
    shots = QuaIterableRange("shots", n_avg)
    t_sweep = QuaIterable("t", durations)
    n = declare(int)  # QUA variable for the averaging loop
    state = declare(bool)
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'
    state_st = declare_output_stream()

    for shot in shots:
        assign(n, shot)
        save(n, n_st)
        for t in t_sweep:
            I = declare_with_stream(fixed, "I", average_axes=["shots"])
            Q = declare_with_stream(fixed, "Q", average_axes=["shots"])
            # Play the displacement pulse to the cavity
            play("cw", "storage")
            # Wait a varying time after displacing the cavity
            wait(t, "storage")
            # Align the two elements to measure after playing the qubit pulse.
            # Measure the storage state by applying a selective pi-pulse to the qubit and measure the qubit state
            align("qubit", "storage")
            play("x180_long", "qubit")
            align("qubit", "resonator")
            state, I, Q = macros.readout_macro(threshold=ge_threshold, state=state, I=I, Q=Q)

            # Wait for the storage to decay to the ground state
            align("storage", "resonator")
            wait(storage_thermalization_time * u.ns, "storage")
            # Save the 'I' & 'Q' quadratures to their respective streams

    with stream_processing():
        # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
        state_st.boolean_to_int().buffer(len(durations)).average().save("state")
        n_st.save("iteration")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = trace_qmm(QuantumMachinesManager)(host=qop_ip, port=qop_port, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################
simulate = True

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=10_000)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = trace_simulate(qmm.simulate)(config, Cavity_T1, simulation_config)
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
    # Open the quantum machine
    qm = trace_open_qm(qmm.open_qm)(controller_config)
    # Send the QUA program to the OPX, which compiles and executes it
    job = trace_execute(qm.execute)(Cavity_T1, config=logical_config)
    # Get results from QUA program
    results = trace_fetching(fetching_tool)(job, data_list=["I", "Q", "state", "iteration"], mode="live")
    # Live plotting
    fig1, ax1 = plt.subplots(2, 1)
    fig2, ax2 = plt.subplots(1, 1)
    interrupt_on_close(fig1, job)  # Interrupts the job when closing the figure
    while results.is_processing():
        # Fetch results
        I, Q, state, iteration = results.fetch_all()
        # Convert results into Volts
        S = u.demod2volts(I + 1j * Q, readout_len)
        R = np.abs(S)  # Amplitude
        phase = np.angle(S)  # Phase
        # Progress bar
        progress_counter(iteration, n_avg, start_time=results.get_start_time())
        # Plot results
        fig1.suptitle(f"Storage cavity coherent state decay - LO = {storage_LO / u.GHz} GHz")
        ax1[0].clear()
        ax1[1].clear()
        ax1[0].cla()
        ax1[0].plot(4 * durations, R, ".")
        ax1[0].set_xlabel("Wait time [ns]")
        ax1[0].set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ [V]")
        ax1[1].cla()
        ax1[1].plot(4 * durations, phase, ".")
        ax1[1].set_xlabel("Wait time [ns]")
        ax1[1].set_ylabel("Phase [rad]")
        plt.pause(1)
        plt.tight_layout()

        ax2.clear()
        ax2.plot(4 * durations, state, ".")
        ax2.set_ylabel(r"$P_e$")
        ax2.set_xlabel("Wait time [ns]")
        ax2.set_ylim(0, 1)

    def func(t, A, alpha, kappa, offset, n=0):
        return A * np.exp(-np.abs(alpha) ** 2 * np.exp(-kappa * t)) + offset

    # fitting and extracting T1 #
    x0 = [-max(state) + min(state), 3, 0.79, max(state)]
    popt, pcov = spo.curve_fit(func, durations * 4 / u.ms, state, p0=x0)
    print(popt)

    fig3, ax3 = plt.subplots(1, 1)

    x = 4 * np.linspace(4e-3, np.max(durations)) / u.ms
    ax3.plot(4 * durations / u.ms, state, ".")
    ax3.plot(x, func(x, *popt))
    ax3.plot(x, func(x, *x0))
    ax3.set_ylabel(r"$P_e$")
    ax3.set_xlabel("Wait time [ns]")
    plt.show()
    # Save results
    script_name = Path(__file__).name
    data_handler = DataHandler(root_data_folder=save_dir)
    save_data_dict.update({"I_data": I})
    save_data_dict.update({"Q_data": Q})
    save_data_dict.update({"state_data": state})
    save_data_dict.update({"fig1_live": fig1})
    save_data_dict.update({"fig2_live": fig2})
    data_handler.additional_files = {script_name: script_name, **default_additional_files}
    data_handler.save_data(data=save_data_dict, name="_".join(script_name.split("_")[1:]).split(".")[0])

telemetry.end()
