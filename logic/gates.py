from dataclasses import dataclass
from typing import Callable, List, Tuple


@dataclass
class GateCounter:

    count: int = 0

    def tick(self, amount: int = 1) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise TypeError("amount must be an integer")
        if amount < 1:
            raise ValueError("amount must be at least 1")
        self.count += amount

    def reset(self) -> None:
        self.count = 0


GATE_OPS = GateCounter()


def _bit(value: int, name: str = "logic signal") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be the integer 0 or 1")
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1, got {value!r}")
    return value


def NOT(a: int) -> int:
    a = _bit(a, "a")
    GATE_OPS.tick()
    return 1 - a


def AND(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return a & b


def OR(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return a | b


def NAND(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return 1 - (a & b)


def NOR(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return 1 - (a | b)


def XOR(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return a ^ b


def XNOR(a: int, b: int) -> int:
    a = _bit(a, "a")
    b = _bit(b, "b")
    GATE_OPS.tick()
    return 1 - (a ^ b)


def NOT_from_nand(a: int) -> int:
    return NAND(a, a)


def AND_from_nand(a: int, b: int) -> int:
    return NOT_from_nand(NAND(a, b))


def OR_from_nand(a: int, b: int) -> int:
    return NAND(NOT_from_nand(a), NOT_from_nand(b))


def truth_table(
    function: Callable[..., int],
    arity: int,
) -> List[Tuple[Tuple[int, ...], int]]:
    if not callable(function):
        raise TypeError("function must be callable")
    if isinstance(arity, bool) or not isinstance(arity, int):
        raise TypeError("arity must be an integer")
    if arity < 1:
        raise ValueError("arity must be at least 1")

    rows = []
    for value in range(1 << arity):
        inputs = tuple(
            (value >> (arity - 1 - index)) & 1
            for index in range(arity)
        )
        rows.append((inputs, function(*inputs)))
    return rows


if __name__ == "__main__":
    print("XOR truth table:")
    for inputs, output in truth_table(XOR, 2):
        print(f"  {inputs} -> {output}")