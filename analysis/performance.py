"""
performance.py -- Performance / cost analysis and figure generation.

This module produces the quantitative results used in the report's Results &
Discussion section. It looks at the ripple-carry adder, which is the clearest
place where a computer-organization trade-off shows up in this project:

  1. Gate-delay model: worst-case propagation delay of an N-bit ripple-carry
     adder grows linearly (~2N gate delays), while an idealised carry-lookahead
     adder is roughly constant depth. -> figure 1

  2. Gate-count / hardware cost of the ripple-carry adder grows linearly with
     width. -> figure 2

  3. Empirical software cost: measured Python runtime of simulating the
     gate-level adder over many random operations, versus width. This shows how
     the linear carry chain also shows up as real simulation cost. -> figure 3

All figures are written to the figures/ directory as PNGs.

Author: Member D (analysis / integration)
Note: figure styling assisted by an AI tool; all models and numbers verified
by the team (see report Appendix / AI-use disclosure).
"""

from math import ceil, isfinite, log2
from pathlib import Path
import random
import statistics
import sys
import time
from typing import List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "figures"

# Support both the official package execution and direct script execution.
if __package__ in (None, "") and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.combinational import ripple_carry_adder, to_bits
from logic.gates import GATE_OPS


DEFAULT_WIDTHS: Tuple[int, ...] = (4, 8, 16, 32, 64)
DEFAULT_TRIALS = 2000
DEFAULT_REPEATS = 5
DEFAULT_RANDOM_SEED = 369


def _validate_positive_integer(value: int, name: str) -> None:
    """Require a positive non-Boolean integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 1:
        raise ValueError(f"{name} must be at least 1")


def _validate_widths(widths: Sequence[int]) -> Tuple[int, ...]:
    """Return validated adder widths as a non-empty tuple."""
    if isinstance(widths, (str, bytes)):
        raise TypeError("widths must be a sequence of positive integers")

    try:
        checked = tuple(widths)
    except TypeError as error:
        raise TypeError("widths must be an iterable of positive integers") from error

    if not checked:
        raise ValueError("widths must not be empty")

    for width in checked:
        _validate_positive_integer(width, "adder width")

    if len(set(checked)) != len(checked):
        raise ValueError("widths must not contain duplicate values")

    return checked


def _ensure_figure_directory() -> None:
    """Create the output directory and confirm that it is a directory."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    if not FIG_DIR.is_dir():
        raise RuntimeError(f"Figure output path is not a directory: {FIG_DIR}")


# ---------------------------------------------------------------------------
# 1. Simplified analytical delay models, in units of primitive gate delays.
# ---------------------------------------------------------------------------
def ripple_delay(n: int) -> int:
    """Estimate the implemented ripple-carry adder's worst-case delay.

    In the project's full-adder structure, the first carry requires three gate
    levels from an operand input. Each additional stage adds two more levels
    while the carry ripples through an AND and an OR gate. Therefore:

        delay = 3 + 2(n - 1) = 2n + 1
    """
    _validate_positive_integer(n, "adder width")
    return 2 * n + 1


def lookahead_delay(n: int) -> int:
    """Estimate a hierarchical carry-lookahead delay.

    This project does not implement a physical carry-lookahead adder. The
    comparison uses a simplified prefix-tree estimate: one level generates
    propagate/generate terms, each tree stage contributes two gate levels, and
    one final level forms the sum. The depth therefore grows with log2(n)
    instead of remaining constant for every word width.
    """
    _validate_positive_integer(n, "adder width")
    tree_levels = ceil(log2(n)) if n > 1 else 0
    return 2 * tree_levels + 2


def plot_delay(widths: Sequence[int]) -> Path:
    """Plot the two analytical delay estimates and return the PNG path."""
    checked_widths = _validate_widths(widths)
    _ensure_figure_directory()

    ripple = [ripple_delay(width) for width in checked_widths]
    lookahead = [lookahead_delay(width) for width in checked_widths]

    figure, axes = plt.subplots(figsize=(6, 4))
    axes.plot(checked_widths, ripple, "o-", label="Ripple-carry: 2N + 1")
    axes.plot(
        checked_widths,
        lookahead,
        "s--",
        label="Hierarchical lookahead estimate",
    )
    axes.set_xlabel("Adder width N (bits)")
    axes.set_ylabel("Simplified delay (gate-delay units)")
    axes.set_title("Analytical Adder Delay Models")
    axes.legend()
    axes.grid(True, alpha=0.3)
    figure.tight_layout()

    path = FIG_DIR / "fig1_adder_delay.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


# ---------------------------------------------------------------------------
# 2. Primitive gate-evaluation count in the Python simulator.
# ---------------------------------------------------------------------------
def ripple_gate_count(n: int) -> int:
    """Count primitive gate-function calls for one N-bit addition."""
    _validate_positive_integer(n, "adder width")

    GATE_OPS.reset()
    ripple_carry_adder(to_bits(0, n), to_bits(0, n))
    measured_count = GATE_OPS.count
    GATE_OPS.reset()

    # The current full_adder uses two XOR, two AND, and one OR evaluation.
    expected_count = 5 * n
    if measured_count != expected_count:
        raise RuntimeError(
            "Gate-evaluation count no longer matches the current full-adder "
            f"structure: measured {measured_count}, expected {expected_count}"
        )

    return measured_count


def plot_gate_count(widths: Sequence[int]) -> Tuple[List[int], Path]:
    """Plot primitive gate evaluations and return the values and PNG path."""
    checked_widths = _validate_widths(widths)
    _ensure_figure_directory()

    counts = [ripple_gate_count(width) for width in checked_widths]

    figure, axes = plt.subplots(figsize=(6, 4))
    axes.bar([str(width) for width in checked_widths], counts)
    axes.set_xlabel("Adder width N (bits)")
    axes.set_ylabel("Primitive gate evaluations per addition")
    axes.set_title("Ripple-Carry Simulation Gate Evaluations")
    axes.grid(True, axis="y", alpha=0.3)
    figure.tight_layout()

    path = FIG_DIR / "fig2_gate_count.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return counts, path


# ---------------------------------------------------------------------------
# 3. Empirical Python runtime of the gate-level simulation.
# ---------------------------------------------------------------------------
def measure_runtime(
    widths: Sequence[int],
    trials: int = DEFAULT_TRIALS,
    repeats: int = DEFAULT_REPEATS,
    seed: int = DEFAULT_RANDOM_SEED,
) -> List[float]:
    """Measure median adder-only Python runtime in microseconds per addition.

    Random integers are generated deterministically and converted to bit lists
    before the timer starts. Each width is timed several times using the same
    prepared operands, and the median repeat is reported to reduce noise.
    """
    checked_widths = _validate_widths(widths)
    _validate_positive_integer(trials, "trials")
    _validate_positive_integer(repeats, "repeats")

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    median_times = []

    for width in checked_widths:
        generator = random.Random(seed + width)
        prepared_operands = [
            (
                to_bits(generator.randrange(1 << width), width),
                to_bits(generator.randrange(1 << width), width),
            )
            for _ in range(trials)
        ]

        # Warm up the interpreter and imported functions before measurement.
        for a_bits, b_bits in prepared_operands[: min(32, trials)]:
            ripple_carry_adder(a_bits, b_bits)

        repeat_times = []
        for _ in range(repeats):
            start = time.perf_counter()
            for a_bits, b_bits in prepared_operands:
                ripple_carry_adder(a_bits, b_bits)
            elapsed_seconds = time.perf_counter() - start
            repeat_times.append(elapsed_seconds / trials * 1e6)

        median_time = statistics.median(repeat_times)
        if not isfinite(median_time) or median_time <= 0:
            raise RuntimeError(
                f"Invalid runtime measurement for {width}-bit addition"
            )
        median_times.append(median_time)

    GATE_OPS.reset()
    return median_times


def plot_runtime(widths: Sequence[int], times: Sequence[float]) -> Path:
    """Plot median Python simulation runtime and return the PNG path."""
    checked_widths = _validate_widths(widths)
    checked_times = tuple(times)

    if len(checked_times) != len(checked_widths):
        raise ValueError("times must contain one value for each adder width")
    if not checked_times:
        raise ValueError("times must not be empty")

    for measured_time in checked_times:
        if isinstance(measured_time, bool) or not isinstance(
            measured_time, (int, float)
        ):
            raise TypeError("runtime values must be numeric")
        if not isfinite(float(measured_time)) or measured_time <= 0:
            raise ValueError("runtime values must be finite and positive")

    _ensure_figure_directory()

    figure, axes = plt.subplots(figsize=(6, 4))
    axes.plot(checked_widths, checked_times, "o-")
    axes.set_xlabel("Adder width N (bits)")
    axes.set_ylabel("Median simulation time (microseconds per addition)")
    axes.set_title("Python Runtime of Gate-Level Ripple-Carry Addition")
    axes.grid(True, alpha=0.3)
    figure.tight_layout()

    path = FIG_DIR / "fig3_runtime.png"
    figure.savefig(path, dpi=130)
    plt.close(figure)
    return path


def run_all() -> str:
    """Run all analyses, save the three figures, and return a text report."""
    _ensure_figure_directory()
    widths = DEFAULT_WIDTHS
    log = ["=== Performance Analysis ==="]

    delay_path = plot_delay(widths)
    ripple_values = {width: ripple_delay(width) for width in widths}
    lookahead_values = {width: lookahead_delay(width) for width in widths}
    log.append(f"[fig1] ripple delay units    {ripple_values}")
    log.append(f"       lookahead estimate   {lookahead_values}")
    log.append(f"       saved -> {delay_path.name}")

    counts, count_path = plot_gate_count(widths)
    log.append(f"[fig2] gate evaluations     {dict(zip(widths, counts))}")
    log.append(f"       saved -> {count_path.name}")

    times = measure_runtime(widths)
    runtime_path = plot_runtime(widths, times)
    log.append(
        "[fig3] median runtime (us/add; conversion excluded): "
        + ", ".join(
            f"{width}b={measured_time:.2f}"
            for width, measured_time in zip(widths, times)
        )
    )
    log.append(
        f"       {DEFAULT_REPEATS} repeats x {DEFAULT_TRIALS} trials; "
        f"seed={DEFAULT_RANDOM_SEED}"
    )
    log.append(f"       saved -> {runtime_path.name}")

    return "\n".join(log)


if __name__ == "__main__":
    print(run_all())
