from typing import List

from .gates import XOR


def _require_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_bit(value: int, name: str) -> int:
    value = _require_integer(value, name)
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _require_width(width: int) -> int:
    width = _require_integer(width, "width")
    if width < 1:
        raise ValueError("width must be at least 1")
    return width


def _require_unsigned(value: int, width: int, name: str) -> int:
    value = _require_integer(value, name)
    maximum = (1 << width) - 1
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} must be in the range 0 to {maximum}")
    return value


class DFlipFlop:

    def __init__(self, initial: int = 0):
        initial = _require_bit(initial, "initial")
        self.q = initial
        self.d = initial

    def set_input(self, d: int) -> None:
        self.d = _require_bit(d, "d")

    def clock(self) -> int:
        self.q = self.d
        return self.q

    def reset(self) -> None:
        self.q = 0
        self.d = 0


class JKFlipFlop:

    def __init__(self, initial: int = 0):
        self.q = _require_bit(initial, "initial")
        self.j = 0
        self.k = 0

    def set_inputs(self, j: int, k: int) -> None:
        self.j = _require_bit(j, "j")
        self.k = _require_bit(k, "k")

    def clock(self) -> int:
        if self.j == 0 and self.k == 1:
            self.q = 0
        elif self.j == 1 and self.k == 0:
            self.q = 1
        elif self.j == 1 and self.k == 1:
            self.q = 1 - self.q
        return self.q

    def reset(self) -> None:
        self.q = 0
        self.j = 0
        self.k = 0


class TFlipFlop:

    def __init__(self, initial: int = 0):
        self.dff = DFlipFlop(initial)
        self.t = 0

    @property
    def q(self) -> int:
        return self.dff.q

    def set_input(self, t: int) -> None:
        self.t = _require_bit(t, "t")

    def clock(self) -> int:
        self.dff.set_input(XOR(self.t, self.dff.q))
        return self.dff.clock()

    def reset(self) -> None:
        self.dff.reset()
        self.t = 0


class Register:

    def __init__(self, width: int, initial: int = 0):
        self.width = _require_width(width)
        initial = _require_unsigned(initial, self.width, "initial")
        self.cells: List[DFlipFlop] = [
            DFlipFlop((initial >> (self.width - 1 - index)) & 1)
            for index in range(self.width)
        ]

    def load(self, value: int) -> None:
        value = _require_unsigned(value, self.width, "value")
        for index, cell in enumerate(self.cells):
            cell.set_input((value >> (self.width - 1 - index)) & 1)

    def clock(self) -> int:
        for cell in self.cells:
            cell.clock()
        return self.value()

    def value(self) -> int:
        result = 0
        for cell in self.cells:
            result = (result << 1) | cell.q
        return result

    def reset(self) -> None:
        for cell in self.cells:
            cell.reset()


class BinaryCounter:

    def __init__(self, width: int, initial: int = 0):
        self.width = _require_width(width)
        initial = _require_unsigned(initial, self.width, "initial")
        self.stages: List[TFlipFlop] = [
            TFlipFlop((initial >> index) & 1)
            for index in range(self.width)
        ]

    def reset(self) -> None:
        for stage in self.stages:
            stage.reset()

    def clock(self) -> int:
        previous = [stage.q for stage in self.stages]
        enable = 1
        for index, stage in enumerate(self.stages):
            stage.set_input(enable)
            enable &= previous[index]
        for stage in self.stages:
            stage.clock()
        return self.value()

    def value(self) -> int:
        result = 0
        for stage in reversed(self.stages):
            result = (result << 1) | stage.q
        return result


class Clock:

    def __init__(self):
        self.ticks = 0

    def tick(self) -> int:
        self.ticks += 1
        return self.ticks

    def reset(self) -> None:
        self.ticks = 0


if __name__ == "__main__":
    counter = BinaryCounter(3)
    print("3-bit counter sequence:", [counter.clock() for _ in range(10)])