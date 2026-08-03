"""
industrial.py -- An industrial-automation controller built from logic blocks.

Two classic industrial control problems demonstrate the same primitives in a
factory setting:

  * A traffic / intersection-style light sequencer implemented as an FSM whose
    dwell time in each state is timed by a hardware COUNTER (sequential logic).
  * A conveyor SORTER that reads a 3-bit product tag, decodes it with a
    3-to-8 DECODER, and diverts items to bins -- with a ripple-carry ADDER
    keeping a running count of processed items.

Course concepts demonstrated: FSM control, counters/timing, decoders,
binary arithmetic (adder), sequential + combinational integration.

Authors: Member C (application mapping) & Member D (integration)
"""
"""Industrial-automation applications for the ENCM 369 Topic 4 project.

The module combines a Moore traffic FSM with a binary phase counter and a
3-to-8 conveyor decoder with a ripple-carry processed-item counter.  It is an
educational software model, not a safety-certified industrial controller.
"""

from pathlib import Path
import sys
from typing import Iterable, List, Tuple

# Allow this file to run both directly and as part of the applications package.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.combinational import decoder_3to8, from_bits, ripple_carry_adder, to_bits
from logic.fsm import FSM
from logic.sequential import BinaryCounter


# Define the four traffic-light states in their operating sequence.
TRAFFIC_STATES: Tuple[str, ...] = (
    "NS_GREEN",
    "NS_YELLOW",
    "EW_GREEN",
    "EW_YELLOW",
)

# Move the Moore FSM to the next traffic phase after one completed dwell period.
TRAFFIC_TRANSITIONS = {
    ("NS_GREEN", "tick"): "NS_YELLOW",
    ("NS_YELLOW", "tick"): "EW_GREEN",
    ("EW_GREEN", "tick"): "EW_YELLOW",
    ("EW_YELLOW", "tick"): "NS_GREEN",
}

# Assign north-south and east-west light outputs to each Moore state.
TRAFFIC_OUTPUTS = {
    "NS_GREEN": "NS=GREEN  EW=RED",
    "NS_YELLOW": "NS=YELLOW EW=RED",
    "EW_GREEN": "NS=RED    EW=GREEN",
    "EW_YELLOW": "NS=RED    EW=YELLOW",
}

# Set how many clock ticks each traffic phase remains active.
PHASE_TICKS = {
    "NS_GREEN": 4,
    "NS_YELLOW": 2,
    "EW_GREEN": 4,
    "EW_YELLOW": 2,
}

# Map each 3-bit product tag to one of eight conveyor destinations.
BINS: Tuple[str, ...] = (
    "REJECT",
    "SMALL",
    "MEDIUM",
    "LARGE",
    "FRAGILE",
    "HEAVY",
    "PRIORITY",
    "SPARE",
)

TrafficLogEntry = Tuple[int, str, str, int]
SorterLogEntry = Tuple[int, str, int]
SortResult = Tuple[str, List[int]]


def _require_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_range(value: int, name: str, minimum: int, maximum: int) -> int:
    value = _require_integer(value, name)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in the range {minimum} to {maximum}")
    return value


def _require_positive_integer(value: int, name: str) -> int:
    value = _require_integer(value, name)
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


# Verify that every state has one transition, one output, and one dwell time.
def _validate_traffic_configuration() -> int:
    expected_transitions = {(state, "tick") for state in TRAFFIC_STATES}
    if set(TRAFFIC_TRANSITIONS) != expected_transitions:
        raise RuntimeError(
            "TRAFFIC_TRANSITIONS must define one tick transition per state"
        )
    if set(TRAFFIC_OUTPUTS) != set(TRAFFIC_STATES):
        raise RuntimeError(
            "TRAFFIC_OUTPUTS must define every traffic state exactly once"
        )
    if set(PHASE_TICKS) != set(TRAFFIC_STATES):
        raise RuntimeError(
            "PHASE_TICKS must define every traffic state exactly once"
        )
    if any(
        next_state not in TRAFFIC_STATES
        for next_state in TRAFFIC_TRANSITIONS.values()
    ):
        raise RuntimeError("traffic transition table contains an unknown state")

    for state, ticks in PHASE_TICKS.items():
        _require_positive_integer(ticks, f"PHASE_TICKS[{state!r}]")

    maximum_ticks = max(PHASE_TICKS.values())
    return max(1, maximum_ticks.bit_length())


# Build the Moore traffic controller from the transition and output tables.
def build_traffic_fsm() -> FSM:
    """Create the four-state Moore traffic FSM."""
    _validate_traffic_configuration()
    return FSM(
        start="NS_GREEN",
        transitions=dict(TRAFFIC_TRANSITIONS),
        outputs=dict(TRAFFIC_OUTPUTS),
    )


def run_traffic(cycles: int = 2) -> List[TrafficLogEntry]:
    """Run complete traffic cycles and return tick/state/output/timer rows."""
    cycles = _require_positive_integer(cycles, "cycles")
    # Create the traffic FSM and a binary counter for the current phase time.
    timer_width = _validate_traffic_configuration()
    fsm = build_traffic_fsm()
    timer = BinaryCounter(timer_width)

    log: List[TrafficLogEntry] = []
    global_tick = 0
    completed_phases = 0
    required_phases = len(TRAFFIC_STATES) * cycles

    while completed_phases < required_phases:
        state = fsm.state
        if state not in TRAFFIC_STATES:
            raise RuntimeError(f"traffic FSM entered an unknown state: {state!r}")

        target_ticks = PHASE_TICKS[state]
        global_tick += 1
        timer_count = timer.clock()
        output = fsm.output()
        if not isinstance(output, str):
            raise RuntimeError(f"traffic state {state!r} has no valid output")

        # Record the current tick, state, light outputs, and phase-counter value.
        log.append((global_tick, state, output, timer_count))

        # Advance the FSM and reset the timer when the dwell time is complete.
        if timer_count == target_ticks:
            fsm.step("tick")
            timer.reset()
            completed_phases += 1
        elif timer_count > target_ticks:
            raise RuntimeError("traffic phase timer exceeded its dwell time")

    return log


def sort_item(tag: int) -> SortResult:
    """Decode one 3-bit product tag into one bin and an 8-bit one-hot list."""
    # Convert the integer tag to three bits and activate one decoder output.
    tag = _require_range(tag, "tag", 0, len(BINS) - 1)
    a2, a1, a0 = to_bits(tag, 3)
    one_hot = decoder_3to8(a2, a1, a0)
    if len(one_hot) != len(BINS) or sum(one_hot) != 1:
        raise RuntimeError("3-to-8 decoder did not produce valid one-hot output")
    selected_index = one_hot.index(1)
    return BINS[selected_index], one_hot


def run_sorter(
    tags: Iterable[int],
    counter_width: int = 8,
) -> List[SorterLogEntry]:
    """Sort tagged items and count them with the ripple-carry adder."""
    if isinstance(tags, (str, bytes)):
        raise TypeError("tags must be an iterable of integer product tags")
    try:
        iterator = iter(tags)
    except TypeError as error:
        raise TypeError("tags must be iterable") from error

    # Initialize a fixed-width binary processed-item counter and a value of one.
    counter_width = _require_positive_integer(counter_width, "counter_width")
    count_bits = to_bits(0, counter_width)
    increment = to_bits(1, counter_width)
    log: List[SorterLogEntry] = []

    for item_number, tag in enumerate(iterator, start=1):
        # Decode the product destination and increment the binary count by one.
        bin_name, _ = sort_item(tag)
        next_count_bits, carry_out = ripple_carry_adder(count_bits, increment)
        # Reject the next item if the fixed-width counter cannot represent it.
        if carry_out:
            maximum = (1 << counter_width) - 1
            raise OverflowError(
                f"{counter_width}-bit counter overflowed at item {item_number}; "
                f"maximum count is {maximum}. Use a larger counter_width."
            )
        count_bits = next_count_bits
        processed_count = from_bits(count_bits)
        if processed_count != item_number:
            raise RuntimeError("processed-item counter produced an incorrect value")
        log.append((tag, bin_name, processed_count))

    return log


# Combine the traffic and conveyor simulations into one report-ready output.
def demo() -> str:
    """Run the industrial demonstrations and return a report-ready log."""
    log: List[str] = ["=== Industrial Automation Demo ==="]

    log.append("\n[Traffic sequencer -- Moore FSM + binary phase counter]")
    for tick, state, output, timer_count in run_traffic(cycles=1):
        log.append(f"  t={tick:02d} timer={timer_count} {state:<9} | {output}")

    log.append("\n[Conveyor sorter -- 3-to-8 decoder + ripple-carry counter]")
    sample_tags = (2, 5, 0, 7, 3, 3)
    for tag, bin_name, processed_count in run_sorter(sample_tags):
        log.append(
            f"  tag {tag:03b} -> bin {bin_name:<8} "
            f"(processed={processed_count})"
        )

    return "\n".join(log)


if __name__ == "__main__":
    print(demo())
