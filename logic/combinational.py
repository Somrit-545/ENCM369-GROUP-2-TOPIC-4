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
rom typing import List, Sequence, Tuple

from .gates import AND, NOT, OR, XOR


def _require_integer(value: int, name: str) -> int:
    """Return a non-Boolean integer or raise a clear error."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_positive_width(width: int) -> int:
    """Return a valid bit width."""
    width = _require_integer(width, "width")
    if width < 1:
        raise ValueError("width must be at least 1")
    return width


def _require_bit(value: int, name: str) -> int:
    """Return a validated binary digit."""
    value = _require_integer(value, name)
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _validated_bits(bits: Sequence[int], name: str) -> Tuple[int, ...]:
    """Return a non-empty tuple containing only 0/1 integers."""
    if isinstance(bits, (str, bytes)):
        raise TypeError(f"{name} must be a sequence of bits")
    try:
        values = tuple(bits)
    except TypeError as error:
        raise TypeError(f"{name} must be a sequence of bits") from error
    if not values:
        raise ValueError(f"{name} must contain at least one bit")
    return tuple(
        _require_bit(bit, f"{name}[{index}]")
        for index, bit in enumerate(values)
    )


def to_bits(value: int, width: int) -> List[int]:
    """Convert an unsigned integer to a fixed-width MSB-first bit list."""
    value = _require_integer(value, "value")
    width = _require_positive_width(width)
    maximum = (1 << width) - 1
    if not 0 <= value <= maximum:
        raise ValueError(f"value must be in the range 0 to {maximum}")
    return [
        (value >> (width - 1 - index)) & 1
        for index in range(width)
    ]


def from_bits(bits: Sequence[int]) -> int:
    """Convert a non-empty MSB-first bit sequence to an integer."""
    values = _validated_bits(bits, "bits")
    result = 0
    for bit in values:
        result = (result << 1) | bit
    return result


def half_adder(a: int, b: int) -> Tuple[int, int]:
    """Return ``(sum_bit, carry_bit)`` for two 1-bit inputs."""
    return XOR(a, b), AND(a, b)


def full_adder(a: int, b: int, carry_in: int) -> Tuple[int, int]:
    """Return ``(sum_bit, carry_out)`` for two bits and a carry-in."""
    first_sum, first_carry = half_adder(a, b)
    final_sum, second_carry = half_adder(first_sum, carry_in)
    carry_out = OR(first_carry, second_carry)
    return final_sum, carry_out


def ripple_carry_adder(
    a_bits: Sequence[int],
    b_bits: Sequence[int],
    cin: int = 0,
) -> Tuple[List[int], int]:
    """Add two equal-width, MSB-first bit sequences."""
    a_values = _validated_bits(a_bits, "a_bits")
    b_values = _validated_bits(b_bits, "b_bits")
    carry = _require_bit(cin, "cin")

    if len(a_values) != len(b_values):
        raise ValueError("a_bits and b_bits must have the same width")

    sum_bits = [0] * len(a_values)
    for index in range(len(a_values) - 1, -1, -1):
        sum_bits[index], carry = full_adder(
            a_values[index],
            b_values[index],
            carry,
        )
    return sum_bits, carry


def mux2(d0: int, d1: int, sel: int) -> int:
    """Select ``d0`` when ``sel=0`` and ``d1`` when ``sel=1``."""
    return OR(AND(d0, NOT(sel)), AND(d1, sel))


def mux4(
    d0: int,
    d1: int,
    d2: int,
    d3: int,
    s1: int,
    s0: int,
) -> int:
    """Select one of four data bits using the selector ``s1 s0``."""
    lower_pair = mux2(d0, d1, s0)
    upper_pair = mux2(d2, d3, s0)
    return mux2(lower_pair, upper_pair, s1)


def decoder_2to4(a1: int, a0: int, enable: int = 1) -> List[int]:
    """Return a 4-bit one-hot output when enabled, otherwise all zeros."""
    not_a1 = NOT(a1)
    not_a0 = NOT(a0)
    return [
        AND(enable, AND(not_a1, not_a0)),
        AND(enable, AND(not_a1, a0)),
        AND(enable, AND(a1, not_a0)),
        AND(enable, AND(a1, a0)),
    ]


def decoder_3to8(
    a2: int,
    a1: int,
    a0: int,
    enable: int = 1,
) -> List[int]:
    """Return an 8-bit one-hot output using two 2-to-4 decoders."""
    lower_enable = AND(enable, NOT(a2))
    upper_enable = AND(enable, a2)
    return (
        decoder_2to4(a1, a0, lower_enable)
        + decoder_2to4(a1, a0, upper_enable)
    )


def comparator_1bit(a: int, b: int) -> Tuple[int, int, int]:
    """Return ``(a_gt_b, a_eq_b, a_lt_b)`` for two bits."""
    a_greater = AND(a, NOT(b))
    a_less = AND(NOT(a), b)
    a_equal = NOT(OR(a_greater, a_less))
    return a_greater, a_equal, a_less


def magnitude_comparator(
    a_bits: Sequence[int],
    b_bits: Sequence[int],
) -> str:
    """Compare equal-width unsigned bit sequences from MSB to LSB."""
    a_values = _validated_bits(a_bits, "a_bits")
    b_values = _validated_bits(b_bits, "b_bits")
    if len(a_values) != len(b_values):
        raise ValueError("a_bits and b_bits must have the same width")

    for a_bit, b_bit in zip(a_values, b_values):
        greater, _, less = comparator_1bit(a_bit, b_bit)
        if greater:
            return "A>B"
        if less:
            return "A<B"
    return "A=B"


if __name__ == "__main__":
    a_value = to_bits(13, 8)
    b_value = to_bits(29, 8)
    sum_value, carry_value = ripple_carry_adder(a_value, b_value)
    print(f"13 + 29 = {from_bits(sum_value)} (carry {carry_value})")

