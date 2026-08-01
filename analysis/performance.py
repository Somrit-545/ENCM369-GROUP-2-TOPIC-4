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

import os
import time
import random
import matplotlib
matplotlib.use("Agg")               # headless backend
import matplotlib.pyplot as plt

from logic.gates import GATE_OPS
from logic.combinational import ripple_carry_adder, to_bits

FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")


# ---------------------------------------------------------------------------
# 1. Gate-delay models (in units of "gate delays").
# ---------------------------------------------------------------------------
def ripple_delay(n: int) -> int:
    """Worst-case ripple-carry delay ~ 2 gate-delays per full-adder stage."""
    return 2 * n + 1


def lookahead_delay(n: int) -> int:
    """
    Idealised carry-lookahead delay: carry generated in a small constant
    number of levels regardless of width (log/const depth). Modelled as a
    constant here to contrast the asymptotic behaviour.
    """
    return 4


def plot_delay(widths):
    ripple = [ripple_delay(n) for n in widths]
    lookahead = [lookahead_delay(n) for n in widths]
    plt.figure(figsize=(6, 4))
    plt.plot(widths, ripple, "o-", label="Ripple-carry (~2N)")
    plt.plot(widths, lookahead, "s--", label="Carry-lookahead (ideal, const)")
    plt.xlabel("Adder width N (bits)")
    plt.ylabel("Worst-case delay (gate delays)")
    plt.title("Adder propagation delay vs. word width")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig1_adder_delay.png")
    plt.savefig(path, dpi=130)
    plt.close()
    return path


# ---------------------------------------------------------------------------
# 2. Gate-count / hardware cost.
# ---------------------------------------------------------------------------
def ripple_gate_count(n: int) -> int:
    """
    Count primitive gate evaluations for one N-bit ripple-carry addition by
    running it with the shared gate counter.
    """
    GATE_OPS.reset()
    ripple_carry_adder(to_bits(0, n), to_bits(0, n))
    return GATE_OPS.count


def plot_gate_count(widths):
    counts = [ripple_gate_count(n) for n in widths]
    plt.figure(figsize=(6, 4))
    plt.bar([str(n) for n in widths], counts, color="#3b76c9")
    plt.xlabel("Adder width N (bits)")
    plt.ylabel("Primitive gate evaluations")
    plt.title("Ripple-carry adder hardware cost vs. width")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig2_gate_count.png")
    plt.savefig(path, dpi=130)
    plt.close()
    return counts, path


# ---------------------------------------------------------------------------
# 3. Empirical software runtime of the gate-level simulation.
# ---------------------------------------------------------------------------
def measure_runtime(widths, trials=4000):
    times = []
    for n in widths:
        operands = [(random.randrange(1 << n), random.randrange(1 << n))
                    for _ in range(trials)]
        start = time.perf_counter()
        for x, y in operands:
            ripple_carry_adder(to_bits(x, n), to_bits(y, n))
        elapsed = (time.perf_counter() - start) / trials * 1e6  # microseconds
        times.append(elapsed)
    return times


def plot_runtime(widths, times):
    plt.figure(figsize=(6, 4))
    plt.plot(widths, times, "o-", color="#c0392b")
    plt.xlabel("Adder width N (bits)")
    plt.ylabel("Mean simulated add time (microseconds)")
    plt.title("Measured runtime of gate-level ripple-carry addition")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig3_runtime.png")
    plt.savefig(path, dpi=130)
    plt.close()
    return path


def run_all():
    os.makedirs(FIG_DIR, exist_ok=True)
    widths = [4, 8, 16, 32, 64]
    log = ["=== Performance Analysis ==="]

    p1 = plot_delay(widths)
    log.append(f"[fig1] adder delay model      -> {os.path.basename(p1)}")

    counts, p2 = plot_gate_count(widths)
    log.append(f"[fig2] gate counts {dict(zip(widths, counts))}")
    log.append(f"       saved -> {os.path.basename(p2)}")

    times = measure_runtime(widths)
    p3 = plot_runtime(widths, times)
    log.append("[fig3] runtime (us): "
               + ", ".join(f"{n}b={t:.2f}" for n, t in zip(widths, times)))
    log.append(f"       saved -> {os.path.basename(p3)}")

    return "\n".join(log)


if __name__ == "__main__":
    print(run_all())
