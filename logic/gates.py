"""
gates.py -- Primitive logic gates.

This module implements the fundamental Boolean logic gates that every other
circuit in the project is built from. Each gate operates on single-bit inputs
represented as Python ints 0 or 1 and returns a single-bit int.

Course concepts demonstrated:
  * Boolean algebra / truth tables
  * Gate-level abstraction (the building block of all digital logic)
  * NAND functional completeness (any circuit can be built from NAND alone)

A module-level counter (GATE_OPS) tallies primitive gate evaluations so the
performance analysis can estimate hardware cost of larger circuits.

Author: Member A (combinational / gate-level design)
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Optional gate-operation counter (used by analysis/performance.py).
# ---------------------------------------------------------------------------
@dataclass
class GateCounter:
    """Counts how many primitive gate evaluations have occurred."""
    count: int = 0

    def tick(self, n: int = 1) -> None:
        self.count += n

    def reset(self) -> None:
        self.count = 0


GATE_OPS = GateCounter()


def _bit(x: int) -> int:
    """Validate and normalise an input to a clean 0/1 bit."""
    if x not in (0, 1):
        raise ValueError(f"Logic signal must be 0 or 1, got {x!r}")
    return x


# ---------------------------------------------------------------------------
# Primitive gates.
# ---------------------------------------------------------------------------
def NOT(a: int) -> int:
    GATE_OPS.tick()
    return 1 - _bit(a)


def AND(a: int, b: int) -> int:
    GATE_OPS.tick()
    return _bit(a) & _bit(b)


def OR(a: int, b: int) -> int:
    GATE_OPS.tick()
    return _bit(a) | _bit(b)


def NAND(a: int, b: int) -> int:
    GATE_OPS.tick()
    return 1 - (_bit(a) & _bit(b))


def NOR(a: int, b: int) -> int:
    GATE_OPS.tick()
    return 1 - (_bit(a) | _bit(b))


def XOR(a: int, b: int) -> int:
    GATE_OPS.tick()
    return _bit(a) ^ _bit(b)


def XNOR(a: int, b: int) -> int:
    GATE_OPS.tick()
    return 1 - (_bit(a) ^ _bit(b))


# ---------------------------------------------------------------------------
# NAND-only equivalents -- demonstrates functional completeness of NAND.
# These are used in the report to argue that a single gate type suffices to
# implement any combinational function (a key computer-organization insight).
# ---------------------------------------------------------------------------
def NOT_from_nand(a: int) -> int:
    return NAND(a, a)


def AND_from_nand(a: int, b: int) -> int:
    return NOT_from_nand(NAND(a, b))


def OR_from_nand(a: int, b: int) -> int:
    return NAND(NOT_from_nand(a), NOT_from_nand(b))


def truth_table(func, arity: int):
    """
    Return the full truth table of a gate/function of the given arity.

    Returns a list of (inputs_tuple, output) rows, useful for verification.
    """
    rows = []
    for i in range(2 ** arity):
        inputs = tuple((i >> (arity - 1 - k)) & 1 for k in range(arity))
        rows.append((inputs, func(*inputs)))
    return rows


if __name__ == "__main__":
    # Quick self-check when run directly.
    print("XOR truth table:")
    for inp, out in truth_table(XOR, 2):
        print(f"  {inp} -> {out}")
    print("\nNAND-built AND matches AND:",
          all(AND(a, b) == AND_from_nand(a, b)
              for a in (0, 1) for b in (0, 1)))
