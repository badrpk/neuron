# neuron

`neuron` is an experimental C++17 research harness for testing a compact spiking neural network across many generated sensory patterns, random seeds, noisy inputs, training epochs, and evolutionary mutations.

## Purpose

The program studies whether a small biologically inspired network can form diverse, stable motor representations without collapsing every input onto one output. It is designed for reproducible experimentation—not for claiming scientific discovery.

## Current model

- 9 sensory inputs
- 18 hidden spiking neurons
- 9 motor neurons
- leaky integrate-and-fire dynamics
- adaptive thresholds and refractory state
- competitive pseudo-label training
- deterministic noisy evaluation
- mutation with rollback
- CSV experiment reporting

## Metrics

The harness reports initial, trained, and evolved quality together with clean target accuracy, noisy target accuracy, noise consistency, average and minimum winner margins, distinct motor usage, motor-usage entropy, and retention.

An `[UNUSUAL]` result means only that a run crossed the thresholds encoded in this harness. It is not evidence that the behaviour is new to science.

## Build

### Direct compiler

```bash
g++ -std=c++17 -O2 -Wall -Wextra -pedantic src/neuron.cpp -o neuron
```

### CMake

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
```

## Run

Test eight patterns:

```bash
./neuron 8
```

Test twelve patterns:

```bash
./neuron 12
```

Results are written to `research_results_v5.csv`.

## Reading results

```bash
(head -n 1 research_results_v5.csv && \
 tail -n +2 research_results_v5.csv | sort -t, -k4,4nr | head -10) | column -s, -t
```

Show experiments that beat their initial network:

```bash
awk -F, 'NR==1 || $7>0' research_results_v5.csv | column -s, -t
```

## Experimental interpretation

Earlier versions exposed motor collapse: a high-confidence network could map every input to one motor. The current objective penalises collapse and separately measures diversity, robustness, target alignment, and retention.

The present research question is whether noisy competitive training and bounded evolutionary search can jointly produce representations that are diverse, correctly aligned, and robust to perturbation.

## Limitations

- Generated patterns are synthetic.
- Pseudo-labels test representational capacity rather than autonomous concept discovery.
- Results require comparison with standard classifiers and clustering methods.
- Statistical significance and independent replication are not yet implemented.

## Roadmap

- repeated confidence intervals and significance tests
- baseline comparisons
- configurable network dimensions
- saved checkpoints
- adversarial perturbation tests
- unsupervised target formation
- automated regression tests

## Licence

MIT
