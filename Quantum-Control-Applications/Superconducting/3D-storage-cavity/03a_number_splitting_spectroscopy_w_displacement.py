"""
        NUMBER SPLITTING SPECTROSCOPY WITH DISPLACEMENT
This sequence involves sending a cw pulse to the storage cavity (displacing the storage)
followed by a selective pi-pulse (x180_long) to qubit and measure across various qubit drive intermediate dfs.

The data is post-processed to determine the distance between different Fock states in the frequency domain.

Prerequisites:
    - Identification of the resonator's resonance frequency when coupled to the qubit in question (referred to as "resonator_spectroscopy").
    - Calibration of the IQ mixer connected to the resonator drive line (whether it's an external mixer or an Octave port).
    - Identification of the qubit's resonance frequency (referred to as "qubit_spectroscopy").
    - Calibration of the IQ mixer connected to the qubit drive line (whether it's an external mixer or an Octave port).
    - Having calibrated qubit pi pulse (x180_len) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - Specification of the expected storage_thermalization_time of the storage in the configuration.

Before proceeding to the next node:
    - Update the resonance frequency of the qubit when the storage cavity is at Fock state n=1, labeled as "qubit_IF_n1".
"""

from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from qm import QuantumMachinesManager
from qm import SimulationConfig
from configuration import *
from qualang_tools.results import progress_counter, fetching_tool
from qualang_tools.plot import interrupt_on_close
from qualang_tools.loops import from_array
import matplotlib.pyplot as plt
import macros as macros
import numpy as np
from qualang_tools.results.data_handler import DataHandler


##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 500  # The number of averages

center = 177 * u.MHz
top = 3 * u.MHz
bottom = -3 * u.MHz
df = 10 * u.kHz
dfs = np.arange(bottom, top, df).astype(int)  # Qubit detuning sweep

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "center_frequency": center,
    "dfs": dfs,
    "config": config,
}

###################
# The QUA program #
###################
with program() as number_splitting_spectroscopy:
    shots = QuaIterableRange("shots", n_avg)
    df_sweep = QuaIterable("df", dfs)
    n = declare(int)  # QUA variable for the averaging loop
    state = declare(bool)
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'
    state_st = declare_output_stream()

    for shot in shots:
        assign(n, shot)
        save(n, n_st)
        for df in df_sweep:
            I = declare_with_stream(fixed, "I", average_axes=["shots"])
            Q = declare_with_stream(fixed, "Q", average_axes=["shots"])
            state = declare_with_stream(bool, "state", average_axes=["shots"])
            # Update the frequency of the digital oscillator linked to the qubit element
            update_frequency("qubit", df + center)
            # Play a displacement pulse to the storage
            play("cw", "storage")
            align("qubit", "storage")
            # Align the two elements to measure after playing the storage pulse.
            # Measure the storage state by applying a selective pi-pulse to the qubit and measure the qubit state
            play("x180_long", "qubit")
            align("qubit", "resonator")
            # Measure the state of the resonator
            state, I, Q = macros.readout_macro(threshold=ge_threshold, state=state, I=I, Q=Q)

            # Wait for the storage to decay to the ground state
            align("storage", "resonator")
            wait(storage_thermalization_time * u.ns, "storage")
            # Save the 'I' & 'Q' quadratures to their respective streams

    with stream_processing():
        # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
        state_st.boolean_to_int().buffer(len(dfs)).average().save("state")
        n_st.save("iteration")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################
simulate = True

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=10_000)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = qmm.simulate(config, number_splitting_spectroscopy, simulation_config)
    # Get the simulated samples
    samples = job.get_simulated_samples()
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
    qm = qmm.open_qm(controller_config)
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.execute(number_splitting_spectroscopy, config=logical_config)
    # Get results from QUA program
    results = fetching_tool(job, data_list=["I", "Q", "state", "iteration"], mode="live")
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
        fig1.suptitle(f"Number Splitting Spectroscopy - LO = {storage_LO / u.GHz} GHz")
        ax1[0].clear()
        ax1[1].clear()
        ax1[0].cla()
        ax1[0].plot((dfs + center) / u.MHz, I, ".")
        ax1[0].set_xlabel("Qubit intermediate frequency [MHz]")
        ax1[0].set_ylabel(r"I [V]")
        ax1[1].cla()
        ax1[1].plot((dfs + center) / u.MHz, Q, ".")
        ax1[1].set_xlabel("Qubit intermediate frequency [MHz]")
        ax1[1].set_ylabel("Q [V]")
        plt.pause(1)
        plt.tight_layout()

        ax2.clear()
        ax2.plot((dfs + center) / u.MHz, state, ".")
        ax2.set_ylabel(r"$P_e$")
        ax2.set_xlabel("Qubit intermediate frequency [MHz]")
        ax2.set_ylim(0, 1)
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
