# Getting Started with the QUA Emulator

The QUA Emulator generates a visual representation of a QUA program's full pulse sequence in about a second. Click any pulse to jump to the source line that produced it. Step through loop iterations to see how the sequence varies across parameters.

The emulator is built for **QUA 2**, released alongside QOP 4. The main thing QUA 2 introduces is the **shot**: a block of timing-critical code that runs gap-free, because the heavy preparation work happens outside it. QUA 1 support is planned for a future release.

It is not a hardware simulator. It uses static analysis, which is what makes it fast. That fits QUA 2 well: because shots are designed to be gap-free, what the emulator shows you matches what will actually run on hardware. For QUA 1 it would have been less useful, since computation-induced gaps there only show up at runtime.

> **Note:** Two situations where the emulated sequence will not match what runs on hardware: feedback latency (the emulator assumes zero latency for conditional operations) and any delays between shots (inter-shot gaps depend on runtime conditions the emulator does not model).

![Main Screen](./assets/main-screen.png)
---

## Try it without installing

Open [qua2-playground.develop.quantum-machines.co](https://qua2-playground.develop.quantum-machines.co). You can edit a QUA 2 program in the browser and the emulator output updates as you go.

For QUA 1 / QOP 3 programs, see [qua-playground.develop.quantum-machines.co](https://qua-playground.develop.quantum-machines.co).

> **Note:** Both links are currently accessible within the QM network only.

## Install the Python package

Install the wheel file provided by QM:

```bash
pip install path/to/qua_emulator-<version>-py3-none-any.whl
```

For QUA 2 / QOP 4 you may also need to install the custom `qm-qua` wheel shipped alongside it:

```bash
pip install path/to/qm_qua-<version>-py3-none-any.whl
```

## Your first emulation

```python
from qm.qua import *
from qua_emulator import QuaEmulator
from qua_emulator.plot import plot_state

config = {
    # See examples/config.py for a minimal working config.
    ...
}

@shot
def play_two(a):
    play("pulse_single" * amp(a), "qe_single")
    play("pulse_mixed", "qe_mixed")

with program() as prog:
    a = declare(fixed)
    with for_(a, 0.1, a < 1.0, a + 0.2):
        play_two(a)

state = QuaEmulator().evaluate(prog, config)
plot_state(state)
```

A browser tab opens with the visualization. If you're in a notebook, the plot renders inline.

<!-- TODO: screenshot — annotated playground view with callouts pointing to analog/digital lanes, click-to-source, hover tooltip, and the loop selector -->

## Reading the visualization

- Each element gets its own row, with separate analog and digital lanes. Use the channel filter to hide rows you don't care about.
- Clicking a pulse jumps to the source line that produced it. The mapping prefers your original Python; for compiler-generated pulses it falls back to the raw QUA AST.
- Hovering shows the element, pulse name, intermediate frequency, and timing.
- Drag and scroll to zoom and pan.
- The loop view toggle switches between *unrolled* (every iteration laid out in time) and *loop-indexed* (one iteration shown, with arrows to step through and see how the sequence varies).

---

## The API in 30 seconds

```python
from qua_emulator import QuaEmulator, QuaEmulatorOptions

evaluator = QuaEmulator(QuaEmulatorOptions(time_delay_lf_ns=48))
state = evaluator.evaluate(prog, config)
```

`state` is a `QuaProgramState`. It holds the parsed sequence plus four layers of enrichment: config metadata, timing, sample waveforms, and output signals. You can iterate `state.sequence` directly, or pass `state` to `plot_state()` for the interactive view.

For higher-fidelity timing (matching what the FPGA actually does), pass a waveform report from the QM simulator as a third argument:

```python
state = evaluator.evaluate(prog, config, job.get_simulated_waveform_report())
```

See `examples/02_simple_waveform_report.py` for the full pattern.

## Injecting measurement results

The emulator does not perform measurements. To run programs that depend on measurement results or feedback, plug in an **input handler** that supplies values at `measure` and `pause` points:

```python
from qua_emulator.input import FixedMeasureResultHandler
# Full examples: examples/04_inject_measure_result.py through 08_multiple_input_handlers.py
```

Examples `04` through `08` in the repo cover the common patterns: fixed measurement results, input streams, loopback (one element's output feeds another's input), and chaining multiple handlers.

## When to use the simulator instead

The emulator is built for the development loop: fast feedback, full-sequence view, source linking. Use the QM simulator instead when you need:

- Conditional feedback that depends on full FPGA semantics
- Complex control-flow patterns that static analysis doesn't yet support
- Exact hardware-equivalent traces, for example to cross-check against measured data

The validation team's **QUA Validator** runs both the emulator and the simulator and flags discrepancies. That is what keeps the emulator in sync with what QUA actually does.

---

## Next steps

- For runnable examples, see the `examples/` directory in the repo.
- For a programmatic walkthrough, read `qua_emulator/QuaEmulator.py` and the enrichment pipeline under `qua_emulator/enrichment/`.
