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
import sys
from typing import Callable, List, Type

from analysis.performance import lookahead_delay, ripple_delay, ripple_gate_count
from applications.industrial import (
    BINS,
    PHASE_TICKS,
    TRAFFIC_OUTPUTS,
    TRAFFIC_STATES,
    run_sorter,
    run_traffic,
    sort_item,
)
from applications.smart_home import (
    APPLIANCES,
    SECURITY_EVENTS,
    SECURITY_OUTPUTS,
    SECURITY_STATES,
    SECURITY_TRANSITIONS,
    build_security_fsm,
    decode_command,
    read_status,
    run_security,
    thermostat,
)
from logic.combinational import (
    comparator_1bit,
    decoder_2to4,
    decoder_3to8,
    from_bits,
    full_adder,
    half_adder,
    magnitude_comparator,
    mux2,
    mux4,
    ripple_carry_adder,
    to_bits,
)
from logic.fsm import FSM
from logic.gates import (
    AND,
    AND_from_nand,
    GATE_OPS,
    NAND,
    NOR,
    NOT,
    NOT_from_nand,
    OR,
    OR_from_nand,
    XNOR,
    XOR,
    truth_table,
)
from logic.sequential import (
    BinaryCounter,
    Clock,
    DFlipFlop,
    JKFlipFlop,
    Register,
    TFlipFlop,
)


class Results:
    """Collect grouped verification results and printable messages."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.log: List[str] = []

    def check(self, name: str, condition: bool) -> None:
        """Record one grouped check."""
        if condition:
            self.passed += 1
            self.log.append(f"  PASS  {name}")
        else:
            self.failed += 1
            self.log.append(f"  FAIL  {name}")

    def summary(self) -> str:
        """Return a compact pass/fail summary."""
        total = self.passed + self.failed
        suffix = "" if self.failed == 0 else f"  ({self.failed} FAILED)"
        return f"\n{self.passed}/{total} grouped checks passed{suffix}"


def _raises(
    expected: Type[BaseException],
    function: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> bool:
    """Return True only when the expected exception type is raised."""
    try:
        function(*args, **kwargs)
    except expected:
        return True
    except Exception:
        return False
    return False


def _all_raise(cases: List[tuple]) -> bool:
    """Run a list of ``(exception, function, args, kwargs)`` cases."""
    return all(
        _raises(expected, function, *args, **kwargs)
        for expected, function, args, kwargs in cases
    )


def _verify_gates(results: Results) -> None:
    binary_functions = {
        "AND": (AND, lambda a, b: a & b),
        "OR": (OR, lambda a, b: a | b),
        "NAND": (NAND, lambda a, b: 1 - (a & b)),
        "NOR": (NOR, lambda a, b: 1 - (a | b)),
        "XOR": (XOR, lambda a, b: a ^ b),
        "XNOR": (XNOR, lambda a, b: 1 - (a ^ b)),
    }
    for name, (function, reference) in binary_functions.items():
        valid = all(
            function(a, b) == reference(a, b)
            for a, b in itertools.product((0, 1), repeat=2)
        )
        results.check(f"{name} exhaustive truth table", valid)

    results.check(
        "NOT exhaustive truth table",
        all(NOT(a) == 1 - a for a in (0, 1)),
    )
    results.check(
        "NAND functional completeness",
        all(
            AND_from_nand(a, b) == (a & b)
            and OR_from_nand(a, b) == (a | b)
            for a, b in itertools.product((0, 1), repeat=2)
        )
        and all(NOT_from_nand(a) == 1 - a for a in (0, 1)),
    )
    results.check(
        "truth_table helper",
        truth_table(XOR, 2)
        == [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 0)],
    )

    GATE_OPS.reset()
    invalid_cases = [
        (ValueError, AND, (2, 0), {}),
        (TypeError, OR, (True, 0), {}),
        (ValueError, NOT, (-1,), {}),
        (TypeError, truth_table, (XOR, True), {}),
        (ValueError, truth_table, (XOR, 0), {}),
    ]
    invalid_ok = _all_raise(invalid_cases) and GATE_OPS.count == 0
    results.check("gate input validation and clean counter", invalid_ok)


def _verify_combinational(results: Results) -> None:
    conversion_ok = True
    for width in range(1, 9):
        for value in range(1 << width):
            if from_bits(to_bits(value, width)) != value:
                conversion_ok = False
                break
    results.check("bit conversion exhaustive for widths 1-8", conversion_ok)

    results.check(
        "half-adder exhaustive",
        all(
            2 * half_adder(a, b)[1] + half_adder(a, b)[0] == a + b
            for a, b in itertools.product((0, 1), repeat=2)
        ),
    )
    results.check(
        "full-adder exhaustive",
        all(
            2 * full_adder(a, b, carry)[1]
            + full_adder(a, b, carry)[0]
            == a + b + carry
            for a, b, carry in itertools.product((0, 1), repeat=3)
        ),
    )

    ripple_ok = True
    ripple_pairs = 0
    for width in range(1, 6):
        for a_value in range(1 << width):
            for b_value in range(1 << width):
                sum_bits, carry = ripple_carry_adder(
                    to_bits(a_value, width),
                    to_bits(b_value, width),
                )
                actual = (carry << width) | from_bits(sum_bits)
                ripple_pairs += 1
                if actual != a_value + b_value:
                    ripple_ok = False
                    break
    results.check(
        f"ripple-carry exhaustive widths 1-5 ({ripple_pairs} pairs)",
        ripple_ok,
    )

    results.check(
        "2-to-1 multiplexer exhaustive",
        all(
            mux2(d0, d1, select) == (d1 if select else d0)
            for d0, d1, select in itertools.product((0, 1), repeat=3)
        ),
    )

    mux4_ok = True
    for values in itertools.product((0, 1), repeat=6):
        d0, d1, d2, d3, s1, s0 = values
        expected = (d0, d1, d2, d3)[(s1 << 1) | s0]
        if mux4(d0, d1, d2, d3, s1, s0) != expected:
            mux4_ok = False
            break
    results.check("4-to-1 multiplexer exhaustive", mux4_ok)

    decoder_ok = True
    for value in range(4):
        enabled = decoder_2to4(*to_bits(value, 2), enable=1)
        disabled = decoder_2to4(*to_bits(value, 2), enable=0)
        decoder_ok &= enabled == [int(index == value) for index in range(4)]
        decoder_ok &= disabled == [0, 0, 0, 0]
    for value in range(8):
        enabled = decoder_3to8(*to_bits(value, 3), enable=1)
        disabled = decoder_3to8(*to_bits(value, 3), enable=0)
        decoder_ok &= enabled == [int(index == value) for index in range(8)]
        decoder_ok &= disabled == [0] * 8
    results.check("2-to-4 and 3-to-8 decoders exhaustive", decoder_ok)

    results.check(
        "1-bit comparator exhaustive",
        all(
            comparator_1bit(a, b)
            == (int(a > b), int(a == b), int(a < b))
            for a, b in itertools.product((0, 1), repeat=2)
        ),
    )

    comparator_ok = True
    comparator_pairs = 0
    for width in range(1, 7):
        for a_value in range(1 << width):
            for b_value in range(1 << width):
                expected = (
                    "A>B"
                    if a_value > b_value
                    else "A<B"
                    if a_value < b_value
                    else "A=B"
                )
                comparator_pairs += 1
                if magnitude_comparator(
                    to_bits(a_value, width),
                    to_bits(b_value, width),
                ) != expected:
                    comparator_ok = False
                    break
    results.check(
        f"magnitude comparator exhaustive widths 1-6 ({comparator_pairs} pairs)",
        comparator_ok,
    )

    invalid_cases = [
        (ValueError, to_bits, (0, 0), {}),
        (TypeError, to_bits, (True, 1), {}),
        (ValueError, to_bits, (4, 2), {}),
        (ValueError, from_bits, ([],), {}),
        (ValueError, from_bits, ([0, 2],), {}),
        (ValueError, ripple_carry_adder, ([0], [0, 1]), {}),
        (ValueError, ripple_carry_adder, ([0], [0]), {"cin": 2}),
        (ValueError, magnitude_comparator, ([0], [0, 1]), {}),
    ]
    results.check("combinational boundary validation", _all_raise(invalid_cases))


def _verify_sequential(results: Results) -> None:
    d_ok = True
    for initial, d_value in itertools.product((0, 1), repeat=2):
        flip_flop = DFlipFlop(initial)
        before = flip_flop.q
        flip_flop.set_input(d_value)
        d_ok &= flip_flop.q == before and flip_flop.clock() == d_value
    results.check("D flip-flop state table", d_ok)

    jk_ok = True
    for initial, j_value, k_value in itertools.product((0, 1), repeat=3):
        flip_flop = JKFlipFlop(initial)
        flip_flop.set_inputs(j_value, k_value)
        expected = {
            (0, 0): initial,
            (0, 1): 0,
            (1, 0): 1,
            (1, 1): 1 - initial,
        }[(j_value, k_value)]
        jk_ok &= flip_flop.clock() == expected
    results.check("JK flip-flop complete state table", jk_ok)

    t_ok = True
    for initial, t_value in itertools.product((0, 1), repeat=2):
        flip_flop = TFlipFlop(initial)
        flip_flop.set_input(t_value)
        expected = initial if t_value == 0 else 1 - initial
        t_ok &= flip_flop.clock() == expected
    results.check("T flip-flop complete state table", t_ok)

    register_ok = True
    register_cases = 0
    for width in range(1, 9):
        for value in range(1 << width):
            register = Register(width)
            register.load(value)
            register_ok &= register.value() == 0
            register_ok &= register.clock() == value
            register.reset()
            register_ok &= register.value() == 0
            register_cases += 1
    results.check(
        f"register load/hold/reset widths 1-8 ({register_cases} words)",
        register_ok,
    )

    counter_ok = True
    counter_edges = 0
    for width in range(1, 7):
        counter = BinaryCounter(width)
        modulus = 1 << width
        for expected in list(range(1, modulus)) + [0]:
            counter_ok &= counter.clock() == expected
            counter_edges += 1
        counter.reset()
        counter_ok &= counter.value() == 0
    nonzero = BinaryCounter(4, initial=13)
    counter_ok &= [nonzero.clock() for _ in range(4)] == [14, 15, 0, 1]
    results.check(
        f"binary counters full cycles widths 1-6 ({counter_edges} edges)",
        counter_ok,
    )

    clock = Clock()
    clock_ok = [clock.tick() for _ in range(4)] == [1, 2, 3, 4]
    clock.reset()
    clock_ok &= clock.ticks == 0
    results.check("simulation clock edge counting", clock_ok)

    invalid_cases = [
        (ValueError, DFlipFlop, (2,), {}),
        (TypeError, DFlipFlop, (True,), {}),
        (ValueError, JKFlipFlop().set_inputs, (0, 2), {}),
        (ValueError, TFlipFlop().set_input, (-1,), {}),
        (ValueError, Register, (0,), {}),
        (ValueError, Register, (4, 16), {}),
        (ValueError, Register(4).load, (16,), {}),
        (ValueError, BinaryCounter, (0,), {}),
        (ValueError, BinaryCounter, (3, 8), {}),
    ]
    results.check("sequential input validation", _all_raise(invalid_cases))


def _verify_fsm(results: Results) -> None:
    transitions = {
        ("OFF", "toggle"): "ON",
        ("ON", "toggle"): "OFF",
    }
    outputs = {"OFF": 0, "ON": 1}
    machine = FSM("OFF", transitions, outputs)
    trace = machine.run(["toggle", "toggle", "toggle"])
    expected = [
        ("toggle", "ON", 1),
        ("toggle", "OFF", 0),
        ("toggle", "ON", 1),
    ]
    machine.reset()
    results.check(
        "Moore FSM transitions, outputs, trace, and reset",
        trace == expected and machine.state == "OFF" and machine.output() == 0,
    )
    results.check(
        "strict FSM rejects undefined transition",
        _raises(ValueError, machine.step, "unknown"),
    )
    permissive = FSM("OFF", transitions, outputs, strict=False)
    results.check(
        "optional permissive FSM holds undefined transition",
        permissive.step("unknown") == "OFF",
    )
    results.check(
        "FSM configuration validation",
        _raises(
            ValueError,
            FSM,
            "OFF",
            {("OFF", "toggle"): "ON"},
            {"OFF": 0},
        ),
    )


def _verify_smart_home(results: Results) -> None:
    decoder_ok = all(
        decode_command(code)
        == (
            APPLIANCES[code],
            [int(index == code) for index in range(len(APPLIANCES))],
        )
        for code in range(len(APPLIANCES))
    )
    results.check("smart-home command decoder all commands", decoder_ok)

    mux_ok = True
    sensor_cases = 0
    for sensors in itertools.product((0, 1), repeat=4):
        for channel, expected in enumerate(sensors):
            mux_ok &= read_status(sensors, channel) == expected
            sensor_cases += 1
    results.check(
        f"smart-home sensor mux exhaustive ({sensor_cases} selections)",
        mux_ok,
    )

    thermostat_ok = True
    thermostat_pairs = 0
    for current in range(64):
        for setpoint in range(64):
            expected = (
                "COOL"
                if current > setpoint
                else "HEAT"
                if current < setpoint
                else "IDLE"
            )
            thermostat_ok &= thermostat(current, setpoint) == expected
            thermostat_pairs += 1
    results.check(
        f"thermostat exhaustive 6-bit comparison ({thermostat_pairs} pairs)",
        thermostat_ok,
    )

    expected_pairs = set(itertools.product(SECURITY_STATES, SECURITY_EVENTS))
    transition_ok = set(SECURITY_TRANSITIONS) == expected_pairs
    transition_ok &= set(SECURITY_OUTPUTS) == set(SECURITY_STATES)
    for state, event in expected_pairs:
        machine = build_security_fsm()
        machine.state = state
        resulting_state = machine.step(event)
        transition_ok &= resulting_state == SECURITY_TRANSITIONS[(state, event)]
        transition_ok &= machine.output() == SECURITY_OUTPUTS[resulting_state]
    scenario = run_security(["arm", "motion", "clear", "disarm"])
    transition_ok &= [row[1] for row in scenario] == [
        "ARMED",
        "ALARM",
        "ARMED",
        "DISARMED",
    ]
    results.check("security FSM completeness and scenario", transition_ok)

    invalid_cases = [
        (ValueError, decode_command, (-1,), {}),
        (TypeError, decode_command, (True,), {}),
        (ValueError, read_status, ((0, 1, 0), 0), {}),
        (ValueError, read_status, ((0, 1, 2, 0), 0), {}),
        (ValueError, read_status, ((0, 1, 0, 1), 4), {}),
        (ValueError, thermostat, (0, 0, 0), {}),
        (ValueError, thermostat, (64, 21), {}),
        (ValueError, run_security, (("arm", "motoin"),), {}),
    ]
    results.check("smart-home boundary validation", _all_raise(invalid_cases))


def _verify_industrial(results: Results) -> None:
    sorter_decoder_ok = all(
        sort_item(tag)
        == (BINS[tag], [int(index == tag) for index in range(len(BINS))])
        for tag in range(len(BINS))
    )
    results.check("industrial sorter decoder all tags", sorter_decoder_ok)

    traffic_log = run_traffic(cycles=2)
    expected_rows = []
    tick = 0
    for _ in range(2):
        for state in TRAFFIC_STATES:
            for timer_count in range(1, PHASE_TICKS[state] + 1):
                tick += 1
                expected_rows.append(
                    (tick, state, TRAFFIC_OUTPUTS[state], timer_count)
                )
    results.check(
        "traffic FSM sequence, outputs, dwell times, and timer resets",
        traffic_log == expected_rows,
    )

    tags = tuple(range(8)) * 4
    sorter_log = run_sorter(tags)
    sorter_ok = all(
        tag == tags[index]
        and bin_name == BINS[tag]
        and count == index + 1
        for index, (tag, bin_name, count) in enumerate(sorter_log)
    )
    results.check("industrial sorter routing and running count", sorter_ok)

    capacity_ok = run_sorter((0 for _ in range(255)), 8)[-1][2] == 255
    capacity_ok &= _raises(
        OverflowError,
        run_sorter,
        (0 for _ in range(256)),
        8,
    )
    capacity_ok &= run_sorter((0 for _ in range(256)), 9)[-1][2] == 256
    results.check("sorter counter capacity and overflow handling", capacity_ok)

    invalid_cases = [
        (ValueError, run_traffic, (0,), {}),
        (TypeError, run_traffic, (1.5,), {}),
        (ValueError, sort_item, (-1,), {}),
        (ValueError, sort_item, (8,), {}),
        (TypeError, run_sorter, ("012",), {}),
        (TypeError, run_sorter, (5,), {}),
        (ValueError, run_sorter, ((0,), 0), {}),
    ]
    results.check("industrial boundary validation", _all_raise(invalid_cases))


def _verify_performance_models(results: Results) -> None:
    widths = (1, 2, 4, 8, 16, 32, 64)
    ripple_values = [ripple_delay(width) for width in widths]
    lookahead_values = [lookahead_delay(width) for width in widths]
    model_ok = ripple_values == [2 * width + 1 for width in widths]
    model_ok &= all(
        later > earlier
        for earlier, later in zip(ripple_values, ripple_values[1:])
    )
    model_ok &= all(
        later >= earlier
        for earlier, later in zip(lookahead_values, lookahead_values[1:])
    )
    results.check("analytical delay model consistency", model_ok)

    results.check(
        "primitive gate-evaluation model",
        all(ripple_gate_count(width) == 5 * width for width in widths),
    )

    invalid_cases = [
        (ValueError, ripple_delay, (0,), {}),
        (TypeError, ripple_delay, (True,), {}),
        (ValueError, lookahead_delay, (-1,), {}),
        (ValueError, ripple_gate_count, (0,), {}),
    ]
    results.check("performance-model input validation", _all_raise(invalid_cases))


def verify_all() -> Results:
    """Run every grouped verification category and return its results."""
    results = Results()
    _verify_gates(results)
    _verify_combinational(results)
    _verify_sequential(results)
    _verify_fsm(results)
    _verify_smart_home(results)
    _verify_industrial(results)
    _verify_performance_models(results)
    return results


if __name__ == "__main__":
    verification_results = verify_all()
    print("\n".join(verification_results.log))
    print(verification_results.summary())
    sys.exit(1 if verification_results.failed else 0)

    
