##########################################################################################
# tests/test_hosts_slow.py: Imports of the host and per-body kernel catalogs
##########################################################################################
"""Opt-in tests that import the large kernel catalogs.

These are separated from test_import.py because they are slower than the rest of the
suite, not because they are optional. Importing spyceman.hosts.Cassini takes about 5
seconds and spyceman.hosts.Voyager about 1 second, measured on an Apple-silicon Mac, which
is dominated by resolving the NAIF IDs of the 1764 KTuples in Cassini's catalog.

Run them with:

    pytest -m slow

They are deselected by default, so a normal `pytest` run stays under three seconds.
"""

import importlib

import pytest

HOST_MODULES = ['spyceman.hosts.Cassini', 'spyceman.hosts.Voyager']

BODY_MODULES = ['spyceman.solarsystem.General', 'spyceman.solarsystem.Jupiter',
                'spyceman.solarsystem.Saturn', 'spyceman.solarsystem.Neptune']


@pytest.mark.slow
@pytest.mark.parametrize('name', HOST_MODULES)
def test_host_module_imports(name):
    """Each host catalog imports.

    Parameters:
        name (str): Fully qualified name of the host module to import.
    """

    assert importlib.import_module(name) is not None


@pytest.mark.slow
@pytest.mark.parametrize('name', BODY_MODULES)
def test_body_module_imports(name):
    """Each per-body catalog imports.

    Parameters:
        name (str): Fully qualified name of the solar system module to import.
    """

    assert importlib.import_module(name) is not None


@pytest.mark.slow
def test_host_package_is_capitalized():
    """The Cassini subpackage is importable under the name the README uses.

    The directory was tracked in git as "cassini" while existing on disk as "Cassini".
    On a case-sensitive filesystem, which is what CI runs on, a fresh checkout would
    therefore fail this import.
    """

    from spyceman.hosts import Cassini
    assert Cassini is not None

##########################################################################################
