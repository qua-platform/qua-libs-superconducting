"""
        POWER RABI WITH ERROR AMPLIFICATION
This sequence involves repeatedly executing the qubit pulse (such as x180, square_pi, or similar) 'N' times and
measuring the state of the resonator across different qubit pulse amplitudes and number of pulses.
By doing so, the effect of amplitude inaccuracies is amplified, enabling a more precise measurement of the pi pulse
amplitude. The results are then analyzed to determine the qubit pulse amplitude suitable for the selected duration.

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated the IQ mixer connected to the qubit drive line (external mixer or Octave port)
    - Having found the rough qubit frequency and pi pulse duration (rabi_chevron_duration or time_rabi).
    - Having found the pi pulse amplitude (power_rabi).
    - Set the qubit frequency, desired pi pulse duration and rough pi pulse amplitude in the configuration.

Next steps before going to the next node:
    - Update the qubit pulse amplitude (pi_amp_q) in the configuration.
"""

from qm import QuantumMachinesManager, SimulationConfig
from qua_libs_core.telemetry import (
    start_qca_telemetry,
    trace_execute,
    trace_fetching,
    trace_get_simulated_samples,
    trace_open_qm,
    trace_qmm,
    trace_simulate,
)
from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from configuration import *
import matplotlib.pyplot as plt
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close
from macros import qua_declaration, multiplexed_readout
from qualang_tools.results.data_handler import DataHandler

##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 10  # The number of averages
scaling_min = 0.0
scaling_max = 1.5
scaling_step = 0.005
scalings = np.arange(scaling_min, scaling_max, scaling_step)
# repeated rabi
max_nb_of_pulses = 80  # Maximum number of qubit pulses
nb_of_pulses = np.arange(0, max_nb_of_pulses, 2)  # Always play an odd/even number of pulses to end up in the same state

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "nb_of_pulses": nb_of_pulses,
    "scalings": scalings,
    "config": config,
}

telemetry = start_qca_telemetry(__file__, params=save_data_dict)

###################
# The QUA program #
###################
with program() as PROGRAM:
    I, I_st, Q, Q_st, n, n_st = qua_declaration(nb_of_qubits=2)
    shots = QuaIterableRange("shots", n_avg)
    npi_sweep = QuaIterable("npi", nb_of_pulses.astype(int))
    a_sweep = QuaIterable("a", scalings)
    count = declare(int)

    for shot in shots:
        assign(n, shot)
        for npi in npi_sweep:
            for a in a_sweep:
                with for_(count, 0, count < npi, count + 1):
                    play("x180", "q1_xy", amplitude_scale=a)
                    play("x180", "q2_xy", amplitude_scale=a)
                align()
                multiplexed_readout(
                    I, I_st, Q, Q_st, resonators=[1, 2], weights="rotated_", amplitude=1.0
                )
                wait(thermalization_time * u.ns)
        save(n, n_st)

    with stream_processing():
        n_st.save("n")
        I_st[0].buffer(len(scalings)).buffer(len(nb_of_pulses)).average().save("I1")
        Q_st[0].buffer(len(scalings)).buffer(len(nb_of_pulses)).average().save("Q1")
        I_st[1].buffer(len(scalings)).buffer(len(nb_of_pulses)).average().save("I2")
        Q_st[1].buffer(len(scalings)).buffer(len(nb_of_pulses)).average().save("Q2")


#####################################
#  Open Communication with the QOP  #
#####################################
qmm = trace_qmm(QuantumMachinesManager)(host=qop_ip, port=qop_port, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################

simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=1_000)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = trace_simulate(qmm.simulate)(config, PROGRAM, simulation_config)
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
    try:
        # Open the quantum machine
        qm = trace_open_qm(qmm.open_qm)(controller_config)
        # Send the QUA program to the OPX, which compiles and executes it
        job = trace_execute(qm.execute)(PROGRAM, config=logical_config)
        # Prepare the figure for live plotting
        fig = plt.figure()
        interrupt_on_close(fig, job)
        # Tool to easily fetch results from the OPX (results_handle used in it)
        results = trace_fetching(fetching_tool)(job, ["n", "I1", "Q1", "I2", "Q2"], mode="live")
        # Live plotting
        while results.is_processing():
            # Fetch results
            n, I1, Q1, I2, Q2 = results.fetch_all()
            # Progress bar
            progress_counter(n, n_avg, start_time=results.start_time)
            # Convert the results into Volts
            I1, Q1 = u.demod2volts(I1, readout_len), u.demod2volts(Q1, readout_len)
            I2, Q2 = u.demod2volts(I2, readout_len), u.demod2volts(Q2, readout_len)
            # Plots
            # Power Rabi with error amplification
            plt.subplot(221)
            plt.cla()
            plt.pcolor(scalings * pi_amp_q1, nb_of_pulses, I1)
            plt.title("I1")
            plt.ylabel("# of Rabi pulses")
            plt.subplot(223)
            plt.cla()
            plt.pcolor(scalings * pi_amp_q1, nb_of_pulses, Q1)
            plt.title("Q1")
            plt.xlabel("qubit pulse amplitude [V]")
            plt.ylabel("# of Rabi pulses")
            plt.subplot(222)
            plt.cla()
            plt.pcolor(scalings * pi_amp_q2, nb_of_pulses, I2)
            plt.title("I2")
            plt.subplot(224)
            plt.cla()
            plt.pcolor(scalings * pi_amp_q2, nb_of_pulses, Q2)
            plt.title("Q2")
            plt.xlabel("Qubit pulse amplitude [V]")
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

telemetry.end()
