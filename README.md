# Designing Digital Logic for Smart Home and Industrial Automation Systems

ENCM 369 — Computer Organization — Group Project
Topic 4: *Designing Digital Logic for Smart Home and Industrial Automation Systems*

A pure-Python, gate-level digital-logic simulator. Every circuit is built up
from primitive Boolean gates (no Python arithmetic shortcuts), verified
exhaustively, and then used to drive two realistic controllers — a smart-home
node and an industrial automation line — plus a performance/cost analysis of
the ripple-carry adder.

## Course concepts integrated (>= 5 required)
1. Boolean algebra and logic gates (incl. NAND functional completeness)
2. Combinational logic — adders, multiplexers, decoders, comparators
3. Binary arithmetic — ripple-carry addition and carry propagation
4. Sequential logic — D/JK/T flip-flops, registers, counters, clocking
5. Finite state machines as control units
6. Performance / cost trade-offs (delay and gate count vs. word width)

## Layout
```
digital_logic_project/
├── logic/
│   ├── gates.py          # primitive gates + NAND-only equivalents   (Member A)
│   ├── combinational.py  # adders, mux, decoder, comparator          (Member A)
│   ├── sequential.py     # flip-flops, register, counter, clock      (Member B)
│   └── fsm.py            # generic Moore FSM engine                  (Member B)
├── applications/
│   ├── smart_home.py     # security FSM + command decode + thermostat (Member C/D)
│   └── industrial.py     # traffic FSM + conveyor sorter             (Member C/D)
├── analysis/
│   └── performance.py    # delay/cost/runtime models + figures       (Member D)
├── tests/
│   └── verify.py         # exhaustive truth-table verification       (Member A/B)
├── figures/              # generated PNGs (fig1..fig3)
└── main.py               # runs the whole pipeline
```

## Run it
```bash
python main.py            # verification + demos + analysis + figures
python -m tests.verify    # just the verification suite
```
Requires Python 3.9+ and matplotlib (only for the figures).

## Current status
- Verification: 65/65 exhaustive checks pass.
- Figures generated: adder delay, gate count, measured runtime.
- Two application demos run end-to-end.

> AI-tool use: an AI assistant (Claude) helped scaffold the project structure,
> draft docstrings, and style the figures. All logic, verification, and results
> were reviewed and validated by the team. See the report Appendix for the
> per-member AI-use disclosure required by the course.
