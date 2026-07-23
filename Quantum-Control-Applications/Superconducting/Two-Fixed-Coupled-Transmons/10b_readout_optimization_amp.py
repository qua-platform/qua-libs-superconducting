"""
        READOUT OPTIMISATION: FREQUENCY & AMP
This sequence involves measuring the state of the resonator in two scenarios: first, after thermalization
(with the qubit in the |g> state) and then after applying a pi pulse to the qubit (transitioning the qubit to the
|e> state). This is done while varying the readout frequency.
The average I & Q quadratures for the qubit states |g> and |e>, along with their variances, are extracted to
determine the Signal-to-Noise Ratio (SNR). The readout frequency that yields the highest SNR is selected as the
optimal choice.

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated qubit pi pulse (x180) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.

Next steps before going to the next node:
    - Update the readout frequency (resonator_IF_q) in the configuration.
"""

from qm import QuantumMachinesManager, SimulationConfig
from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from configuration import *
import matplotlib.pyplot as plt
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool, progress_counter
from macros import multiplexed_readout, qua_declaration
from qualang_tools.results.data_handler import DataHandler
from qualang_tools.analysis import two_state_discriminator

##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 1000  # Number of runs
scaling_max = 1.99
scaling_min = 0.0
scaling_step = 0.025
scalings = np.arange(scaling_min, scaling_max, scaling_step)
iq_blobs_analysis_method = "snr"  # "snr" "fidelity" or "overlap"

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "scalings": scalings,
    "config": config,
}

###################
# The QUA program #
###################
with program() as PROGRAM:
    shots = QuaIterableRange("shots", n_avg)
    a_sweep = QuaIterable("a", scalings)
    n = declare(int)  # QUA variable for the averaging loop
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'
    df = declare(int)  # QUA variable for the readout frequency
    Ig1 = declare(fixed)
    Qg1 = declare(fixed)
    Ig2 = declare(fixed)
    Qg2 = declare(fixed)
    Ig1_st = declare_output_stream()
    Qg1_st = declare_output_stream()
    Ig2_st = declare_output_stream()
    Qg2_st = declare_output_stream()
    Ie1 = declare(fixed)
    Qe1 = declare(fixed)
    Ie2 = declare(fixed)
    Qe2 = declare(fixed)
    Ie1_st = declare_output_stream()
    Qe1_st = declare_output_stream()
    Ie2_st = declare_output_stream()
    Qe2_st = declare_output_stream()

    for shot in shots:
        assign(n, shot)
        save(n, n_st)

        for a in a_sweep:
            # Reset both qubits to ground
            wait(thermalization_time * u.ns)
            # Measure the ground IQ blobs
            measure(
                "readout" * amp(a),
                "rr1",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", Ig1),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qg1),
            )
            measure(
                "readout" * amp(a),
                "rr2",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", Ig2),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qg2),
            )
            save(Ig1, Ig1_st)
            save(Qg1, Qg1_st)
            save(Ig2, Ig2_st)
            save(Qg2, Qg2_st)

            align()
            # Reset both qubits to ground
            wait(thermalization_time * u.ns)
            # Measure the excited IQ blobs
            play("x180", "q1_xy")
            play("x180", "q2_xy")
            align()
            measure(
                "readout" * amp(a),
                "rr1",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", Ie1),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qe1),
            )
            measure(
                "readout" * amp(a),
                "rr2",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", Ie2),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qe2),
            )
            save(Ie1, Ie1_st)
            save(Qe1, Qe1_st)
            save(Ie2, Ie2_st)
            save(Qe2, Qe2_st)

    with stream_processing():
        n_st.save("iteration")
        for i in range(2):
            Ig{i+1}_st.buffer(n_avg).buffer(len(scalings)).save(f"I_g_q{i}")
            Qg{i+1}_st.buffer(n_avg).buffer(len(scalings)).save(f"Q_g_q{i}")
            Ie{i+1}_st.buffer(n_avg).buffer(len(scalings)).save(f"I_e_q{i}")
            Qe{i+1}_st.buffer(n_avg).buffer(len(scalings)).save(f"Q_e_q{i}")

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
    simulation_config = SimulationConfig(duration=10_000)  # In clock cycles = 4ns
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
        qm = qmm.open_qm(config)
        # Send the QUA program to the OPX, which compiles and executes it
        job = qm.execute(PROGRAM)
        results = fetching_tool(job, data_list=["iteration"], mode="live")
        # Get progress counter to monitor runtime of the program
        while results.is_processing():
            # Fetch results
            iteration = results.fetch_all()
            # Progress bar
            progress_counter(iteration[0], len(scalings), start_time=results.get_start_time())

        # Fetch the results at the end
        results = fetching_tool(job, ["I_g_q0", "Q_g_q0", "I_e_q0", "Q_e_q0", "I_g_q1", "Q_g_q1", "I_e_q1", "Q_e_q1"])
        I_g_q1, Q_g_q1, I_e_q1, Q_e_q1, I_g_q2, Q_g_q2, I_e_q2, Q_e_q2 = results.fetch_all()
        # Process the data
        fidelity_vec = [[], []]
        ground_fidelity_vec = [[], []]
        for i in range(len(scalings)):
            _, _, fidelity_q1, gg_q1, _, _, _ = two_state_discriminator(
                I_g_q1[i], Q_g_q1[i], I_e_q1[i], Q_e_q1[i], b_print=False, b_plot=False
            )
            _, _, fidelity_q2, gg_q2, _, _, _ = two_state_discriminator(
                I_g_q2[i], Q_g_q2[i], I_e_q2[i], Q_e_q2[i], b_print=False, b_plot=False
            )
            fidelity_vec[0].append(fidelity_q1)
            fidelity_vec[1].append(fidelity_q2)
            ground_fidelity_vec[0].append(gg_q1)
            ground_fidelity_vec[1].append(gg_q2)

        # Plot the data
        fig = plt.figure()
        plt.suptitle("Readout amplitude optimization")
        plt.subplot(121)
        plt.plot(scalings * readout_amp_q1, fidelity_vec[0], "b.-", label="averaged fidelity")
        plt.plot(scalings * readout_amp_q1, ground_fidelity_vec[0], "r.-", label="ground fidelity")
        plt.title("Qubit 1")
        plt.xlabel("Readout amplitude [V]")
        plt.ylabel("Fidelity [%]")
        plt.legend()
        plt.subplot(122)
        plt.title("Qubit 2")
        plt.plot(scalings * readout_amp_q2, fidelity_vec[1], "b.-", label="averaged fidelity")
        plt.plot(scalings * readout_amp_q2, ground_fidelity_vec[1], "r.-", label="ground fidelity")
        plt.xlabel("Readout amplitude [V]")
        plt.ylabel("Fidelity [%]")
        plt.legend()
        plt.tight_layout()

        # Save results
        script_name = Path(__file__).name
        data_handler = DataHandler(root_data_folder=save_dir)
        save_data_dict.update({"I_g_q1_data": I_g_q1})
        save_data_dict.update({"Q_g_q1_data": Q_g_q1})
        save_data_dict.update({"I_e_q1_data": I_e_q1})
        save_data_dict.update({"Q_e_q1_data": Q_e_q1})
        save_data_dict.update({"I_g_q2_data": I_g_q2})
        save_data_dict.update({"Q_g_q2_data": Q_g_q2})
        save_data_dict.update({"I_e_q2_data": I_e_q2})
        save_data_dict.update({"Q_e_q2_data": Q_e_q2})
        save_data_dict.update({"fig_live": fig})
        data_handler.additional_files = {script_name: script_name, **default_additional_files}
        data_handler.save_data(data=save_data_dict, name="_".join(script_name.split("_")[1:]).split(".")[0])

    except Exception as e:
        print(f"An exception occurred: {e}")

    finally:
        qm.close()
        print("Experiment QM is now closed")
        plt.show(block=True)
