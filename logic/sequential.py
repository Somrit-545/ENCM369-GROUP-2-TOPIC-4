"""
sequential.py -- Sequential logic circuits (elements with memory).

Unlike combinational logic, sequential circuits have state: their outputs
depend on both current inputs and stored history, and they update on a clock
edge. Each element below models a positive-edge-triggered device and exposes a
`clock()` method that advances it by one edge.

Elements implemented:
  * DFlipFlop, JKFlipFlop, TFlipFlop  (1-bit storage primitives)
  * Register                          (n-bit word, array of D flip-flops)
  * BinaryCounter                     (synchronous up counter of T flip-flops)
  * Clock                             (simple tick generator for simulations)

Course concepts demonstrated:
  * Sequential logic and state
  * Clocking / synchronous updates
  * Registers and counters (the storage layer of a datapath)

Author: Member B (sequential logic / clocking)
"""

from typing import List
from .gates import XOR


class DFlipFlop:
    """
    Positive-edge-triggered D flip-flop.
    On a clock edge the output Q takes the value present on input D.
    """

    def __init__(self, initial: int = 0):
        self.q = initial & 1
        self.d = initial & 1

    def set_input(self, d: int) -> None:
        self.d = d & 1

    def clock(self) -> int:
        """Advance one clock edge; latch D into Q. Returns new Q."""
        self.q = self.d
        return self.q


class JKFlipFlop:
    """
    Positive-edge-triggered JK flip-flop.
      J K | next Q
      0 0 | hold
      0 1 | reset (0)
      1 0 | set   (1)
      1 1 | toggle
    """

    def __init__(self, initial: int = 0):
        self.q = initial & 1
        self.j = 0
        self.k = 0

    def set_inputs(self, j: int, k: int) -> None:
        self.j, self.k = j & 1, k & 1

    def clock(self) -> int:
        if self.j == 0 and self.k == 0:
            pass                      # hold
        elif self.j == 0 and self.k == 1:
            self.q = 0                # reset
        elif self.j == 1 and self.k == 0:
            self.q = 1                # set
        else:
            self.q = 1 - self.q       # toggle
        return self.q


class TFlipFlop:
    """
    Positive-edge-triggered T (toggle) flip-flop.
    When T=1 the output toggles on a clock edge; when T=0 it holds.
    Implemented with an XOR feeding a D flip-flop, as in real hardware.
    """

    def __init__(self, initial: int = 0):
        self.dff = DFlipFlop(initial)
        self.t = 0

    @property
    def q(self) -> int:
        return self.dff.q

    def set_input(self, t: int) -> None:
        self.t = t & 1

    def clock(self) -> int:
        self.dff.set_input(XOR(self.t, self.dff.q))
        return self.dff.clock()


class Register:
    """
    n-bit register: an array of D flip-flops that load in parallel.
    Bits are stored/reported MSB-first to match the combinational helpers.
    """

    def __init__(self, width: int, initial: int = 0):
        self.width = width
        self.cells: List[DFlipFlop] = [
            DFlipFlop((initial >> (width - 1 - i)) & 1) for i in range(width)
        ]

    def load(self, value: int) -> None:
        """Present a value on the D inputs (latched on the next clock)."""
        for i, cell in enumerate(self.cells):
            cell.set_input((value >> (self.width - 1 - i)) & 1)

    def clock(self) -> int:
        for cell in self.cells:
            cell.clock()
        return self.value()

    def value(self) -> int:
        v = 0
        for cell in self.cells:
            v = (v << 1) | cell.q
        return v


class BinaryCounter:
    """
    Synchronous up counter built from T flip-flops.
    Each stage toggles when all lower stages are 1 (classic ripple/enable
    chain). Wraps around at 2**width.
    """

    def __init__(self, width: int, initial: int = 0):
        self.width = width
        self.stages: List[TFlipFlop] = [
            TFlipFlop((initial >> i) & 1) for i in range(width)  # stage 0 = LSB
        ]

    def reset(self) -> None:
        for stage in self.stages:
            stage.dff.q = 0
            stage.dff.d = 0

    def clock(self) -> int:
        # Capture PRE-clock outputs; in real hardware every flip-flop sees the
        # current state when the edge arrives, so enables must not use values
        # that have already been updated this edge.
        pre = [stage.q for stage in self.stages]   # LSB -> MSB
        enable = 1
        for i, stage in enumerate(self.stages):    # LSB -> MSB
            stage.set_input(enable)                # T_i = AND of lower Qs
            enable &= pre[i]                        # fold in for the next stage
        for stage in self.stages:                  # all toggle simultaneously
            stage.clock()
        return self.value()

    def value(self) -> int:
        v = 0
        for stage in reversed(self.stages):        # MSB first for the integer
            v = (v << 1) | stage.q
        return v


class Clock:
    """A trivial clock source: yields alternating 0/1 levels or edge counts."""

    def __init__(self):
        self.ticks = 0

    def tick(self) -> int:
        self.ticks += 1
        return self.ticks


if __name__ == "__main__":
    ctr = BinaryCounter(3)
    seq = [ctr.clock() for _ in range(10)]
    print("3-bit counter sequence:", seq)   # 1,2,...,7,0,1,2

    reg = Register(8)
    reg.load(0b10110001)
    print("register after load+clock:", bin(reg.clock()))
