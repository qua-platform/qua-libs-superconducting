# QUA 1 → QUA 2 Migration Guide

> **Vendored copy.** Source: sibling [`../qm-qua-sdk`](../../qm-qua-sdk) ([`qm-qua-sdk`](https://github.com/qm-labs/qm-qua-sdk)) branch `qop4_main`, file `docs/migration/qua1-to-qua2.md`.
> Re-copy from that checkout when the migration guide changes during this branch's QUA 2 effort.
> The four recipe sections below are not the full `[2.0.0]` list — also read [`../qm-qua-sdk/CHANGELOG.md`](../../qm-qua-sdk/CHANGELOG.md) section `[2.0.0]`.

---

> **Audience.** Existing QUA 1 / QOP 3.x users (and AI coding assistants helping them) migrating code to QUA 2 / QOP 4.x.
>
> **How to use.** Each section below documents one breaking change between QUA 1 and QUA 2. Sections are independent — find the ones that match warnings/errors in your code, apply the recipe, move on.
>
> **For AI assistants.** Each section is self-contained and includes:
> - A **stable section ID** (`mixers-section-removed`) usable as a section anchor.
> - A **detection** block: regex / grep patterns and error messages that indicate the user hits this change.
> - A **before / after** code pair.
> - A **mechanical recipe** in numbered steps.
> - A **why** paragraph (helpful for judgment calls in edge cases).
>
> Apply the recipes literally where the before-pattern matches. Don't invent variants. If a user's code doesn't match any pattern in a section, leave it alone — there are corner cases (custom calibration loops, octave glue) that need human judgement.

---

## Table of contents

1. [`mixers-section-removed`](#mixers-section-removed) — Top-level `mixers` removed; `imbalance_correction` moves onto `mixInputs`
2. [`outputs-replaced-with-mix-and-single`](#outputs-replaced-with-mix-and-single) — `outputs` map replaced by symmetric `single_output` / `mix_outputs`; `singleInput`/`mixInputs` renamed to snake_case; `dual_demod` addresses are `"I"`/`"Q"`
3. [`shots-introduced`](#shots-introduced) — Programs are now organised around `@shot` methods, with typed arguments and return values
4. [`measure-process-element-output-removed`](#measure-process-element-output-removed) — `element_output` removed from `demod` / `integration` / `dual_demod`; `samples_per_chunk` / `chunks_per_window` renamed to `samples_per_slice` / `slices_per_window`

---

<a id="mixers-section-removed"></a>

## 1. `mixers` section removed; `imbalance_correction` moves onto `mixInputs`

### Detection

User code hits this change if **any** of the following is true:

- The dict config has a top-level `"mixers": {...}` key.
- A `mixInputs` block has a `"mixer"` or `"lo_frequency"` key.
- An `oscillators` entry has a `"mixer"` or `"lo_frequency"` key.
- The user calls `qm.set_mixer_correction(...)` on `QmApi` / `QmApiWithDeprecations` (V2 / OPX1000).
- The user imports `Mixer` from `qm.config._elements` or `MixerConfigType` from `qm.type_hinting.config_types`.
- `UpconvertedInputNewApi.set_mixer_correction(...)` call sites.
- `MixInput(..., mixer=..., lo_frequency=...)`, `Oscillator(..., mixer=..., lo_frequency=...)`, `UpconvertedRfInput(..., mixer=...)`, or `PhysicalConfig(..., mixers=...)` call sites.
- Loading a config raises `ValidationError: {'mixers': ['Unknown field.']}` or `Protocol message MixInputs has no "mixer" field.` or `Protocol message Oscillator has no "mixer" field.`

Grep recipe (run from project root):

```
grep -rnE '"mixers"\s*:|"mixer"\s*:\s*"|"lo_frequency"\s*:|set_mixer_correction|from qm.config[^ ]* import [^ ]*Mixer|MixerConfigType' .
```

### Before (QUA 1)

```python
config = {
    "version": 1,
    "controllers": { ... },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "lo_frequency": 5e9,
                "mixer": "mxr_qubit",
            },
            "intermediate_frequency": 100e6,
            "operations": { ... },
        },
    },
    "oscillators": {
        "osc1": {
            "intermediate_frequency": 100e6,
            "lo_frequency": 5e9,
            "mixer": "mxr_qubit",
        },
    },
    "mixers": {
        "mxr_qubit": [
            {
                "intermediate_frequency": 100e6,
                "lo_frequency": 5e9,
                "correction": (1.0, 0.05, -0.05, 0.98),
            },
        ],
    },
}

# Runtime: set the mixer correction (V2 deprecated API, removed in 2.0.0)
qm.set_mixer_correction("mxr_qubit", 100e6, 5e9, (1.0, 0.05, -0.05, 0.98))
```

### After (QUA 2)

```python
config = {
    "version": 1,
    "controllers": { ... },
    "elements": {
        "qubit": {
            "mixInputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                "imbalance_correction": (1.0, 0.05, -0.05, 0.98),
            },
            "intermediate_frequency": 100e6,
            "operations": { ... },
        },
    },
    "oscillators": {
        "osc1": {
            "intermediate_frequency": 100e6,
        },
    },
    # No "mixers" top-level entry.
}

# Runtime: update the element's imbalance correction while a job is running
job.set_element_correction("qubit", (1.0, 0.05, -0.05, 0.98))
```

> **`update_config` only accepts controller-level config**, not element/logical config. To persist a new `imbalance_correction` outside of a running job, write it back into your dict config and re-open the quantum machine. If your workflow swept LO/IF and previously called `qm.set_mixer_correction()` to apply per-(lo, if) corrections before each job, the new pattern is: rebuild the calibrated dict config and call `qmm.open_qm(updated_config)`, or run a job and call `job.set_element_correction()` per element.

### Mechanical recipe

1. **Delete the top-level `mixers` block.** It has no replacement at the top level.
2. **For each `mixInputs` block in `elements`:**
   - Delete the `"mixer"` key.
   - Delete the `"lo_frequency"` key.
   - If the element previously referenced a mixer `M` and the config had a `mixers[M]` entry with one correction matrix, copy that matrix's `correction` tuple as `"imbalance_correction"` on this `mixInputs` block.
   - If the element referenced a mixer with **multiple** correction matrices (one per `(lo_frequency, intermediate_frequency)` pair), this is a **lossy migration**: QUA 2 stores exactly one correction per element. Pick the entry whose `(lo, if)` matches the element's current `lo_frequency` + `intermediate_frequency`, and use that as the `imbalance_correction`. The other entries are dropped — if your workflow swept LO/IF and called `set_mixer_correction()` at runtime to pick the right entry, switch to calling `job.set_element_correction()` at the relevant points in your sweep instead.
3. **For each `oscillators` entry:** delete `"mixer"` and `"lo_frequency"`. Keep `intermediate_frequency`.
4. **Replace runtime `qm.set_mixer_correction(mixer, if_freq, lo_freq, values)` calls:**
   - If a job is running and you want to apply the new correction *immediately*: `job.set_element_correction(element_name, values)`. This is the only runtime path.
   - To persist the new correction in the QM's resting config, modify your dict config and re-open the quantum machine: `qm = qmm.open_qm(updated_config)`. `qm.update_config(...)` only accepts controller-level config — it cannot change an element's `mixInputs.imbalance_correction`.
   - You'll need to know *which element(s)* used mixer `mixer` — in the old model, multiple elements could share one mixer name. Each of those elements now has its own `imbalance_correction`; update them individually.
5. **Programmatic config-model code** (`qm.config._elements`):
   - Delete `from qm.config._elements import Mixer` imports. The `Mixer` class is removed.
   - `MixInput(i_port, q_port, mixer=..., lo_frequency=...)` → `MixInput(i_port, q_port, imbalance_correction=(v00, v01, v10, v11))` (or omit `imbalance_correction` for identity).
   - `Oscillator(intermediate_frequency, lo_frequency=..., mixer=...)` → `Oscillator(intermediate_frequency)`.
   - `UpconvertedRfInput(port, mixer=..., name=...)` → `UpconvertedRfInput(port, imbalance_correction=..., name=...)`.
   - `PhysicalConfig(ports=..., mixers=..., octave_ports=...)` → `PhysicalConfig(ports=..., octave_ports=...)`.
6. **Type-hints**:
   - `MixerConfigType` is removed. Replace any imports / annotations referencing it; the correction now lives as a 4-tuple on `MixInputConfigType.imbalance_correction`.
7. **Direct proto construction** (uncommon — mostly internal/benchmark code):
   - `inc_qua_config_pb2.QuaConfig.MixInputs(I=..., Q=..., mixer=..., loFrequency=...)` → `inc_qua_config_pb2.QuaConfig.MixInputs(I=..., Q=..., imbalance_correction=inc_qua_config_pb2.QuaConfig.Matrix(v00=..., v01=..., v10=..., v11=...))`.
   - `inc_qua_config_pb2.QuaConfig.Oscillator(mixer=...)` → drop the `mixer=` kwarg.
   - Any construction of `inc_qua_config_pb2.QuaConfig.MixerDec(...)`, `MixerRef(...)`, or `CorrectionEntry(...)` is dead — delete the call site.

### Why this change

The legacy model stored I/Q correction matrices in a separate top-level `mixers` map keyed by `(lo_frequency, intermediate_frequency)`, with elements (and oscillators) holding a `mixer` *name* that referenced into that map. In practice the *element* almost always had a single (lo, if) pair active at a time, so the indirection through a named mixer table was scaffolding for a sweep pattern that the gateway no longer needs to model that way.

In QOP 4 / QUA 2:

- The correction matrix lives directly on the `mixInputs` block of each element. Per-element. No name.
- LO frequency is no longer carried on the element/oscillator.
- The runtime API for changing the correction during execution is `job.set_element_correction(element, matrix)` — keyed by element, not by mixer.

This is part of the broader QUA 2 cleanup that also drops the V1 `mixers` proto messages (`MixerDec`, `MixerRef`, `CorrectionEntry`) and the V1 `MixerInfo` runtime model.

### Edge cases / gotchas

- **Multiple corrections per mixer.** If your QUA 1 config had multiple `(lo, if)` correction entries for one mixer name, migration is lossy by design. Pick the relevant entry for the element's active LO/IF; for sweeps, set the correction at sweep points using `job.set_element_correction()`.
- **Deprecated `qm.set_mixer_correction()`.** The deprecation was marked "removed in 2.0.0" — this is that removal. There is no shim.

---

<a id="outputs-replaced-with-mix-and-single"></a>

## 2. `outputs` map replaced by `single_output` / `mix_outputs`; `singleInput`/`mixInputs` renamed

### Detection

User code hits this change if **any** of the following is true:

- The dict config has an element with an `"outputs"` map (e.g. `"outputs": {"out1": ("con1", 1), "out2": ("con1", 2)}`).
- The dict config has an element with `"singleInput"` or `"mixInputs"` keys (camelCase).
- A `dual_demod.full(...)` 5-argument call passes `"out1"` / `"out2"` strings.
- Loading a config raises `ValidationError: {'<element>': {'value': {'singleInput': ['Unknown field.']}}}` (or `mixInputs`, or `outputs`).
- Direct proto access of `element.outputs`, `element.multipleOutputs`, `inc_qua_config_pb2.QuaConfig.MultipleOutputs`.

Grep recipe:

```
grep -rnE '"outputs"\s*:\s*\{|"singleInput"\s*:|"mixInputs"\s*:|"out1"\s*,|"out2"\s*,|MultipleOutputs' .
```

### Before (QUA 1)

```python
config = {
    "elements": {
        "resonator": {
            "mixInputs": {"I": ("con1", 3), "Q": ("con1", 4)},
            "outputs": {
                "out1": ("con1", 1),
                "out2": ("con1", 2),
            },
            "operations": {"readout": "readout_pulse"},
        },
        "drive": {
            "singleInput": {"port": ("con1", 5)},
            "operations": {"pi": "pi_pulse"},
        },
    },
}

with program() as p:
    I = declare(fixed)
    Q = declare(fixed)
    measure(
        "readout", "resonator",
        dual_demod.full("cos", "out1", "sin", "out2", I),
        dual_demod.full("minus_sin", "out1", "cos", "out2", Q),
    )
```

### After (QUA 2)

```python
config = {
    "elements": {
        "resonator": {
            "mix_inputs": {"I": ("con1", 3), "Q": ("con1", 4)},
            "mix_outputs": {
                "I": ("con1", 1),
                "Q": ("con1", 2),
                # Optional 4-tuple imbalance correction matrix:
                # "imbalance_correction": (1.0, 0.0, 0.0, 1.0),
            },
            "operations": {"readout": "readout_pulse"},
        },
        "drive": {
            "single_input": {"port": ("con1", 5)},
            "operations": {"pi": "pi_pulse"},
        },
    },
}

with program() as p:
    I = declare(fixed)
    Q = declare(fixed)
    measure(
        "readout", "resonator",
        dual_demod.full("cos", "I", "sin", "Q", I),
        dual_demod.full("minus_sin", "I", "cos", "Q", Q),
    )
```

### Mechanical recipe

1. **Element dict-config keys**:
   - Rename `"singleInput"` → `"single_input"`.
   - Rename `"mixInputs"` → `"mix_inputs"`.
   - Replace `"outputs": {"out1": <port>, "out2": <port>}` with `"mix_outputs": {"I": <port>, "Q": <port>}`. Optionally add `"imbalance_correction": (v00, v01, v10, v11)` for the readout I/Q imbalance.
   - Replace `"outputs": {"out1": <port>}` (single ADC) with `"single_output": {"port": <port>}`.
   - If the old config used arbitrary names like `"outputs": {"a": ..., "b": ...}`, they become `"I"`/`"Q"` under `mix_outputs` — the first becomes I, the second becomes Q.
2. **`MWInput` / `MWOutput`** are unchanged. Don't rename them.
3. **`measure` / `dual_demod` calls** (5-argument explicit form):
   - Replace `"out1"` → `"I"` and `"out2"` → `"Q"` in the `element_output1` / `element_output2` positional args.
   - The 3-argument shortcut form `dual_demod.full(iw1, iw2, target)` continues to work — the SDK now defaults to `"I"`/`"Q"` instead of `"out1"`/`"out2"`.
4. **Runtime `set_input_dc_offset_by_element` / `get_input_dc_offset_by_element` calls**: the `output` argument is now `"I"` / `"Q"` (for `mix_outputs` elements) or `"single"` (for `single_output` elements). The latter mirrors the existing convention used by `get_output_dc_offset_by_element` for `single_input` elements.
5. **Direct proto construction** (uncommon — mostly internal/benchmark code):
   - `inc_qua_config_pb2.QuaConfig.MultipleOutputs(port_references={...})` and the legacy `element.outputs` map are removed. Use `element.singleOutput.port` (an `AdcPortReference`) for a single output, or `element.mixOutputs.I` / `element.mixOutputs.Q` (each an `AdcPortReference`) plus optional `element.mixOutputs.imbalance_correction` (a `Matrix`).

### Why this change

Readout has always been at most two ADC ports — an I/Q pair — and the SDK treated the first two `outputs` map entries as I and Q regardless of their string keys. The new schema codifies that contract: `mix_outputs.I` and `mix_outputs.Q` for an IQ-demodulated readout, or `single_output.port` for a one-ADC readout. The dict keys also become snake_case (`single_input`, `mix_inputs`, `single_output`, `mix_outputs`) for symmetry across inputs and outputs.

### Edge cases / gotchas

- **`out1`/`out2` user-chosen names.** If a QUA 1 config had `"outputs": {"my_in_phase": ..., "my_quad": ...}` (non-standard names), the new layout uses `"I"` and `"Q"`, full stop — there is no escape hatch. Any `dual_demod` call previously referencing `"my_in_phase"` / `"my_quad"` must switch to `"I"` / `"Q"`.
- **More than two ADC ports.** No longer supported. The new schema rejects a third entry at config-load time.

<a id="shots-introduced"></a>

## 3. Programs are now organised around `@shot` methods

QUA 2 introduces the `@shot` decorator as the unit of a quantum experiment: the block of operations performed in one experimental run, callable multiple times. In QUA 1 there were no shots — a program was a single procedure under `with program():`. In QUA 2 that procedure is factored into one or more `@shot` methods, which can take typed arguments and produce typed return values.

### Detection

There's no warning to detect. The migration is conceptual: organise the program around `@shot` methods and pass data through their signatures instead of through shared declared variables.

### Before / after

QUA 1 — single procedure under `program()`:

```python
from qm.qua import program, declare, assign, for_, play, if_, else_

with program() as p:
    threshold = declare(int)
    flag      = declare(bool)

    with for_(...):
        assign(threshold, ...)
        with if_(threshold > 2):
            play("pi", "qubit")
            assign(flag, True)
        with else_():
            assign(flag, False)
```

QUA 2 — factor into a typed `@shot`:

```python
from qm.qua import program, for_, play, shot, if_, else_, assign, declare
from qm.qua.type_hints import QuaVariable

@shot
def run_round(threshold: QuaVariable[int]) -> QuaVariable[bool]:
    flag = declare(bool, False)
    with if_(threshold > 2):
        play("pi", "qubit")
        assign(flag, True)
    return flag

with program() as p:
    with for_(...):
        flag = run_round(<some threshold expr>)
```

<a id="measure-process-element-output-removed"></a>

## 4. `element_output` removed from `demod` / `integration` / `dual_demod`; chunk → slice naming

### Detection

User code hits this change if **any** of the following is true:

- A `demod.full`, `demod.sliced`, `demod.accumulated`, `demod.moving_window`, `integration.full`, `integration.sliced`, `integration.accumulated`, or `integration.moving_window` call passes a trailing `element_output` string.
- A `dual_demod.full`, `dual_demod.sliced`, `dual_demod.accumulated`, or `dual_demod.moving_window` call passes `element_output1` / `element_output2` strings between the integration-weight names.
- A `measure(...)` call passes a 3-tuple `("iw", "out1", target)` shortcut for an output.
- A `demod.*` or `integration.*` call uses the keyword `samples_per_chunk=` or `chunks_per_window=`.
- A `TypeError` like `demod.full() takes 3 positional arguments but 4 were given`, or an `unexpected keyword argument 'samples_per_chunk'`.

Grep recipe:

```
grep -rnE 'demod\.(full|sliced|accumulated|moving_window)\(.*"[^"]*",\s*"[^"]*"\)|samples_per_chunk|chunks_per_window' .
```

### Before (QUA 1)

```python
with program() as p:
    I = declare(fixed)
    Q = declare(fixed)
    arr = declare(fixed, size=8)

    # Single demod with explicit ADC port
    measure("readout", "resonator", None,
            demod.full("cos", I, "out1"),
            demod.full("sin", Q, "out1"))

    # Sliced demod with chunk-named params
    measure("readout", "resonator", None,
            demod.sliced("cos", arr, samples_per_chunk=8, element_output="out1"))

    # Dual demod with explicit per-quadrature ports
    measure("readout", "resonator", None,
            dual_demod.full("cos", "out1", "sin", "out2", I))

    # 3-tuple shortcut
    measure("readout", "resonator", None,
            ("cos", "out1", I))
```

### After (QUA 2)

```python
with program() as p:
    I = declare(fixed)
    Q = declare(fixed)
    arr = declare(fixed, size=8)

    # Single demod — ADC port comes from the element's single_output / mix_outputs config
    measure("readout", "resonator", None,
            demod.full("cos", I),
            demod.full("sin", Q))

    # Sliced demod with slice-named params
    measure("readout", "resonator", None,
            demod.sliced("cos", arr, samples_per_slice=8))

    # Dual demod — only the 3-arg form remains; weight 1 maps to I, weight 2 to Q
    measure("readout", "resonator", None,
            dual_demod.full("cos", "sin", I))

    # 2-tuple shortcut (3-tuple form is removed)
    measure("readout", "resonator", None,
            ("cos", I))
```

### Mechanical recipe

1. **Single demod / single integration** (`demod.full/sliced/accumulated/moving_window`, `integration.full/sliced/accumulated/moving_window`):
   - Remove the trailing `element_output` argument (positional or keyword). The ADC routing is now derived from the element's `single_output` / `mix_outputs` block.
2. **Dual demod** (`dual_demod.full/sliced/accumulated/moving_window`):
   - Use only the 3-arg form: `dual_demod.full(iw1, iw2, target)`, `dual_demod.sliced(iw1, iw2, samples_per_slice, target)`, etc.
   - Drop any `element_output1` / `element_output2` arguments between or around the weight names. `iw1` always applies to the element's I-quadrature ADC; `iw2` always applies to Q.
3. **Parameter renames**:
   - `samples_per_chunk` → `samples_per_slice` (on every `demod.*` / `integration.*` / `dual_demod.*` accumulation method)
   - `chunks_per_window` → `slices_per_window` (on every `*.moving_window` method)
4. **`measure(...)` tuple shorthand**:
   - Replace 3-tuples `("iw", "out", target)` with 2-tuples `("iw", target)`. The 2-tuple form is equivalent to `demod.full("iw", target)`.

### Why this change

The ADC port is now an intrinsic property of the element — declared once via `single_output: {port: ...}` or `mix_outputs: {I: ..., Q: ...}` — rather than re-specified at every `measure(...)` call site. This removes a redundancy where the same `"out1"` / `"out2"` (or `"I"` / `"Q"`) string was being repeated across every demod call for a given element, and prevents a class of bugs where a demod call referenced an ADC port the element didn't actually declare. The chunk → slice rename aligns the SDK vocabulary with the IR's, which uses `samples_per_slice` / `slices_per_window` natively.

### Edge cases / gotchas

- **Mixed forms.** If a single `measure(...)` call has some demod calls with `element_output` and some without, all of them now must drop the argument. There's no per-call escape hatch.
- **Custom calibration loops** that build their own `inc_qua_pb2.QuaProgram.AnalogMeasureProcess(...)` messages directly need to drop `elementOutput` / `elementOutput1` / `elementOutput2` from the proto field list, and rebuild the target field as one of `full=`, `sliced=`, `accumulated=`, `movingWindow=` on `AnalogProcessTarget` (the scalar/vector outer split is gone).


### Mechanical recipe

1. **Define a `@shot` function** at module scope wrapping the body of one experimental run.
2. **Annotate every parameter and the return** with a concrete type — `int`, `bool`, `float`, `fixed`, or a `QuaVariable[...]` generic from `qm.qua.type_hints`. Annotations are mandatory: a missing or non-specific annotation (e.g. bare `QuaVariable` without a type arg) raises `QmQuaException` at first-call time. For multi-return shots use `-> (bool, int)` or `typing.Tuple[bool, int]`.
3. **Use Python `return value`** (or `return v1, v2` for multi-return) to hand values back to the caller — no special `return_()` helper.
4. **Call the shot from `program()`**. Each call site can pass any scalar — a `QuaVariable`, a Python literal, or an arbitrary scalar expression. The decorator returns `None` (no returns), a `QuaVariable` (one return), or a tuple (multiple returns), so `result = run_round(a)` works and `result` can be used in any subsequent expression.

### Edge cases / gotchas

- **`@shot` without args or returns** is supported: `@shot def my_shot(): ...` is valid and the call site is `my_shot()`.
- **One return → unwrapped `QuaVariable`; multiple returns → tuple.** `result = single_return_shot(x)` gives back a `QuaVariable`; `flag, count = multi_return_shot(x)` gives back two.
- **Return targets are auto-declared.** The decorator allocates a caller-side `QuaVariable` per return slot, names it `shot_ret_<n>`, and wires it into the call's `return_targets`.

## 5. New `timing` parameter on `declare()`

QUA 2 adds an optional `timing` argument to `declare()` that lets you override the compiler's automatic inference of when a variable is evaluated. In most cases the compiler infers this from data-flow; use `timing` only when you need explicit control. This is a new feature with no QUA 1 equivalent — no migration is required.

| Value | Meaning |
|-------|---------|
| `"prepared"` | Variable has no measurement dependency; the compiler may hoist its computation outside the shot's critical path. |
| `"live"` | Variable is treated as measurement-dependent; its value is resolved during shot execution. |
| `None` (default) | Compiler infers timing from data-flow automatically. |

```python
@shot
def my_shot():
    prep = declare(fixed, timing="prepared")   # forced preparation-time
    live = declare(int, timing="live")         # forced live
    auto = declare(bool)                       # compiler infers (unchanged behaviour)
```
