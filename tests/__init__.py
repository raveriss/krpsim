"""Test package setup."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow importing the ``krpsim`` package from ``src`` without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
