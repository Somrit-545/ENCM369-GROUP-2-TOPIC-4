# Designing Digital Logic for Smart Home and Industrial Automation Systems

**ENCM 369 — Computer Organization — Group Project (Topic 4)**

A Python simulation of digital-logic circuits and two systems built from them.
The **combinational** circuits (gates, adders, multiplexers, decoders,
comparators) are modeled at the **gate level** — every output is produced by
calling primitive Boolean gate functions, not Python arithmetic. The
**sequential** elements (flip-flops, registers, counter) and the **finite state
machines** are **behavioral** models: they use clocked Python logic to reproduce
the same input/output behavior. These blocks are then wired into a smart-home
controller and an industrial controller, and the ripple-carry adder is analyzed
for delay, gate cost, and simulation runtime.

## What it does

Running the project performs four stages in order:

1. **Verification** — 45 grouped self-checks covering the logic blocks,
   applications, and performance models (many are exhaustive over their full
   input space; invalid inputs are checked to make sure they are rejected).
2. **Smart-home demo** — a 2-to-4 command decoder, a 4-to-1 sensor multiplexer,
   a 6-bit comparator thermostat, and a DISARMED/ARMED/ALARM security FSM
   (including automatic smoke-triggered alarm).
3. **Industrial demo** — a four-phase traffic-light FSM timed by a binary
   counter, and a conveyor sorter that decodes 3-bit tags with a 3-to-8 decoder
   while a ripple-carry adder keeps a running (overflow-checked) item count.
4. **Performance analysis** — writes three PNG graphs to `figures/`: an
   analytical adder-delay model, the per-addition gate-evaluation count, and the
   measured Python simulation runtime.

> Note: the performance figures are *simulation* results, not real-hardware
> measurements. The delay graph is an analytical model in gate-delay units, the
> gate-count graph counts primitive gate-function calls (not transistors), and
> the runtime graph measures Python execution time (not hardware propagation).

## Requirements

- Python 3.9 or newer (tested on 3.12)
- `matplotlib` (only needed for the performance figures)

```bash
pip install matplotlib
```

## How to run

From the project root (the folder containing `main.py`):

```bash
python main.py            # run everything: verification, both demos, figures
python -m tests.verify    # run only the verification suite
```

Individual modules can also be run directly to see a small self-test, e.g.:

```bash
python -m logic.gates
python -m applications.smart_home
python -m applications.industrial
```

`main.py` exits with status 0 on success and non-zero if any verification check
fails or a figure cannot be produced.

## Project structure

```
.
├── main.py                     # entry point; runs the four stages in order
├── logic/                      # the reusable building blocks
│   ├── gates.py                # primitive gates (AND, OR, NOT, NAND, XOR, ...)
│   ├── combinational.py        # adders, multiplexers, decoders, comparators
│   ├── sequential.py           # D/JK/T flip-flops, register, binary counter
│   └── fsm.py                  # generic Moore finite-state-machine engine
├── applications/
│   ├── smart_home.py           # security FSM, decoder, mux, thermostat demo
│   └── industrial.py           # traffic-light FSM + conveyor sorter demo
├── analysis/
│   └── performance.py          # delay model, gate-count, runtime + figures
├── tests/
│   └── verify.py               # 45 grouped correctness/validation checks
└── figures/                    # generated PNG graphs (created on run)
```

## Notes

- Signals are the integers `0` and `1`; gate and sequential inputs validate
  their arguments and raise a clear error on anything else.
- The FSM engine defaults to **strict** mode (an undefined transition raises an
  error, which catches typos); pass `strict=False` for permissive behavior.
- An AI assistant was used to help scaffold structure, docstrings, and figure
  styling; all logic and results were reviewed and verified by the team (see the
  report's Appendix for the full AI-use disclosure).
