from qm.qua import *
from qm.qua.extensions import QuaIterable, QuaIterableRange
from configuration import *
from qm import QuantumMachinesManager
from qua_libs_core.telemetry import (
    start_qca_telemetry,
    trace_execute,
    trace_fetching,
    trace_open_qm,
    trace_qmm,
)
import matplotlib.pyplot as plt
import numpy as np
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close

n_avg = 100

cooldown_time = 5 * qubit_T1 // 4

a_min = -1
a_max = 1
da = 0.05
amps = np.arange(a_min, a_max + da / 2, da)  # + da/2 to add a_max to amplitudes

iter_min = 0
iter_max = 25
d = 1
iters = np.arange(iter_min, iter_max + 0.1, d)

resonator_cooldown = 500

with program() as drag:
    shots = QuaIterableRange("shots", n_avg)
    a_sweep = QuaIterable("a", amps)
    it = declare(int)
    pulses = declare(int)
    I_g = declare(fixed)
    n = declare(int)  # QUA variable for the averaging loop
    n_st = declare_output_stream()  # Stream for the averaging iteration 'n'

    for shot in shots:
        assign(n, shot)
        save(n, n_st)
        for a in a_sweep:
            I = declare_with_stream(fixed, "I", average_axes=["shots"])
            Q = declare_with_stream(fixed, "Q", average_axes=["shots"])
            state = declare_with_stream(int, "state", average_axes=["shots"])
            with for_(it, iter_min, it <= iter_max, it + d):
                measure("readout", "resonator", dual_demod.full("rotated_cos", "rotated_sin", I_g))
                # To prepare the ground state we used -0.0003 which is a more strict threshold (3 sigma)
                # to guarantee higher ground state fidelity
                with while_(I_g > -0.0003):
                    measure("readout", "resonator", dual_demod.full("rotated_cos", "rotated_sin", I_g))
                align()
                wait(resonator_cooldown)
                with for_(pulses, iter_min, pulses <= it, pulses + d):
                    play("x180", "qubit", amplitude_scale=(1, 0, 0, a))
                    play("x180", "qubit", amplitude_scale=(-1, 0, 0, -a))
                align("qubit", "resonator")
                measure(
                    "readout",
                    "resonator",
                    dual_demod.full("rotated_cos", "rotated_sin", I),
                    dual_demod.full("rotated_minus_sin", "rotated_cos", Q),
                )
            assign(state, I > ge_threshold)

    with stream_processing():
        n_st.save("iteration")
#####################################
#  Open Communication with the QOP  #
#####################################
telemetry = start_qca_telemetry(__file__)

qmm = trace_qmm(QuantumMachinesManager)(host="192.168.88.10", port=80)
# Open quantum machine
qm = trace_open_qm(qmm.open_qm)(controller_config, close_other_machines=False)
# Execute QUA program
job = trace_execute(qm.execute)(drag, config=logical_config)

# Get results from QUA program
results = trace_fetching(fetching_tool)(job, data_list=["state", "iteration"], mode="live")
# Live plotting
fig = plt.figure()
interrupt_on_close(fig, job)  # Interrupts the job when closing the figure

while results.is_processing():
    # Fetch results
    state, iteration = results.fetch_all()
    # Progress bar
    progress_counter(iteration, n_avg, start_time=results.get_start_time())
    # Plot results
    plt.cla()
    plt.pcolor(iters, amps * drag_coef, state, cmap="magma")
    plt.axhline(y=0.01)
    plt.xlabel("drag coef")

# Close quantum machine
qm.close()

telemetry.end()
