"""
combinational.py -- Combinational logic circuits.

Combinational circuits produce outputs that depend only on the current inputs
(no memory). Everything here is built strictly from the primitive gates in
gates.py, so each function is a faithful gate-level model rather than a Python
shortcut.

Circuits implemented:
  * half_adder / full_adder / ripple_carry_adder   (arithmetic datapath)
  * mux2 / mux4                                     (data selection / routing)
  * decoder_2to4 / decoder_3to8                     (address / command decode)
  * comparator_1bit / magnitude_comparator          (control decisions)

Course concepts demonstrated:
  * Combinational logic design from gates
  * Binary arithmetic (ripple-carry addition, carry propagation)
  * Data routing (multiplexers) and address decoding (decoders)

Author: Member A (combinational / gate-level design)
"""

from typing import List, Tuple
from .gates import AND, OR, NOT, XOR


# ---------------------------------------------------------------------------
# Binary <-> bit-list helpers (bit lists are MSB-first).
# ---------------------------------------------------------------------------
def to_bits(value: int, width: int) -> List[int]:
    """Convert a non-negative integer to a fixed-width MSB-first bit list."""
    if value < 0 or value >= (1 << width):
        raise ValueError(f"{value} does not fit in {width} bits")
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def from_bits(bits: List[int]) -> int:
    """Convert an MSB-first bit list back to an integer."""
    v = 0
    for b in bits:
        v = (v << 1) | b
    return v


# ---------------------------------------------------------------------------
# Adders.
# ---------------------------------------------------------------------------
def half_adder(a: int, b: int) -> Tuple[int, int]:
    """Return (sum, carry) for two 1-bit inputs."""
    s = XOR(a, b)
    c = AND(a, b)
    return s, c


def full_adder(a: int, b: int, cin: int) -> Tuple[int, int]:
    """Return (sum, cout) for two bits plus a carry-in (two half-adders)."""
    s1, c1 = half_adder(a, b)
    s2, c2 = half_adder(s1, cin)
    cout = OR(c1, c2)
    return s2, cout


def ripple_carry_adder(a_bits: List[int], b_bits: List[int],
                       cin: int = 0) -> Tuple[List[int], int]:
    """
    Add two equal-width MSB-first bit lists.

    Returns (sum_bits, carry_out). The carry ripples from LSB to MSB, exactly
    as in a hardware ripple-carry adder -- which is why its worst-case delay
    grows linearly with the word width (analysed in analysis/performance.py).
    """
    if len(a_bits) != len(b_bits):
        raise ValueError("Operands must be the same width")
    n = len(a_bits)
    sum_bits = [0] * n
    carry = cin
    # Iterate LSB -> MSB (list is MSB-first, so walk it in reverse).
    for i in range(n - 1, -1, -1):
        sum_bits[i], carry = full_adder(a_bits[i], b_bits[i], carry)
    return sum_bits, carry


# ---------------------------------------------------------------------------
# Multiplexers (data selection).
# ---------------------------------------------------------------------------
def mux2(d0: int, d1: int, sel: int) -> int:
    """2:1 multiplexer -- out = d1 if sel else d0, built from gates."""
    return OR(AND(d0, NOT(sel)), AND(d1, sel))


def mux4(d0: int, d1: int, d2: int, d3: int, s1: int, s0: int) -> int:
    """4:1 multiplexer with 2-bit select {s1,s0}."""
    lo = mux2(d0, d1, s0)
    hi = mux2(d2, d3, s0)
    return mux2(lo, hi, s1)


# ---------------------------------------------------------------------------
# Decoders (one-hot address / command decode).
# ---------------------------------------------------------------------------
def decoder_2to4(a1: int, a0: int, enable: int = 1) -> List[int]:
    """2-to-4 decoder. Returns [y0, y1, y2, y3]; one-hot when enabled."""
    na1, na0 = NOT(a1), NOT(a0)
    return [
        AND(enable, AND(na1, na0)),  # 00
        AND(enable, AND(na1, a0)),   # 01
        AND(enable, AND(a1, na0)),   # 10
        AND(enable, AND(a1, a0)),    # 11
    ]


def decoder_3to8(a2: int, a1: int, a0: int, enable: int = 1) -> List[int]:
    """3-to-8 decoder built by gating two 2-to-4 decoders with the MSB."""
    lower = decoder_2to4(a1, a0, AND(enable, NOT(a2)))
    upper = decoder_2to4(a1, a0, AND(enable, a2))
    return lower + upper


# ---------------------------------------------------------------------------
# Comparators (used by the application controllers for decisions).
# ---------------------------------------------------------------------------
def comparator_1bit(a: int, b: int) -> Tuple[int, int, int]:
    """Return (a_gt_b, a_eq_b, a_lt_b) for two single bits."""
    a_gt = AND(a, NOT(b))
    a_lt = AND(NOT(a), b)
    a_eq = NOT(OR(a_gt, a_lt))
    return a_gt, a_eq, a_lt


def magnitude_comparator(a_bits: List[int], b_bits: List[int]) -> str:
    """
    Compare two MSB-first unsigned bit lists.
    Returns one of 'A>B', 'A=B', 'A<B'. Scans from MSB down, gate-level style.
    """
    if len(a_bits) != len(b_bits):
        raise ValueError("Operands must be the same width")
    for a, b in zip(a_bits, b_bits):   # MSB first
        gt, eq, lt = comparator_1bit(a, b)
        if gt:
            return "A>B"
        if lt:
            return "A<B"
    return "A=B"


if __name__ == "__main__":
    a, b = to_bits(13, 8), to_bits(29, 8)
    s, c = ripple_carry_adder(a, b)
    print(f"13 + 29 = {from_bits(s)} (carry {c})")
    print("decoder_3to8 for input 5:", decoder_3to8(1, 0, 1))
    print("compare 13 vs 29:", magnitude_comparator(a, b))
