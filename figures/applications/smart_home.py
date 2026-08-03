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
from pathlib import Path
import sys
from typing import Iterable, List, Sequence, Tuple

# Allow this file to run directly or as part of the applications package.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.combinational import decoder_2to4, magnitude_comparator, mux4, to_bits
from logic.fsm import FSM


# Define the four appliance targets controlled by the 2-to-4 decoder.
APPLIANCES: Tuple[str, ...] = (
    "LIGHTS",
    "THERMOSTAT",
    "LOCK",
    "ALARM",
)

# Assign one name to each input channel of the 4-to-1 sensor multiplexer.
SENSOR_NAMES: Tuple[str, ...] = (
    "door",
    "window",
    "motion",
    "smoke",
)

# Define the three operating states of the Moore security controller.
SECURITY_STATES: Tuple[str, ...] = (
    "DISARMED",
    "ARMED",
    "ALARM",
)

# Define every event accepted by the security FSM.
SECURITY_EVENTS: Tuple[str, ...] = (
    "arm",
    "disarm",
    "motion",
    "smoke",
    "clear",
)

# Map every current-state and event pair to the next security state.
SECURITY_TRANSITIONS = {
    ("DISARMED", "arm"): "ARMED",
    ("DISARMED", "disarm"): "DISARMED",
    ("DISARMED", "motion"): "DISARMED",
    ("DISARMED", "smoke"): "ALARM",
    ("DISARMED", "clear"): "DISARMED",
    ("ARMED", "arm"): "ARMED",
    ("ARMED", "disarm"): "DISARMED",
    ("ARMED", "motion"): "ALARM",
    ("ARMED", "smoke"): "ALARM",
    ("ARMED", "clear"): "ARMED",
    ("ALARM", "arm"): "ALARM",
    ("ALARM", "disarm"): "DISARMED",
    ("ALARM", "motion"): "ALARM",
    ("ALARM", "smoke"): "ALARM",
    ("ALARM", "clear"): "ARMED",
}

# Assign the siren output to each Moore state.
SECURITY_OUTPUTS = {
    "DISARMED": "siren=OFF",
    "ARMED": "siren=OFF",
    "ALARM": "siren=ON",
}

# Convert comparator results into thermostat control actions.
THERMOSTAT_ACTIONS = {
    "A>B": "COOL",
    "A<B": "HEAT",
    "A=B": "IDLE",
}

SecurityTraceEntry = Tuple[str, str, str]
SmokeAlarmResult = Tuple[int, str, str]
CommandDecodeResult = Tuple[str, List[int]]


# Validate that a value is an integer and not a Boolean value.
def _require_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


# Validate that an integer is inside the required inclusive range.
def _require_range(value: int, name: str, minimum: int, maximum: int) -> int:
    value = _require_integer(value, name)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in the range {minimum} to {maximum}")
    return value


# Restrict a digital signal to the valid binary values 0 and 1.
def _require_bit(value: int, name: str) -> int:
    return _require_range(value, name, 0, 1)


# Confirm that the security FSM tables are complete and internally valid.
def _validate_security_configuration() -> None:
    expected_pairs = {
        (state, event)
        for state in SECURITY_STATES
        for event in SECURITY_EVENTS
    }
    if set(SECURITY_TRANSITIONS) != expected_pairs:
        raise RuntimeError(
            "SECURITY_TRANSITIONS must define every state/event pair exactly once"
        )
    if set(SECURITY_OUTPUTS) != set(SECURITY_STATES):
        raise RuntimeError(
            "SECURITY_OUTPUTS must define every security state exactly once"
        )
    if any(
        next_state not in SECURITY_STATES
        for next_state in SECURITY_TRANSITIONS.values()
    ):
        raise RuntimeError("security transition table contains an unknown state")


# Build the complete Moore security FSM from the transition and output tables.
def build_security_fsm() -> FSM:
    """Create the complete three-state Moore security FSM."""
    _validate_security_configuration()
    return FSM(
        start="DISARMED",
        transitions=dict(SECURITY_TRANSITIONS),
        outputs=dict(SECURITY_OUTPUTS),
    )


def run_security(events: Iterable[str]) -> List[SecurityTraceEntry]:
    """Run validated security events and return a state/output trace."""
    if isinstance(events, (str, bytes)):
        raise TypeError("events must be an iterable of event strings")
    try:
        iterator = iter(events)
    except TypeError as error:
        raise TypeError("events must be iterable") from error

    # Start from DISARMED and record the state and output after each event.
    fsm = build_security_fsm()
    trace: List[SecurityTraceEntry] = []
    for event in iterator:
        if not isinstance(event, str):
            raise TypeError("each security event must be a string")
        if event not in SECURITY_EVENTS:
            allowed = ", ".join(SECURITY_EVENTS)
            raise ValueError(
                f"unknown security event {event!r}; expected one of: {allowed}"
            )
        # Apply one event, then read the new Moore state and siren output.
        state = fsm.step(event)
        output = fsm.output()
        if state not in SECURITY_STATES or not isinstance(output, str):
            raise RuntimeError("security FSM produced an invalid state or output")
        trace.append((event, state, output))
    return trace


def decode_command(cmd_code: int) -> CommandDecodeResult:
    """Decode command 0-3 into one appliance and a 4-bit one-hot output."""
    # Convert the command to two bits and activate one appliance output.
    cmd_code = _require_range(cmd_code, "cmd_code", 0, len(APPLIANCES) - 1)
    a1, a0 = to_bits(cmd_code, 2)
    one_hot = decoder_2to4(a1, a0)
    if len(one_hot) != len(APPLIANCES) or sum(one_hot) != 1:
        raise RuntimeError("2-to-4 decoder did not produce valid one-hot output")
    selected_index = one_hot.index(1)
    return APPLIANCES[selected_index], one_hot


def read_status(sensors: Sequence[int], channel_sel: int) -> int:
    """Select one of four digital sensor readings with the 4-to-1 mux."""
    if isinstance(sensors, (str, bytes)) or not isinstance(sensors, Sequence):
        raise TypeError("sensors must be a sequence of four digital readings")
    if len(sensors) != len(SENSOR_NAMES):
        raise ValueError("sensors must contain exactly four readings")

    # Validate all four sensor inputs before sending them to the multiplexer.
    checked = tuple(
        _require_bit(value, f"sensors[{index}]")
        for index, value in enumerate(sensors)
    )
    channel_sel = _require_range(
        channel_sel,
        "channel_sel",
        0,
        len(SENSOR_NAMES) - 1,
    )
    # Convert the channel number to select bits and route one sensor value.
    s1, s0 = to_bits(channel_sel, 2)
    return mux4(*checked, s1, s0)


def apply_smoke_sensor(
    security: FSM,
    sensors: Sequence[int],
) -> SmokeAlarmResult:
    """Read the smoke channel and trigger the security alarm when smoke is 1.

    The smoke detector is connected to channel 3 of the 4-to-1 multiplexer.
    A detected smoke signal triggers the ``smoke`` event from any security
    state, so the Moore FSM enters or remains in ``ALARM`` with ``siren=ON``.
    When smoke is 0, the current security state is preserved.
    """
    if not isinstance(security, FSM):
        raise TypeError("security must be an FSM instance")

    # Read channel 3, which is assigned to the smoke detector.
    smoke_channel = SENSOR_NAMES.index("smoke")
    smoke_detected = read_status(sensors, smoke_channel)
    # Trigger the smoke event so the FSM enters or remains in ALARM.
    if smoke_detected == 1:
        security.step("smoke")

    state = security.state
    output = security.output()
    if state not in SECURITY_STATES or not isinstance(output, str):
        raise RuntimeError("smoke-alarm integration produced an invalid result")
    return smoke_detected, state, output


def thermostat(current_temp: int, setpoint: int, width: int = 6) -> str:
    """Return HEAT, COOL, or IDLE using an unsigned fixed-width comparator."""
    width = _require_integer(width, "width")
    if width < 1:
        raise ValueError("width must be at least 1")

    # Calculate the largest unsigned temperature supported by this bit width.
    maximum = (1 << width) - 1
    current_temp = _require_range(current_temp, "current_temp", 0, maximum)
    setpoint = _require_range(setpoint, "setpoint", 0, maximum)
    # Compare the current temperature with the setpoint using fixed-width bits.
    comparison = magnitude_comparator(
        to_bits(current_temp, width),
        to_bits(setpoint, width),
    )
    if comparison not in THERMOSTAT_ACTIONS:
        raise RuntimeError(
            f"magnitude comparator returned an unknown result: {comparison!r}"
        )
    return THERMOSTAT_ACTIONS[comparison]


# Combine all smart-home subsystems into one report-ready demonstration.
def demo() -> str:
    """Run the smart-home demonstration and return a report-ready log."""
    log: List[str] = ["=== Smart-Home Controller Demo ==="]

    # Demonstrate all four command-decoder outputs.
    log.append("\n[Command decoder -- 2-to-4]")
    for code in range(len(APPLIANCES)):
        selected, one_hot = decode_command(code)
        log.append(f"  cmd {code:02b} -> {selected:<10} one-hot={one_hot}")

    # Demonstrate normal arm, motion, alarm, clear, and disarm transitions.
    log.append("\n[Security controller -- Moore FSM]")
    security = build_security_fsm()
    log.append(f"  start    -> {security.state:<9} [{security.output()}]")
    events = ("arm", "motion", "disarm", "arm", "motion", "clear", "disarm")
    for event, state, output in run_security(events):
        log.append(f"  {event:<8} -> {state:<9} [{output}]")

    # Demonstrate selection of each door, window, motion, and smoke channel.
    log.append("\n[Sensor routing -- 4-to-1 multiplexer]")
    sensors = (1, 0, 1, 0)
    for channel, name in enumerate(SENSOR_NAMES):
        value = read_status(sensors, channel)
        log.append(f"  channel {channel} ({name:<7}) -> {value}")

    # Demonstrate automatic fire-alarm activation from the smoke channel.
    log.append("\n[Fire detection -- smoke sensor + security FSM]")
    safe_security = build_security_fsm()
    safe_result = apply_smoke_sensor(safe_security, (0, 0, 0, 0))
    log.append(
        f"  smoke={safe_result[0]} -> {safe_result[1]:<9} "
        f"[{safe_result[2]}]"
    )
    fire_security = build_security_fsm()
    fire_result = apply_smoke_sensor(fire_security, (0, 0, 0, 1))
    log.append(
        f"  smoke={fire_result[0]} -> {fire_result[1]:<9} "
        f"[{fire_result[2]}]"
    )

    # Demonstrate HEAT, IDLE, and COOL decisions around one setpoint.
    log.append("\n[Thermostat -- 6-bit magnitude comparator]")
    setpoint = 21
    for temperature in (18, 21, 25):
        action = thermostat(temperature, setpoint)
        log.append(
            f"  temperature={temperature} °C, setpoint={setpoint} °C -> {action}"
        )

    return "\n".join(log)


if __name__ == "__main__":
    print(demo())


if __name__ == "__main__":
    print(demo())
