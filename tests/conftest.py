##########################################################################################
# tests/conftest.py: Shared fixtures
##########################################################################################
"""Fixtures shared across the test suite.

Two pieces of global state make kernel tests order-dependent unless they are managed
deliberately, and both are handled here:

* _KernelInfo keeps one registry of every basename it has ever seen, for the lifetime of
  the process, and a basename cannot be re-registered with different metadata. The
  ``unique_name`` fixture hands out a distinct prefix to each test so that no two tests
  can collide, whatever order they run in.
* Kernel tracks what is furnished, plus the debug, download, and verbose switches, in
  module-level state. The ``spice_sandbox`` fixture saves all of it, puts the Kernel layer
  into debug mode so nothing reaches SPICE or the network, and restores it afterward.
"""

import itertools
import pathlib

import pytest

from spyceman import Kernel, KernelFile
import spyceman.kernel as kernel_module

_COUNTER = itertools.count(1)

# Extension to a minimal plausible file body. Metadata comes from the KTuples, so the
# content matters only where something reads the file; these keep that harmless.
_STUB_CONTENT = {
    '.tls': 'KPL/LSK\n\\begindata\nDELTET/DELTA_T_A = 32.184\n\\begintext\n',
    '.tpc': 'KPL/PCK\n\\begindata\nBODY499_RADII = ( 3396.19 3396.19 3376.2 )\n'
            '\\begintext\n',
    '.tf':  'KPL/FK\n\\begindata\nFRAME_TEST = -99000\n\\begintext\n',
}
_DEFAULT_CONTENT = 'stub kernel file\n'


@pytest.fixture
def unique_name():
    """A factory for basenames unique to the calling test.

    _KernelInfo registers every basename it sees in a process-wide dictionary and refuses
    to redefine one, so two tests that both used "test.bsp" would interfere. Each call
    returns a name no other test will use.

    Returns:
        function: Called as unique_name(suffix), where suffix is the part of the basename
            after the unique prefix, e.g. unique_name("2000.bsp").
    """

    prefix = f'zz{next(_COUNTER):05d}'

    def make(suffix):
        """Build one unique basename.

        Parameters:
            suffix (str): The trailing part of the basename, including its extension.

        Returns:
            str: The basename, prefixed so that it is unique within this session.
        """

        return f'{prefix}_{suffix}'

    return make


@pytest.fixture
def spice_sandbox():
    """Put the Kernel layer into debug mode and restore all global state afterward.

    In debug mode, furnish() and unload() record what they would have done without
    calling into SPICE, and downloads are disabled, so a test neither loads a kernel nor
    touches the network. The record of furnished basenames is cleared before the test and
    restored after it.

    Returns:
        dict: The mapping from ktype to the list of furnished basenames, so that a test
            can assert on what was furnished and in what order.
    """

    saved_furnished = {k: list(v) for k, v in kernel_module._FURNISHED_BASENAMES.items()}
    saved_debug = Kernel.debug()
    saved_download = Kernel.download()
    saved_verbose = Kernel.verbose()

    for basenames in kernel_module._FURNISHED_BASENAMES.values():
        basenames.clear()

    Kernel.debug(True)
    Kernel.download(False)
    Kernel.verbose(False)

    yield kernel_module._FURNISHED_BASENAMES

    Kernel.debug(saved_debug)
    Kernel.download(saved_download)
    Kernel.verbose(saved_verbose)
    for ktype, basenames in saved_furnished.items():
        kernel_module._FURNISHED_BASENAMES[ktype][:] = basenames


@pytest.fixture
def kernel_dir(tmp_path):
    """A factory that writes stub kernel files and registers them with spyceman.

    A file must exist on disk before it can be furnished, but its metadata comes from the
    KTuple that describes it, so the contents are stubs.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.

    Returns:
        function: Called as kernel_dir(*basenames); writes each one and registers the
            directory, returning the pathlib.Path of the directory.
    """

    def make(*basenames):
        """Write and register one or more stub kernel files.

        Parameters:
            *basenames (str): The basenames to create.

        Returns:
            pathlib.Path: The directory holding them.
        """

        for basename in basenames:
            ext = '.' + basename.rpartition('.')[-1]
            path = tmp_path / basename
            path.write_text(_STUB_CONTENT.get(ext, _DEFAULT_CONTENT))
            KernelFile.use_path(path)

        return tmp_path

    return make


@pytest.fixture
def furnished(spice_sandbox):
    """A helper returning the basenames furnished so far, in load order.

    Parameters:
        spice_sandbox (dict): Fixture providing the furnished-basename record.

    Returns:
        function: Called as furnished() for every ktype in load order, or
            furnished("SPK") for one ktype.
    """

    def report(ktype=None):
        """The furnished basenames.

        Parameters:
            ktype (str, optional): One kernel type; None for every type in load order.

        Returns:
            list[str]: The basenames furnished, in the order they were furnished.
        """

        if ktype is not None:
            return list(spice_sandbox[ktype])

        names = []
        for basenames in spice_sandbox.values():
            names += basenames
        return names

    return report

##########################################################################################
