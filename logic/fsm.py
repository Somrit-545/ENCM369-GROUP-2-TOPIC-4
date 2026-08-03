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
from typing import Any, Dict, Hashable, Iterable, List, Tuple


@dataclass
class FSM:
    """A Moore FSM whose outputs depend only on the current state."""

    start: Hashable
    transitions: Dict[Tuple[Hashable, Hashable], Hashable]
    outputs: Dict[Hashable, Any] = field(default_factory=dict)
    state: Hashable = None
    strict: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.transitions, dict):
            raise TypeError("transitions must be a dictionary")
        if not isinstance(self.outputs, dict):
            raise TypeError("outputs must be a dictionary")
        if not isinstance(self.strict, bool):
            raise TypeError("strict must be a Boolean")

        self.transitions = dict(self.transitions)
        self.outputs = dict(self.outputs)

        known_states = {self.start}
        for key, next_state in self.transitions.items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError(
                    "each transition key must be a (state, input_symbol) pair"
                )
            known_states.add(key[0])
            known_states.add(next_state)

        if self.outputs:
            missing_outputs = known_states.difference(self.outputs)
            if missing_outputs:
                missing = ", ".join(sorted(map(str, missing_outputs)))
                raise ValueError(f"missing Moore outputs for states: {missing}")

        if self.state is None:
            self.state = self.start
        elif self.state not in known_states:
            raise ValueError("initial state is not defined by the FSM")

    def reset(self) -> None:
        """Return the machine to its start state."""
        self.state = self.start

    def output(self) -> Any:
        """Return the Moore output for the current state."""
        if not self.outputs:
            return None
        if self.state not in self.outputs:
            raise RuntimeError(f"no output is defined for state {self.state!r}")
        return self.outputs[self.state]

    def step(self, symbol: Hashable) -> Hashable:
        """Consume one symbol and return the resulting state."""
        key = (self.state, symbol)
        if key not in self.transitions:
            if self.strict:
                raise ValueError(
                    f"undefined transition from state {self.state!r} "
                    f"with input {symbol!r}"
                )
            return self.state
        self.state = self.transitions[key]
        return self.state

    def run(
        self,
        symbols: Iterable[Hashable],
    ) -> List[Tuple[Hashable, Hashable, Any]]:
        """Return ``(input, resulting_state, output)`` for each symbol."""
        if isinstance(symbols, (str, bytes)):
            raise TypeError("symbols must be an iterable, not one string")
        try:
            iterator = iter(symbols)
        except TypeError as error:
            raise TypeError("symbols must be iterable") from error

        trace = []
        for symbol in iterator:
            state = self.step(symbol)
            trace.append((symbol, state, self.output()))
        return trace


if __name__ == "__main__":
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
    for input_symbol, state, output in turnstile.run(
        ["push", "coin", "push", "push"]
    ):
        print(f"{input_symbol:5s} -> {state:8s} ({output})")
