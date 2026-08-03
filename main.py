from pathlib import Path
import struct
import sys
from typing import Callable, Tuple

from analysis.performance import run_all as run_performance
from applications.industrial import demo as industrial_demo
from applications.smart_home import demo as smart_home_demo
from tests.verify import Results, verify_all


PROJECT_ROOT = Path(__file__).resolve().parent
FIGURE_DIRECTORY = PROJECT_ROOT / "figures"

EXPECTED_FIGURES: Tuple[str, ...] = (
    "fig1_adder_delay.png",
    "fig2_gate_count.png",
    "fig3_runtime.png",
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def run_text_stage(
    stage_name: str,
    stage_function: Callable[[], str],
) -> str:
    """Run one project stage and print its validated text output."""
    output = stage_function()

    if not isinstance(output, str):
        raise TypeError(
            f"{stage_name} must return a string"
        )

    if not output.strip():
        raise ValueError(
            f"{stage_name} returned an empty result"
        )

    print(output)
    return output


def prepare_figure_directory() -> None:
    """Create the figures folder and remove old expected figures."""
    FIGURE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not FIGURE_DIRECTORY.is_dir():
        raise RuntimeError(
            f"Figure path is not a directory: "
            f"{FIGURE_DIRECTORY}"
        )

    for filename in EXPECTED_FIGURES:
        figure_path = FIGURE_DIRECTORY / filename

        if figure_path.exists():
            if not figure_path.is_file():
                raise RuntimeError(
                    f"Figure path is not a file: "
                    f"{figure_path}"
                )

            figure_path.unlink()


def _read_png_dimensions(path: Path) -> Tuple[int, int]:
    """Read the PNG signature and image dimensions."""
    with path.open("rb") as image_file:
        header = image_file.read(24)

    if len(header) != 24:
        raise RuntimeError(
            f"PNG file is too short: {path.name}"
        )

    if header[:8] != PNG_SIGNATURE:
        raise RuntimeError(
            f"Invalid PNG signature: {path.name}"
        )

    if header[12:16] != b"IHDR":
        raise RuntimeError(
            f"PNG file has no valid IHDR chunk: "
            f"{path.name}"
        )

    width, height = struct.unpack(
        ">II",
        header[16:24],
    )

    return width, height


def verify_generated_figures(
    performance_output: str,
) -> None:
    """Confirm that all generated figures are valid PNG files."""
    for filename in EXPECTED_FIGURES:
        figure_path = FIGURE_DIRECTORY / filename

        if not figure_path.is_file():
            raise FileNotFoundError(
                f"Performance figure was not created: "
                f"{filename}"
            )

        if figure_path.stat().st_size <= 1000:
            raise RuntimeError(
                f"Performance figure is unexpectedly small: "
                f"{filename}"
            )

        width, height = _read_png_dimensions(
            figure_path
        )

        if width < 400 or height < 250:
            raise RuntimeError(
                "Performance figure resolution is too small: "
                f"{filename} ({width}x{height})"
            )

        if filename not in performance_output:
            raise RuntimeError(
                "Performance report does not reference "
                f"figure: {filename}"
            )


def main() -> int:
    """Run the complete project and return an exit status."""
    print("#" * 68)
    print(
        "# Designing Digital Logic for "
        "Smart Home & Industrial Automation"
    )
    print(
        "# ENCM 369 -- Computer Organization"
    )
    print("#" * 68)

    try:
        print("\n### 1. VERIFICATION ###")

        results = verify_all()

        if not isinstance(results, Results):
            raise TypeError(
                "verify_all() must return a Results object"
            )

        total_results = (
            results.passed + results.failed
        )

        if total_results != len(results.log):
            raise RuntimeError(
                "Verification counts do not match "
                "the result log"
            )

        if results.log:
            print("\n".join(results.log))

        print(results.summary())

        if results.failed:
            print(
                "\nERROR: Verification failed. "
                "Later stages were not executed.",
                file=sys.stderr,
            )
            return 1

        print(
            "\n\n### 2. SMART-HOME APPLICATION ###\n"
        )

        run_text_stage(
            "Smart-home demo",
            smart_home_demo,
        )

        print(
            "\n\n### 3. INDUSTRIAL "
            "AUTOMATION APPLICATION ###\n"
        )

        run_text_stage(
            "Industrial automation demo",
            industrial_demo,
        )

        print(
            "\n\n### 4. PERFORMANCE ANALYSIS ###\n"
        )

        prepare_figure_directory()

        performance_output = run_text_stage(
            "Performance analysis",
            run_performance,
        )

        verify_generated_figures(
            performance_output
        )

    except Exception as error:
        print(
            f"\nERROR: "
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        "\n  PASS  Three current-run "
        "PNG figures validated"
    )

    print(
        "\nProject pipeline completed successfully."
    )

    print(
        f"Figures written to: {FIGURE_DIRECTORY}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())