"""Command-line interface for the payment terms synchroniser.

This module provides the entry point for running the tool from the command
line. It parses arguments, invokes the high-level runner, and prints where the
JSON report was written.
"""

from __future__ import annotations

import argparse  # Standard library for building CLIs
import sys  # Provides access to the interpreter's exit functionality

from .runner import run_payment_terms  # Orchestrator function to perform sync


def main(argv: list[str] | None = None) -> int:
    # Create an argument parser with a helpful description
    parser = argparse.ArgumentParser(
        description="Synchronise payment terms between Excel and QuickBooks"
    )
    # Required path to the Excel workbook with a 'payment_terms' sheet
    parser.add_argument(
        "--workbook",
        required=True,
        help="Excel workbook containing the payment_terms worksheet",
    )
    # Optional output path for the generated JSON report
    parser.add_argument("--output", help="Optional JSON output path")

    # Parse CLI arguments (from argv if provided, else from sys.argv)
    args = parser.parse_args(argv)

    # Run the synchronisation against the currently open QB company file ("")
    path = run_payment_terms("", args.workbook, output_path=args.output)
    # Inform the user where the report was saved
    print(f"Report written to {path}")
    return 0  # Zero exit code indicates success


if __name__ == "__main__":  # pragma: no cover - manual invocation
    # Allow the module to be executed directly: python -m payment_terms_cli
    sys.exit(main())
