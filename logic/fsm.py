"""
fsm.py -- A small generic finite state machine (FSM) engine.

Both application controllers (smart-home security and industrial traffic) are
expressed as FSMs on top of this engine. A Moore-style FSM is used: outputs
depend only on the current state, which is the natural model for the control
logic in embedded systems.

Course concepts demonstrated:
  * Finite state machines as control logic
  * State registers + next-state combinational logic (control unit structure)

Author: Member B (sequential logic / control)
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Hashable, List, Tuple, Any


@dataclass
class FSM:
    """
    A Moore finite state machine.

    transitions: maps (state, input_symbol) -> next_state.
    outputs:     maps state -> output value (the Moore output).
    """
    start: Hashable
    transitions: Dict[Tuple[Hashable, Hashable], Hashable]
    outputs: Dict[Hashable, Any] = field(default_factory=dict)
    state: Hashable = None

    def __post_init__(self):
        if self.state is None:
            self.state = self.start

    def reset(self) -> None:
        self.state = self.start

    def output(self) -> Any:
        return self.outputs.get(self.state)

    def step(self, symbol: Hashable) -> Hashable:
        """Consume one input symbol and move to the next state."""
        key = (self.state, symbol)
        if key not in self.transitions:
            # Undefined transition -> stay put (safe default for controllers).
            return self.state
        self.state = self.transitions[key]
        return self.state

    def run(self, symbols: List[Hashable]) -> List[Tuple[Hashable, Hashable, Any]]:
        """
        Feed a sequence of inputs and return a trace of
        (input, resulting_state, output) tuples -- handy for tables/figures.
        """
        trace = []
        for sym in symbols:
            self.step(sym)
            trace.append((sym, self.state, self.output()))
        return trace


if __name__ == "__main__":
    # Toy turnstile: LOCKED/UNLOCKED on 'coin'/'push'.
    turnstile = FSM(
        start="LOCKED",
        transitions={
            ("LOCKED", "coin"): "UNLOCKED",
            ("LOCKED", "push"): "LOCKED",
            ("UNLOCKED", "push"): "LOCKED",
            ("UNLOCKED", "coin"): "UNLOCKED",
        },
        outputs={"LOCKED": "closed", "UNLOCKED": "open"},
    )
    for inp, st, out in turnstile.run(["push", "coin", "push", "push"]):
        print(f"{inp:5s} -> {st:8s} ({out})")
