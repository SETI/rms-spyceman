##########################################################################################
# tests/test_import.py: The package imports and exposes its public API
##########################################################################################
"""Import tests.

These cover the modules that import quickly. The `spyceman.hosts` subpackages and the
per-body `spyceman.solarsystem` modules are deliberately excluded: importing them calls
KernelFile.set_info() once per KTuple, and each call signals SPICE errors that take
milliseconds apiece, so a single import runs for minutes. They are exercised by
test_hosts_slow.py, which is opt-in.
"""

import importlib

import pytest

# The modules that make up the public API, each of which must import on its own
CORE_MODULES = [
    'spyceman',
    'spyceman._cspyce',
    'spyceman._downloads',
    'spyceman._kernelinfo',
    'spyceman._ktypes',
    'spyceman._localfiles',
    'spyceman._spicefunc',
    'spyceman._utils',
    'spyceman.kernel',
    'spyceman.kernelfile',
    'spyceman.kernelset',
    'spyceman.kernelstack',
    'spyceman.metakernel',
    'spyceman.recipe',
    'spyceman.rule',
]

# The names that spyceman/__init__.py is expected to export
PUBLIC_NAMES = ['Kernel', 'KernelFile', 'KernelSet', 'KernelStack', 'KTuple',
                'Metakernel', 'Recipe', 'Rule']


@pytest.mark.parametrize('name', CORE_MODULES)
def test_module_imports(name):
    """Each core module imports on its own.

    Parameters:
        name (str): Fully qualified name of the module to import.
    """

    assert importlib.import_module(name) is not None


@pytest.mark.parametrize('name', PUBLIC_NAMES)
def test_public_name_is_exported(name):
    """Each documented public name is reachable as a spyceman attribute.

    Parameters:
        name (str): The attribute expected on the spyceman package.
    """

    import spyceman
    assert hasattr(spyceman, name), f'spyceman.{name} is missing'


def test_import_does_not_require_spicepath(monkeypatch):
    """Importing the package must not depend on the SPICEPATH environment variable.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture used to unset SPICEPATH.
    """

    monkeypatch.delenv('SPICEPATH', raising=False)
    assert importlib.import_module('spyceman') is not None


def test_walk_without_spicepath_is_not_fatal(monkeypatch):
    """KernelFile.walk() with no arguments and no SPICEPATH warns rather than raising.

    The "ignore", "warn", and "error" options are the three behaviors the older
    initialize() function offered.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): Fixture used to unset SPICEPATH.
    """

    monkeypatch.delenv('SPICEPATH', raising=False)
    from spyceman import KernelFile

    KernelFile.walk(missing='ignore')           # silent

    with pytest.warns(UserWarning, match='SPICEPATH'):
        from spyceman import _localfiles
        monkeypatch.setattr(_localfiles._get_spicepath, 'warned', False)
        KernelFile.walk(missing='warn')

    with pytest.raises(RuntimeError, match='SPICEPATH'):
        KernelFile.walk(missing='error')

    with pytest.raises(ValueError):
        KernelFile.walk(missing='nonsense')


def test_all_is_exactly_the_public_names():
    """__all__ lists every public name and nothing else."""

    import spyceman
    assert sorted(spyceman.__all__) == sorted(PUBLIC_NAMES)


def test_version_is_defined():
    """The package reports a version, which setuptools_scm writes at build time."""

    import spyceman
    assert isinstance(spyceman.__version__, str)
    assert spyceman.__version__

##########################################################################################
