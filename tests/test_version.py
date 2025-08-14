from importlib.metadata import version as _pkg_version

from krpsim import version


def test_version():
    assert version() == _pkg_version("krpsim")
