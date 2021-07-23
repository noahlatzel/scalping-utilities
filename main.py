import sys
from pathlib import Path

# Ensure local `src/` is on the path for dev runs
_src = Path(__file__).parent / "src"
if _src.exists():
    sys.path.insert(0, str(_src))

from scalping_utilities.cli import main as cli_main


def main():
    # Delegate to CLI so `python main.py <args>` works too.
    if len(sys.argv) == 1:
        print("Usage: python main.py <product> [--condition N] [--mode ALL|BIN]")
        print("Tip: prefer `uv run run_plotly \"<product>\"` for the CLI entry point.")
        return
    # Pass through to CLI argument parser
    cli_main()


if __name__ == "__main__":
    main()
