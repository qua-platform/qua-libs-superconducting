"""
        READOUT OPTIMISATION: AMPLITUDE
The sequence consists in measuring the state of the resonator after thermalization (qubit in |g>) and after
playing a pi pulse to the qubit (qubit in |e>) successively while sweeping the readout amplitude.
The 'I' & 'Q' quadratures when the qubit is in |g> and |e> are extracted to derive the readout fidelity.
The optimal readout amplitude is chosen as to maximize the readout fidelity.

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated qubit pi pulse (x180) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - Having calibrated the readout frequency and updated the configuration.
    - Set the desired flux bias

Next steps before going to the next node:
    - Update the readout amplitude (readout_amp_q) in the configuration.
"""

from qm import QuantumMachinesManager
from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from qm import SimulationConfig
from configuration import *
import matplotlib.pyplot as plt
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.analysis import two_state_discriminator
from macros import multiplexed_readout, qua_declaration
from qualang_tools.results.data_handler import DataHandler

##################
#   Parameters   #
##################
# Parameters Definition
n_runs = 1
# The readout amplitude sweep (as a pre-factor of the readout amplitude)
a_min = 0.9
a_max = 1.1
da = 0.01
amplitudes = np.arange(a_min, a_max + da / 2, da)  # The amplitude vector +da/2 to add a_max to the scan


# Data to save
save_data_dict = {
    "n_runs": n_runs,
    "amplitudes": amplitudes,
    "config": config,
}

###################
# The QUA program #
###################
with program() as ro_amp_opt:
    shots = QuaIterableRange("shots", n_runs)
    a_sweep = QuaIterable("a", amplitudes)
    n = declare(int)  # QUA variable for the averaging loop
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'
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
    counter = declare(int, value=0)  # Counter for the progress bar
    counter_st = declare_output_stream()  # Stream for the counter variable

    for a in a_sweep:
        # Save the counter to get the progress bar
        save(counter, counter_st)
        for shot in shots:
            assign(n, shot)
            save(n, n_st)
            # Reset both qubits to ground
            wait(thermalization_time * u.ns)
            # Measure the ground IQ blobs
            measure("readout", "rr1",
                dual_demod.full("rotated_cos", "rotated_sin", Ig1),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qg1),
                    amplitude_scale=a,
                )
            measure("readout", "rr2",
                dual_demod.full("rotated_cos", "rotated_sin", Ig2),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qg2),
                    amplitude_scale=a,
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
            measure("readout", "rr1",
                dual_demod.full("rotated_cos", "rotated_sin", Ie1),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qe1),
                    amplitude_scale=a,
                )
            measure("readout", "rr2",
                dual_demod.full("rotated_cos", "rotated_sin", Ie2),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Qe2),
                    amplitude_scale=a,
                )
            save(Ie1, Ie1_st)
            save(Qe1, Qe1_st)
            save(Ie2, Ie2_st)
            save(Qe2, Qe2_st)
        # Increment the counter
        assign(counter, counter + 1)

    with stream_processing():
        # Save all streamed points for plotting the IQ blobs
        Ig1_st.buffer(n_runs).buffer(len(amplitudes)).save("I_g_q0")
        Qg1_st.buffer(n_runs).buffer(len(amplitudes)).save("Q_g_q0")
        Ie1_st.buffer(n_runs).buffer(len(amplitudes)).save("I_e_q0")
        Qe1_st.buffer(n_runs).buffer(len(amplitudes)).save("Q_e_q0")
        Ig2_st.buffer(n_runs).buffer(len(amplitudes)).save("I_g_q1")
        Qg2_st.buffer(n_runs).buffer(len(amplitudes)).save("Q_g_q1")
        Ie2_st.buffer(n_runs).buffer(len(amplitudes)).save("I_e_q1")
        Qe2_st.buffer(n_runs).buffer(len(amplitudes)).save("Q_e_q1")
        counter_st.save("iteration")

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
    job = qmm.simulate(config, ro_amp_opt, simulation_config)
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
    job = qm.execute(ro_amp_opt, config=logical_config)  # execute QUA program
    # Get results from QUA program
    results = fetching_tool(job, data_list=["iteration"], mode="live")
    # Get progress counter to monitor runtime of the program
    while results.is_processing():
        # Fetch results
        iteration = results.fetch_all()
        # Progress bar
        progress_counter(iteration[0], len(amplitudes), start_time=results.get_start_time())

    # Fetch the results at the end
    results = fetching_tool(job, ["I_g_q0", "Q_g_q0", "I_e_q0", "Q_e_q0", "I_g_q1", "Q_g_q1", "I_e_q1", "Q_e_q1"])
    I_g_q1, Q_g_q1, I_e_q1, Q_e_q1, I_g_q2, Q_g_q2, I_e_q2, Q_e_q2 = results.fetch_all()
    # Process the data
    fidelity_vec = [[], []]
    ground_fidelity_vec = [[], []]
    for i in range(len(amplitudes)):
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
    plt.plot(amplitudes * readout_amp_q1, fidelity_vec[0], "b.-", label="averaged fidelity")
    plt.plot(amplitudes * readout_amp_q1, ground_fidelity_vec[0], "r.-", label="ground fidelity")
    plt.title("Qubit 1")
    plt.xlabel("Readout amplitude [V]")
    plt.ylabel("Fidelity [%]")
    plt.legend()
    plt.subplot(122)
    plt.title("Qubit 2")
    plt.plot(amplitudes * readout_amp_q2, fidelity_vec[1], "b.-", label="averaged fidelity")
    plt.plot(amplitudes * readout_amp_q2, ground_fidelity_vec[1], "r.-", label="ground fidelity")
    plt.xlabel("Readout amplitude [V]")
    plt.ylabel("Fidelity [%]")
    plt.legend()
    plt.tight_layout()

    # Close the quantum machines at the end in order to put all flux biases to 0 so that the fridge doesn't heat-up
    qm.close()
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
