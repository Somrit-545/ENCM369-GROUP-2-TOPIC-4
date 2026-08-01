"""
main.py -- Project entry point.

Runs the full pipeline in order and prints a consolidated report to stdout:
  1. Verification of every logic block (exhaustive truth-table checks).
  2. Smart-home controller demo.
  3. Industrial-automation demo.
  4. Performance analysis (writes figures to figures/).

Usage:
    python main.py

Topic: Designing Digital Logic for Smart Home and Industrial Automation Systems
ENCM 369 -- Computer Organization -- Group Project
"""

from tests.verify import verify_all
from applications.smart_home import demo as smart_home_demo
from applications.industrial import demo as industrial_demo
from analysis.performance import run_all as run_performance


def main():
    print("#" * 68)
    print("# Designing Digital Logic for Smart Home & Industrial Automation")
    print("# ENCM 369 -- Computer Organization")
    print("#" * 68)

    print("\n### 1. VERIFICATION ###")
    results = verify_all()
    print("\n".join(results.log))
    print(results.summary())

    print("\n\n### 2. SMART-HOME APPLICATION ###\n")
    print(smart_home_demo())

    print("\n\n### 3. INDUSTRIAL AUTOMATION APPLICATION ###\n")
    print(industrial_demo())

    print("\n\n### 4. PERFORMANCE ANALYSIS ###\n")
    print(run_performance())

    print("\n\nDone. Figures written to ./figures/")


if __name__ == "__main__":
    main()
