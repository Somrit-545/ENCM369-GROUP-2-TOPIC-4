"""
smart_home.py -- A smart-home controller built from the project's logic blocks.

This ties the low-level digital logic to a realistic smart-home node. It shows
how the *same* combinational and sequential primitives found inside real
appliance microcontrollers implement useful behaviour:

  * A 2-to-4 DECODER routes a 2-bit command to one of four appliances
    (lights, thermostat, lock, alarm) -- i.e. address/command decoding.
  * A 4:1 MULTIPLEXER selects which sensor a status channel reports -- i.e.
    data routing.
  * An FSM implements the SECURITY state (DISARMED / ARMED / ALARM) -- i.e.
    a control unit with memory.
  * A magnitude COMPARATOR drives a simple thermostat decision.

Course concepts demonstrated: decoders, multiplexers, comparators, FSM control.

Authors: Member C (application mapping) & Member D (integration)
"""

from logic.combinational import decoder_2to4, mux4, magnitude_comparator, to_bits
from logic.fsm import FSM


# --- Security subsystem as an FSM -----------------------------------------
def build_security_fsm() -> FSM:
    """
    States: DISARMED, ARMED, ALARM.
    Inputs: 'arm', 'disarm', 'motion', 'clear'.
    """
    return FSM(
        start="DISARMED",
        transitions={
            ("DISARMED", "arm"): "ARMED",
            ("DISARMED", "motion"): "DISARMED",   # ignored while disarmed
            ("ARMED", "motion"): "ALARM",
            ("ARMED", "disarm"): "DISARMED",
            ("ALARM", "disarm"): "DISARMED",
            ("ALARM", "clear"): "ARMED",
        },
        outputs={
            "DISARMED": "siren=OFF",
            "ARMED": "siren=OFF",
            "ALARM": "siren=ON",
        },
    )


# --- Command decoding ------------------------------------------------------
APPLIANCES = ["LIGHTS", "THERMOSTAT", "LOCK", "ALARM"]


def decode_command(cmd_code: int):
    """
    Decode a 2-bit command code into a one-hot appliance selection using the
    gate-level 2-to-4 decoder.
    """
    a1, a0 = to_bits(cmd_code, 2)
    one_hot = decoder_2to4(a1, a0)
    selected = APPLIANCES[one_hot.index(1)]
    return selected, one_hot


# --- Sensor status routing -------------------------------------------------
def read_status(sensors, channel_sel: int) -> int:
    """
    `sensors` is a 4-tuple of 1-bit readings
    (door, window, motion, smoke). A 4:1 mux selects one for the status LED.
    """
    d0, d1, d2, d3 = sensors
    s1, s0 = to_bits(channel_sel, 2)
    return mux4(d0, d1, d2, d3, s1, s0)


# --- Thermostat decision ---------------------------------------------------
def thermostat(current_temp: int, setpoint: int, width: int = 6) -> str:
    """Compare measured vs. setpoint (unsigned) and command heat/cool/idle."""
    result = magnitude_comparator(to_bits(current_temp, width),
                                  to_bits(setpoint, width))
    return {"A>B": "COOL", "A<B": "HEAT", "A=B": "IDLE"}[result]


def demo():
    """Run a short scripted scenario and return a text log for the report."""
    log = []
    log.append("=== Smart-Home Controller Demo ===")

    # 1. Command decoding
    log.append("\n[Command decoder -- 2-to-4]")
    for code in range(4):
        sel, one_hot = decode_command(code)
        log.append(f"  cmd {code:02b} -> {sel:<10} one-hot={one_hot}")

    # 2. Security FSM
    log.append("\n[Security FSM]")
    fsm = build_security_fsm()
    events = ["arm", "motion", "disarm", "arm", "motion", "clear", "disarm"]
    log.append(f"  start: {fsm.state} ({fsm.output()})")
    for inp, state, out in fsm.run(events):
        log.append(f"  {inp:<8} -> {state:<9} [{out}]")

    # 3. Sensor status via mux
    log.append("\n[Sensor status routing -- 4:1 mux]")
    sensors = (1, 0, 1, 0)   # door=1, window=0, motion=1, smoke=0
    names = ["door", "window", "motion", "smoke"]
    for ch in range(4):
        log.append(f"  channel {ch} ({names[ch]:<7}) -> "
                   f"{read_status(sensors, ch)}")

    # 4. Thermostat
    log.append("\n[Thermostat -- magnitude comparator]")
    for temp in (18, 21, 25):
        log.append(f"  temp={temp}C, setpoint=21C -> {thermostat(temp, 21)}")

    return "\n".join(log)


if __name__ == "__main__":
    print(demo())
