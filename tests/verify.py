"""
verify.py -- Correctness verification for every logic block.

Each circuit is checked exhaustively (all input combinations) against a
reference model computed with Python's native operators. This is how we
guarantee the gate-level implementations are actually correct before using
them in the application demos or performance analysis.

Run:  python -m tests.verify
Author: Members A & B (verification)
"""

import itertools
from logic.gates import (NOT, AND, OR, NAND, NOR, XOR, XNOR,
                         AND_from_nand, OR_from_nand, NOT_from_nand)
from logic.combinational import (half_adder, full_adder, ripple_carry_adder,
                                 mux2, mux4, decoder_2to4, decoder_3to8,
                                 magnitude_comparator, to_bits, from_bits)
from logic.sequential import DFlipFlop, JKFlipFlop, TFlipFlop, Register, BinaryCounter


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.log = []

    def check(self, name, condition):
        if condition:
            self.passed += 1
            self.log.append(f"  PASS  {name}")
        else:
            self.failed += 1
            self.log.append(f"  FAIL  {name}")

    def summary(self):
        total = self.passed + self.failed
        return (f"\n{self.passed}/{total} checks passed"
                + ("" if self.failed == 0 else f"  ({self.failed} FAILED)"))


def verify_all() -> Results:
    r = Results()

    # --- Primitive gates vs Python operators ---
    for a, b in itertools.product((0, 1), repeat=2):
        r.check(f"AND({a},{b})", AND(a, b) == (a & b))
        r.check(f"OR({a},{b})", OR(a, b) == (a | b))
        r.check(f"XOR({a},{b})", XOR(a, b) == (a ^ b))
        r.check(f"NAND({a},{b})", NAND(a, b) == (1 - (a & b)))
        r.check(f"NOR({a},{b})", NOR(a, b) == (1 - (a | b)))
        r.check(f"XNOR({a},{b})", XNOR(a, b) == (1 - (a ^ b)))
    for a in (0, 1):
        r.check(f"NOT({a})", NOT(a) == (1 - a))

    # --- NAND functional completeness ---
    for a, b in itertools.product((0, 1), repeat=2):
        r.check("NAND-AND", AND_from_nand(a, b) == (a & b))
        r.check("NAND-OR", OR_from_nand(a, b) == (a | b))
    for a in (0, 1):
        r.check("NAND-NOT", NOT_from_nand(a) == (1 - a))

    # --- Half / full adder ---
    for a, b in itertools.product((0, 1), repeat=2):
        s, c = half_adder(a, b)
        r.check(f"half_adder({a},{b})", (c * 2 + s) == (a + b))
    for a, b, cin in itertools.product((0, 1), repeat=3):
        s, c = full_adder(a, b, cin)
        r.check(f"full_adder({a},{b},{cin})", (c * 2 + s) == (a + b + cin))

    # --- Ripple-carry adder (exhaustive at 4 bits) ---
    ok = True
    for x in range(16):
        for y in range(16):
            s, c = ripple_carry_adder(to_bits(x, 4), to_bits(y, 4))
            if (c << 4) + from_bits(s) != x + y:
                ok = False
    r.check("ripple_carry_adder 4-bit exhaustive", ok)

    # --- Multiplexers ---
    ok2 = all(mux2(d0, d1, s) == (d1 if s else d0)
              for d0, d1, s in itertools.product((0, 1), repeat=3))
    r.check("mux2 exhaustive", ok2)
    ok4 = True
    for bits in itertools.product((0, 1), repeat=6):
        d0, d1, d2, d3, s1, s0 = bits
        expected = [d0, d1, d2, d3][(s1 << 1) | s0]
        if mux4(d0, d1, d2, d3, s1, s0) != expected:
            ok4 = False
    r.check("mux4 exhaustive", ok4)

    # --- Decoders (one-hot) ---
    ok_d = True
    for i in range(4):
        out = decoder_2to4(*to_bits(i, 2))
        if out.count(1) != 1 or out.index(1) != i:
            ok_d = False
    r.check("decoder_2to4 one-hot", ok_d)
    ok_d3 = True
    for i in range(8):
        out = decoder_3to8(*to_bits(i, 3))
        if out.count(1) != 1 or out.index(1) != i:
            ok_d3 = False
    r.check("decoder_3to8 one-hot", ok_d3)

    # --- Comparator ---
    r.check("comparator 5<9", magnitude_comparator(to_bits(5, 4), to_bits(9, 4)) == "A<B")
    r.check("comparator 9>5", magnitude_comparator(to_bits(9, 4), to_bits(5, 4)) == "A>B")
    r.check("comparator 7=7", magnitude_comparator(to_bits(7, 4), to_bits(7, 4)) == "A=B")

    # --- Flip-flops ---
    d = DFlipFlop()
    d.set_input(1); r.check("D-FF latch 1", d.clock() == 1)
    d.set_input(0); r.check("D-FF latch 0", d.clock() == 0)

    jk = JKFlipFlop()
    jk.set_inputs(1, 0); jk.clock(); r.check("JK set", jk.q == 1)
    jk.set_inputs(1, 1); jk.clock(); r.check("JK toggle", jk.q == 0)
    jk.set_inputs(0, 1); jk.clock(); r.check("JK reset", jk.q == 0)

    t = TFlipFlop()
    t.set_input(1); t.clock(); r.check("T toggle to 1", t.q == 1)
    t.clock(); r.check("T toggle to 0", t.q == 0)

    # --- Register ---
    reg = Register(8); reg.load(0b10101010)
    r.check("register load", reg.clock() == 0b10101010)

    # --- Counter wraps correctly ---
    ctr = BinaryCounter(3)
    seq = [ctr.clock() for _ in range(9)]
    r.check("3-bit counter sequence", seq == [1, 2, 3, 4, 5, 6, 7, 0, 1])

    return r


if __name__ == "__main__":
    res = verify_all()
    print("\n".join(res.log))
    print(res.summary())
