"""
        RAMSEY CHEVRON (IDLE TIME VS FREQUENCY)
The program consists in playing a Ramsey sequence (x90 - idle_time - x90 - measurement) for different qubit intermediate
frequencies and idle times.
From the results, one can estimate the qubit frequency more precisely than by doing Rabi and also gets a rough estimate
of the qubit coherence time.

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated qubit pi pulse (x180) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - (optional) Having calibrated the readout (readout_frequency, amplitude, duration_optimization IQ_blobs) for better SNR.

Next steps before going to the next node:
    - Update the qubit frequency (qubit_IF_q) in the configuration.
"""

from qm import QuantumMachinesManager, SimulationConfig
from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from configuration import *
import matplotlib.pyplot as plt
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool
from qualang_tools.plot import interrupt_on_close
from qualang_tools.results import progress_counter
from macros import qua_declaration, multiplexed_readout
from qualang_tools.results.data_handler import DataHandler

##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 10  # The number of averages
# Qubit detuning sweep with respect to qubit_IF
freq_span = 10e6
freq_step = 0.2e6
dfs = np.arange(-freq_span, +freq_span, freq_step)

t_max = 200
t_min = 4
t_step = 6
t_delay = np.arange(t_min, t_max, t_step)  # Idle time sweep in clock cycles (Needs to be a list of integers)

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "dfs": dfs,
    "t_delay": t_delay,
    "config": config,
}

###################
# The QUA program #
###################
with program() as PROGRAM:
    shots = QuaIterableRange("shots", n_avg)
    df_sweep = QuaIterable("df", dfs)
    t_sweep = QuaIterable("t", t_delay)
    n = declare(int)  # QUA variable for the averaging loop
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'

    for shot in shots:
        assign(n, shot)
        save(n, n_st)
        for df in df_sweep:
            # Update the frequency of the two qubit elements
            update_frequency("q1_xy", df + qubit_IF_q1)
            update_frequency("q2_xy", df + qubit_IF_q2)

            for t in t_sweep:
                I1 = declare_with_stream(fixed, "I1", average_axes=["shots"])
                Q1 = declare_with_stream(fixed, "Q1", average_axes=["shots"])
                I2 = declare_with_stream(fixed, "I2", average_axes=["shots"])
                Q2 = declare_with_stream(fixed, "Q2", average_axes=["shots"])
                # qubit 1
                play("x90", "q1_xy")
                wait(t, "q1_xy")
                play("x90", "q1_xy")

                # qubit 2
                play("x90", "q2_xy")
                wait(t, "q2_xy")
                play("x90", "q2_xy")

                # Align the elements to measure after having waited a time "tau" after the qubit pulses.
                align()
                # Measure the state of the resonators
                measure("readout", "rr1", None, dual_demod.full("rotated_cos", "rotated_sin", I1), dual_demod.full("rotated_minus_sin", "rotated_cos", Q1))
                measure("readout", "rr2", None, dual_demod.full("rotated_cos", "rotated_sin", I2), dual_demod.full("rotated_minus_sin", "rotated_cos", Q2))
                # Wait for the qubit to decay to the ground state
                wait(thermalization_time * u.ns)

    with stream_processing():
        n_st.save("n")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################

simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=1_000)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = qmm.simulate(config, PROGRAM, simulation_config)
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
    try:
        # Open the quantum machine
        qm = qmm.open_qm(controller_config)
        # Send the QUA program to the OPX, which compiles and executes it
        job = qm.execute(PROGRAM, config=logical_config)
        # Prepare the figure for live plotting
        fig = plt.figure()
        interrupt_on_close(fig, job)
        # Tool to easily fetch results from the OPX (results_handle used in it)
        results = fetching_tool(job, ["n", "I1", "Q1", "I2", "Q2"], mode="live")
        # Live plotting
        while results.is_processing():
            # Fetch results
            n, I1, Q1, I2, Q2 = results.fetch_all()
            # Convert the results into Volts
            I1, Q1 = u.demod2volts(I1, readout_len), u.demod2volts(Q1, readout_len)
            I2, Q2 = u.demod2volts(I2, readout_len), u.demod2volts(Q2, readout_len)
            # Progress bar
            progress_counter(n, n_avg, start_time=results.start_time)
            # Plot
            plt.suptitle("Ramsey chevron")
            plt.subplot(221)
            plt.cla()
            plt.pcolor(4 * t_delay, dfs / u.MHz, I1)
            plt.title(f"qubit 1 I, fcent={(qubit_LO_q1 + qubit_IF_q1) / u.MHz} MHz")
            plt.ylabel("Frequency detuning [MHz]")
            plt.subplot(223)
            plt.cla()
            plt.pcolor(4 * t_delay, dfs / u.MHz, Q1)
            plt.title("qubit 1 Q")
            plt.xlabel("Idle time [ns]")
            plt.ylabel("Frequency detuning [MHz]")
            plt.subplot(222)
            plt.cla()
            plt.pcolor(4 * t_delay, dfs / u.MHz, I2)
            plt.title(f"qubit 2 I, fcent={(qubit_LO_q2 + qubit_IF_q2) / u.MHz} MHz")
            plt.subplot(224)
            plt.cla()
            plt.pcolor(4 * t_delay, dfs / u.MHz, Q2)
            plt.title("qubit 2 Q")
            plt.xlabel("Idle time [ns]")
            plt.tight_layout()
            plt.pause(1)

        # Save results
        script_name = Path(__file__).name
        data_handler = DataHandler(root_data_folder=save_dir)
        save_data_dict.update({"I1_data": I1})
        save_data_dict.update({"Q1_data": Q1})
        save_data_dict.update({"I2_data": I2})
        save_data_dict.update({"Q2_data": Q2})
        save_data_dict.update({"fig_live": fig})
        data_handler.additional_files = {script_name: script_name, **default_additional_files}
        data_handler.save_data(data=save_data_dict, name="_".join(script_name.split("_")[1:]).split(".")[0])

    except Exception as e:
        print(f"An exception occurred: {e}")

    finally:
        qm.close()
        print("Experiment QM is now closed")
        plt.show(block=True)
