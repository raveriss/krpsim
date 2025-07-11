"""Verifier command line interface."""

import sys


def main(argv: list[str] | None = None) -> int:
    """Entry point for the krpsim verifier."""
    argv = argv or sys.argv[1:]
    print("krpsim verifier placeholder", argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
