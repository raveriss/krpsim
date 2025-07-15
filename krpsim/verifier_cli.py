"""Command line interface for krpsim verifier."""

from __future__ import annotations

import sys

def main(argv: list[str] | None = None) -> int:
    """Entry point for the verifier CLI."""
    argv = argv or sys.argv[1:]
    print("krpsim verifier placeholder", argv)
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
