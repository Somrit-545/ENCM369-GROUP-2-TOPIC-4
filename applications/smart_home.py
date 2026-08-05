from pathlib import Path
import sys
from typing import Iterable, List, Sequence, Tuple


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic.combinational import decoder_2to4, magnitude_comparator, mux4, to_bits
from logic.fsm import FSM


APPLIANCES: Tuple[str, ...] = (
    "LIGHTS",
    "THERMOSTAT",
    "LOCK",
    "ALARM",
)


SENSOR_NAMES: Tuple[str, ...] = (
    "door",
    "window",
    "motion",
    "smoke",
)


SECURITY_STATES: Tuple[str, ...] = (
    "DISARMED",
    "ARMED",
    "ALARM",
)


SECURITY_EVENTS: Tuple[str, ...] = (
    "arm",
    "disarm",
    "motion",
    "smoke",
    "clear",
)


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


SECURITY_OUTPUTS = {
    "DISARMED": "siren=OFF",
    "ARMED": "siren=OFF",
    "ALARM": "siren=ON",
}


THERMOSTAT_ACTIONS = {
    "A>B": "COOL",
    "A<B": "HEAT",
    "A=B": "IDLE",
}

SecurityTraceEntry = Tuple[str, str, str]
SmokeAlarmResult = Tuple[int, str, str]
CommandDecodeResult = Tuple[str, List[int]]


def _require_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _require_range(value: int, name: str, minimum: int, maximum: int) -> int:
    value = _require_integer(value, name)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in the range {minimum} to {maximum}")
    return value


def _require_bit(value: int, name: str) -> int:
    return _require_range(value, name, 0, 1)


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


def build_security_fsm() -> FSM:
    _validate_security_configuration()
    return FSM(
        start="DISARMED",
        transitions=dict(SECURITY_TRANSITIONS),
        outputs=dict(SECURITY_OUTPUTS),
    )


def run_security(events: Iterable[str]) -> List[SecurityTraceEntry]:
    if isinstance(events, (str, bytes)):
        raise TypeError("events must be an iterable of event strings")
    try:
        iterator = iter(events)
    except TypeError as error:
        raise TypeError("events must be iterable") from error


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

        state = fsm.step(event)
        output = fsm.output()
        if state not in SECURITY_STATES or not isinstance(output, str):
            raise RuntimeError("security FSM produced an invalid state or output")
        trace.append((event, state, output))
    return trace


def decode_command(cmd_code: int) -> CommandDecodeResult:

    cmd_code = _require_range(cmd_code, "cmd_code", 0, len(APPLIANCES) - 1)
    a1, a0 = to_bits(cmd_code, 2)
    one_hot = decoder_2to4(a1, a0)
    if len(one_hot) != len(APPLIANCES) or sum(one_hot) != 1:
        raise RuntimeError("2-to-4 decoder did not produce valid one-hot output")
    selected_index = one_hot.index(1)
    return APPLIANCES[selected_index], one_hot


def read_status(sensors: Sequence[int], channel_sel: int) -> int:
    if isinstance(sensors, (str, bytes)) or not isinstance(sensors, Sequence):
        raise TypeError("sensors must be a sequence of four digital readings")
    if len(sensors) != len(SENSOR_NAMES):
        raise ValueError("sensors must contain exactly four readings")


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

    s1, s0 = to_bits(channel_sel, 2)
    return mux4(*checked, s1, s0)


def apply_smoke_sensor(
    security: FSM,
    sensors: Sequence[int],
) -> SmokeAlarmResult:
    if not isinstance(security, FSM):
        raise TypeError("security must be an FSM instance")


    smoke_channel = SENSOR_NAMES.index("smoke")
    smoke_detected = read_status(sensors, smoke_channel)

    if smoke_detected == 1:
        security.step("smoke")

    state = security.state
    output = security.output()
    if state not in SECURITY_STATES or not isinstance(output, str):
        raise RuntimeError("smoke-alarm integration produced an invalid result")
    return smoke_detected, state, output


def thermostat(current_temp: int, setpoint: int, width: int = 6) -> str:
    width = _require_integer(width, "width")
    if width < 1:
        raise ValueError("width must be at least 1")


    maximum = (1 << width) - 1
    current_temp = _require_range(current_temp, "current_temp", 0, maximum)
    setpoint = _require_range(setpoint, "setpoint", 0, maximum)

    comparison = magnitude_comparator(
        to_bits(current_temp, width),
        to_bits(setpoint, width),
    )
    if comparison not in THERMOSTAT_ACTIONS:
        raise RuntimeError(
            f"magnitude comparator returned an unknown result: {comparison!r}"
        )
    return THERMOSTAT_ACTIONS[comparison]


def demo() -> str:
    log: List[str] = ["=== Smart-Home Controller Demo ==="]


    log.append("\n[Command decoder -- 2-to-4]")
    for code in range(len(APPLIANCES)):
        selected, one_hot = decode_command(code)
        log.append(f"  cmd {code:02b} -> {selected:<10} one-hot={one_hot}")


    log.append("\n[Security controller -- Moore FSM]")
    security = build_security_fsm()
    log.append(f"  start    -> {security.state:<9} [{security.output()}]")
    events = ("arm", "motion", "disarm", "arm", "motion", "clear", "disarm")
    for event, state, output in run_security(events):
        log.append(f"  {event:<8} -> {state:<9} [{output}]")


    log.append("\n[Sensor routing -- 4-to-1 multiplexer]")
    sensors = (1, 0, 1, 0)
    for channel, name in enumerate(SENSOR_NAMES):
        value = read_status(sensors, channel)
        log.append(f"  channel {channel} ({name:<7}) -> {value}")


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