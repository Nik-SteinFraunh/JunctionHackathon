# Surface Code on IQM Emerald — Challenge Overview

## Quantum Error correction

Quantum computers are fundamentally noise-limited: every gate, every idle moment, every measurement introduces errors that accumulate faster than useful computation can proceed. 
Quantum error correction addresses this by encoding a single logical qubit across many physical qubits and continuously measuring stabilizer operators — parity checks that reveal error syndromes without collapsing the encoded information. 
Surface codes have emerged as the leading practical approach, and they map directly onto the square-lattice connectivity that superconducting processors like IQM Emerald provide.
Still, writing out a whole a whole pipeline is notoriously hard. 
The challenge you will be facing today will have you operating on the forefront of science! 

## The Pipeline

You are building and completing a proof-of-concept quantum error correction pipeline that runs a surface code on real superconducting hardware and produces a logical error rate. The full chain is:

```
(Stim circuit  →)  Qiskit  →  IQM Emerald (Resonance)  →  Syndrome extraction  →  Decoder  →  LER
```

Each stage has a clear role. Stim/ Qiskit defines the surface code circuit including stabilizer structure, qubit coordinates, detectors, and the logical observable. Stim is optional, but makes postprocessing a lot easier. The Qiskit layer translates that abstract circuit into something the hardware can execute. IQM Resonance runs the transpiled circuit and returns shot-by-shot measurement bitstrings. Syndrome extraction converts those raw bitstrings into detection events, which are what the decoder actually needs, not the raw measurements themselves. The decoder then uses those events to infer whether a logical error occurred.

In real hardware, you would then feed the information on logical errors back into the QPU and correct errors on the fly. But real hardware is limited, so this is something we cant do (yet).

**This pipeline is offline**. Decoding happens after all shots are collected. There is no requirement to feed correction results back to the QPU during coherence time.

---

## What Is Already There

### Circuit translation (`surface_code_stim.py`)

Should you wish to use Stim, the full Stim-to-Qiskit translation layer is implemented. It handles the non-trivial details: Stim uses sparse, non-contiguous qubit indices whereas Qiskit requires a contiguous `0..N-1` range, so the converter builds a dense re-indexing map. It strips all noise and annotation instructions (which exist only in Stim's simulation model and have no hardware equivalent), handles mid-circuit reset by translating Stim's `MR` instruction into a measure-then-reset pair (or ), and preserves measurement order exactly.

### Syndrome extraction (extract_syndromes.py)

The full syndrome extraction step is implemented using Stim's compile_m2d_converter(), which converts raw measurement bitstrings into detection events and observable flips in a single call. If you are working within a pure Qiskit workflow and do not want to use Stim for post-processing, you can replace this with a manual implementation: detection events are the XOR of consecutive ancilla measurement rounds (a stabilizer that changes between rounds indicates an error), and the logical observable is recovered from the parity of the final data qubit measurements. Either way, what matters for the decoder is the same output shape — a (shots, num_detectors) boolean array of detection events and a (shots, num_observables) array of logical outcomes. The dictionary also carries per-shot syndrome weights and per-detector firing rates as diagnostics: a mean syndrome weight near zero means the device is performing well; a consistently hot detector points to a miscalibrated ancilla or qubit.

### Hardware execution (`run_on_hadware.py`)

The hardware connection boilerplate is complete. It connects to IQM Resonance via `IQMProvider`, retrieves the backend, transpiles the Qiskit circuit, submits the job, and converts the returned Qiskit counts dictionary into the numpy array format the syndrome extractor expects. The Qiskit bitstring reversal (Qiskit is right-to-left, Stim is left-to-right) is handled in the helper `counts_to_measurement_array`.
**Attention here!** Automatic SWAP insertion for pairs that aren't natively adjacent on the hardware grid! You can cirumvent this by writing your own stim/qiskit-to-emerald hardware mapping.

### Utilities (`inernal_helpers.py`)

Three helper functions support the pipeline. `get_qubit_lists` classifies qubits as data or ancilla using the coordinate parity convention Stim uses for the rotated surface code: data qubits sit at odd-x, odd-y positions, ancillas at positions where at least one coordinate is even. `get_meas_order` returns qubit indices in the order they are measured, which is needed to align hardware bitstrings with Stim's measurement record. `counts_to_measurement_array` does the Qiskit-to-numpy conversion including the endianness correction. Note the docstrings flag that you should verify this logic carefully — it is worth checking against a known small circuit before trusting it at scale.

---

## What Needs To Be Built

### 1. A way to generate the surface code circuit

The pipeline currently has no entry point. `make_stim_circuit` is an empty stub — it takes no parameters and returns nothing — so nothing downstream can run. This is the first thing to complete.

Concretely, you need a function that accepts at minimum a code distance and a number of stabilizer rounds, optionally a noise model, and returns a `stim.Circuit`. Stim has a built-in generator for the rotated surface code that handles all the stabilizer structure, detector annotations, and observable definitions automatically — you don't need to write the circuit gate by gate.

One decision worth thinking about: Stim's default uses mid-circuit reset on ancilla qubits (`MR`), so each round starts with a fresh ancilla and each raw measurement directly gives that round's syndrome. An alternative is to omit the reset: the ancilla then accumulates across rounds, and each raw measurement is the XOR of all syndromes up to that point. The detector definitions are identical in both cases, but the no-reset version avoids the reset error channel (`X_ERROR` after `R`) at the cost of leaving the ancilla live and potentially decohering between rounds. Both are viable — the no-reset path is particularly relevant on hardware where resets introduce errors.

### 2. A way to decode the syndromes and compute the logical error rate

`decode_hardware_results` is stubbed and returns empty lists. The detection events and observable flips are already correctly formatted when they arrive here — `det_events` is a `(shots, num_detectors)` boolean array, `obs_flips` is `(shots, num_observables)`. What is missing is the actual decoding step and the statistical aggregation into a logical error rate and its uncertainty.

The natural choice here is minimum-weight perfect matching via PyMatching. PyMatching can build its matching graph directly from Stim's detector error model, which encodes the probabilities of each error mechanism and which detectors each error affects. Once the matcher is built, it processes all shots in a batch and returns a predicted observable flip for each shot; comparing those predictions against the actual observable flips gives the logical error count and, dividing by the number of shots, the logical error rate.

### 3. (Optional but Recommended) A simulation baseline

There is no `simulate_ler` function. Before spending QPU time, it is strongly advisable to run the same circuit through Stim's Clifford simulator with a noise model — this is essentially free computationally and validates that the circuit generation, syndrome extraction, and decoding are all working correctly end to end. A simulation baseline also gives you an expected LER to compare against the hardware result, making it possible to distinguish a coding error in your pipeline from hardware noise.

### 4. (Optional) Custom hardware qubit placement

`build_emerald_qubit_map` returns an empty dictionary. The Qiskit transpiler handles qubit placement automatically and will find a valid mapping, but it does so without knowledge of the surface code's structure. The rotated surface code has a natural diagonal connectivity that can be aligned to Emerald's square grid such that all CX pairs land on nearest-neighbour qubits — eliminating SWAP overhead entirely. The docstring in that file describes the target 5×5 sub-region and the intended layout explicitly; it is a matter of reading off the Stim qubit coordinates and mapping them to the corresponding hardware QB indices. The `print_qubit_map` function will then show you the mapping and flag any non-native pairs, so you can verify before submitting.

---

## Extensions

### Pulse-level compilation with PulLA

The current pipeline operates at the gate level and relies on Qiskit's transpiler to map to the hardware's native gate set. A more direct path is to compile the stabilizer circuit to pulses using **PulLA** (Pulse-Level Abstraction), IQM's pulse-level compilation framework. This bypasses the gate abstraction entirely and can produce significantly shallower circuits by fusing or reshaping pulses that would otherwise be separate gates. For a noise-limited experiment like this, reducing circuit depth directly translates to fewer errors before the decoder sees the syndrome, which is the most direct lever on logical error rate.
Alternatively investigate a no-reset circuit set up. Instead [TODO]

### Different decoders

PyMatching (minimum-weight perfect matching) is the natural starting point, but it is not the only option. **Union-Find decoding** is asymptotically faster and nearly as accurate near threshold. **Belief propagation** decoders can incorporate more detailed noise information. The MWPM graph itself can be weighted by calibration data from Resonance — using the actual measured two-qubit gate fidelities and T1/T2 times rather than uniform noise — which typically improves decoding accuracy on real hardware.

For a more substantial extension, the **NVIDIA Ising Predecoder** offers a hardware-accelerated decoding path. It operates on the same detection event format that `extract_syndromes` already produces, so the interface is already compatible. The `det_events` array from the syndrome extractor can be passed directly to the Ising predecoder. This route requires working through the Ising model's `MemoryCircuit` class for circuit generation (which handles native X-basis preparation and measurement and a different Stim-to-Qiskit translation), but the downstream syndrome extraction and hardware execution layers are reusable.

### Different hardware patches and code distances

The pipeline as set up targets a distance-3 rotated surface code (17 qubits) on a single 5×5 region of Emerald. Several natural extensions exist: running the same code on different 5×5 sub-regions of the chip and comparing logical error rates across regions reveals spatial variation in hardware quality. Trying distance-5 (49 qubits) would require a larger patch but fits on Emerald's full qubit count. Running multiple rounds of stabilizer measurement rather than just one round (the current hardware setting) moves the experiment toward fault-tolerant operation rather than a single-round snapshot, and gives the decoder temporal correlations to exploit.

Comparing the logical error rate across distances is the key test: a working error-correcting code should show that distance-5 outperforms distance-3 at the same physical error rate. This crossover — if you can see it in hardware data — is the most direct experimental signature of quantum error correction actually working.
