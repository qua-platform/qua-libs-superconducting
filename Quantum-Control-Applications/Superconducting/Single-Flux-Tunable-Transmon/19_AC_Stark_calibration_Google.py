"""
        AC STARK-SHIFT CALIBRATION WITH DRAG PULSES (GOOGLE METHOD)
The sequence consists in applying an increasing number of x180 and -x180 pulses successively for different DRAG
detunings. Here the detuning sweep has to be performed in python, because it involves changing the DRAG waveforms in a
non-linear manner.
After such a sequence, the qubit is expected to always be in the ground state if the AC Stark shift is
properly compensated by the DRAG detuning.
One can then take a line cut for a given number of pulse and fit the 1D trace with a parabola to get the optimum
detuning and update its value in the configuration.

This protocol is described in more details in https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.117.190503

Prerequisites:
    - Having found the resonance frequency of the resonator coupled to the qubit under study (resonator_spectroscopy).
    - Having calibrated qubit pi pulse (x180) by running qubit, spectroscopy, rabi_chevron, power_rabi and updated the config.
    - (optional) Having calibrated the readout (readout_frequency, amplitude, duration_optimization IQ_blobs) for better SNR.
    - Having calibrated the DRAG coefficient.
    - Set the desired flux bias.

Next steps before going to the next node:
    - Update the DRAG detuning (AC_stark_detuning) in the configuration.
"""

from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from qm import QuantumMachinesManager
from qm import SimulationConfig
from configuration import *
from qualang_tools.results import fetching_tool
from qualang_tools.loops import from_array
from macros import readout_macro
import matplotlib.pyplot as plt
from qualang_tools.results.data_handler import DataHandler

##################
#   Parameters   #
##################
# Parameters Definition
n_avg = 100
# Detuning to compensate for the AC STark-shift
detunings = np.arange(-10e6, 10e6, 1e6)
# Scan the number of pulses
iter_min = 0
iter_max = 25
d = 1
iters = np.arange(iter_min, iter_max + 0.1, d)

# Data to save
save_data_dict = {
    "n_avg": n_avg,
    "detunings": detunings,
    "iters": iters,
    "config": config,
}

###################
# The QUA program #
###################
with program() as ac_stark_shift:
    shots = QuaIterableRange("shots", n_avg)
    it_sweep = QuaIterable("it", iters)
    pulses = declare(int)  # QUA variable for counting the qubit pulses
    n = declare(int)  # QUA variable for the averaging loop
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'

    for shot in shots:
        assign(n, shot)
        save(n, n_st)
        for it in it_sweep:
            I = declare_with_stream(fixed, "I", average_axes=["shots"])
            Q = declare_with_stream(fixed, "Q", average_axes=["shots"])
            state = declare_with_stream(int, "state", average_axes=["shots"])
            # Loop for error amplification (perform many qubit pulses with varying DRAG coefficients)
            with for_(pulses, iter_min, pulses <= it, pulses + d):
                play("x180" * amp(1), "qubit")
                play("x180" * amp(-1), "qubit")
            # Align the two elements to measure after playing the qubit pulses.
            align("qubit", "resonator")
            # Measure the resonator and extract the qubit state
            state, I, Q = readout_macro(threshold=ge_threshold, state=state, I=I, Q=Q)
            # Wait for the qubit to decay to the ground state
            wait(thermalization_time * u.ns, "resonator")
            # Save the 'I' & 'Q' quadratures to their respective streams


    with stream_processing():
        # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
        n_st.save("iteration")
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
    job = qmm.simulate(config, ac_stark_shift, simulation_config)
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
    xaxis = []
    I_tot = []
    Q_tot = []
    state_tot = []
    fig = plt.figure()
    # Since the DRAG waveforms need to be changed, we have to do it in Python
    for det in detunings:
        xaxis.append(det)
        # Derive the DRAG waveforms with the new detuning
        x180_wf, x180_der_wf = np.array(
            drag_gaussian_pulse_waveforms(
                x180_amp, x180_len, x180_sigma, alpha=drag_coef, anharmonicity=anharmonicity, detuning=det
            )
        )
        x180_I_wf = x180_wf
        x180_Q_wf = x180_der_wf
        # Update the config
        config["waveforms"]["x180_I_wf"]["samples"] = x180_I_wf.tolist()
        config["waveforms"]["x180_Q_wf"]["samples"] = x180_Q_wf.tolist()
        # Open the quantum machine with the updated config
        qm = qmm.open_qm(config)
        # Send the QUA program to the OPX, which compiles and executes it
        job = qm.execute(ac_stark_shift)
        # Get results from QUA program
        results = fetching_tool(job, data_list=["I", "Q", "state"])
        # Fetch results
        I, Q, state = results.fetch_all()
        # Convert the results into Volts
        I, Q = u.demod2volts(I, readout_len), u.demod2volts(Q, readout_len)
        I_tot.append(I)
        Q_tot.append(Q)
        state_tot.append(state)
        # Plot results
        plt.suptitle("AC stark shift calibration")
        plt.subplot(231)
        plt.cla()
        plt.pcolor(iters, xaxis, I_tot)
        plt.xlabel("# of x180-x180 pulses")
        plt.ylabel("Detuning [Hz]")
        plt.title("I [V]")
        plt.subplot(232)
        plt.cla()
        plt.pcolor(iters, xaxis, Q_tot)
        plt.xlabel("# of x180-x180 pulses")
        plt.ylabel("Detuning [Hz]")
        plt.title("Q [V]")
        plt.subplot(233)
        plt.cla()
        plt.pcolor(iters, xaxis, state_tot)
        plt.xlabel("# of x180-x180 pulses")
        plt.ylabel("Detuning [Hz]")
        plt.title("state")
        plt.subplot(212)
        plt.cla()
        plt.plot(xaxis, np.sum(I_tot, axis=1))
        plt.xlabel("DRAG detuning [Hz]")
        plt.ylabel("Sum along the iterations")
        plt.tight_layout()
        plt.pause(0.01)
    print(f"Optimal DRAG detuning = {xaxis[np.argmin(np.sum(I_tot, axis=1))]:.0f} Hz")

    # Close the quantum machines at the end in order to put all flux biases to 0 so that the fridge doesn't heat-up
    qm.close()
    # Save results
    script_name = Path(__file__).name
    data_handler = DataHandler(root_data_folder=save_dir)
    save_data_dict.update({"I_data": I})
    save_data_dict.update({"Q_data": Q})
    save_data_dict.update({"state_data": state})
    save_data_dict.update({"fig_live": fig})
    data_handler.additional_files = {script_name: script_name, **default_additional_files}
    data_handler.save_data(data=save_data_dict, name="_".join(script_name.split("_")[1:]).split(".")[0])
