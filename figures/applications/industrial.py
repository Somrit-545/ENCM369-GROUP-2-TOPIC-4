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

from logic.combinational import (decoder_3to8, ripple_carry_adder,
                                 to_bits, from_bits)
from logic.sequential import BinaryCounter
from logic.fsm import FSM


# --- Traffic-light sequencer ----------------------------------------------
def build_traffic_fsm() -> FSM:
    """
    A 4-phase intersection controller.
    Input 'tick' advances the phase once the per-phase timer expires.
    """
    return FSM(
        start="NS_GREEN",
        transitions={
            ("NS_GREEN", "tick"): "NS_YELLOW",
            ("NS_YELLOW", "tick"): "EW_GREEN",
            ("EW_GREEN", "tick"): "EW_YELLOW",
            ("EW_YELLOW", "tick"): "NS_GREEN",
        },
        outputs={
            "NS_GREEN":  "NS=GREEN  EW=RED",
            "NS_YELLOW": "NS=YELLOW EW=RED",
            "EW_GREEN":  "NS=RED    EW=GREEN",
            "EW_YELLOW": "NS=RED    EW=YELLOW",
        },
    )


# Dwell time (in clock ticks) for each phase.
PHASE_TICKS = {"NS_GREEN": 4, "NS_YELLOW": 2, "EW_GREEN": 4, "EW_YELLOW": 2}


def run_traffic(cycles: int = 2):
    """
    Drive the traffic FSM using a hardware counter as the phase timer.
    Returns a log of (global_tick, state, output).
    """
    fsm = build_traffic_fsm()
    timer = BinaryCounter(3)
    log = []
    tick = 0
    phases_done = 0
    target = PHASE_TICKS[fsm.state]
    while phases_done < 4 * cycles:
        tick += 1
        count = timer.clock()
        log.append((tick, fsm.state, fsm.output(), count))
        if count >= target:
            fsm.step("tick")
            timer.reset()              # reset the timer for the next phase
            target = PHASE_TICKS[fsm.state]
            phases_done += 1
    return log


# --- Conveyor sorter -------------------------------------------------------
BINS = ["REJECT", "SMALL", "MEDIUM", "LARGE",
        "FRAGILE", "HEAVY", "PRIORITY", "SPARE"]


def sort_item(tag: int):
    """Decode a 3-bit product tag to a one-hot bin selection (3-to-8)."""
    a2, a1, a0 = to_bits(tag, 3)
    one_hot = decoder_3to8(a2, a1, a0)
    return BINS[one_hot.index(1)], one_hot


def run_sorter(tags):
    """
    Process a stream of tagged items, maintaining a running processed-count
    with the ripple-carry adder (8-bit).
    """
    log = []
    count_bits = to_bits(0, 8)
    one = to_bits(1, 8)
    for tag in tags:
        binname, _ = sort_item(tag)
        count_bits, _ = ripple_carry_adder(count_bits, one)   # count += 1
        log.append((tag, binname, from_bits(count_bits)))
    return log


def demo():
    log = ["=== Industrial Automation Demo ==="]

    log.append("\n[Traffic sequencer -- FSM timed by a 3-bit counter]")
    for tick, state, out, count in run_traffic(cycles=1):
        log.append(f"  t={tick:02d} timer={count} {state:<9} | {out}")

    log.append("\n[Conveyor sorter -- 3-to-8 decoder + running-count adder]")
    for tag, binname, running in run_sorter([2, 5, 0, 7, 3, 3]):
        log.append(f"  tag {tag:03b} -> bin {binname:<8} "
                   f"(processed={running})")

    return "\n".join(log)


if __name__ == "__main__":
    print(demo())
