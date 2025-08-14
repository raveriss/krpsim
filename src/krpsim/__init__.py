"""krpsim package."""

from importlib import metadata

__all__ = ["version"]


def version() -> str:
    """Return installed package version."""
    return metadata.version("krpsim")
