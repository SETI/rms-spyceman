##########################################################################################
# tests/test_kernelinfo.py: Tests of _KernelInfo's file-reading fallbacks
##########################################################################################
"""Tests of the paths _KernelInfo takes when a kernel file cannot be read.

These cover defensive branches that ordinary use never reaches, which is exactly why they
had gone untested: a corrupt or truncated kernel is rare, and the code that copes with one
only runs when it happens. Both defects this file guards against were in a single line of
that code, and neither could produce a wrong answer -- only a crash, at the moment the
library was trying to recover from something else.
"""

import warnings

import julian
import pytest

from spyceman import KernelFile
from spyceman.rule import Rule


@pytest.fixture
def unreadable_binary_kernel(tmp_path, unique_name):
    """A file whose header claims to be a DAF but whose contents are not one.

    The header is what makes _KernelInfo try to read embedded comments from it, and the
    contents are what make that attempt fail.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
        unique_name (function): Fixture supplying unique basenames.

    Returns:
        str: The basename of the registered file.
    """

    basename = unique_name('corrupt.bc')
    path = tmp_path / basename
    path.write_bytes(b'DAF/CK  this is not a real DAF file')
    KernelFile.use_path(path)
    return basename


def test_unreadable_comments_yield_an_empty_list(unreadable_binary_kernel):
    """A kernel whose comments cannot be read reports no comments rather than raising.

    Comments are optional, so failing to read them is not fatal.

    Parameters:
        unreadable_binary_kernel (str): Fixture supplying a corrupt kernel's basename.
    """

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        comments = KernelFile(unreadable_binary_kernel)._info.comments

    assert comments == []


def test_unreadable_comments_warn_and_name_the_file(unreadable_binary_kernel):
    """The warning identifies the file and the underlying error.

    Falling back silently is what the warning replaced: a corrupt kernel usually shows up
    here first, and an empty comment list looks exactly like a kernel that has none.

    Parameters:
        unreadable_binary_kernel (str): Fixture supplying a corrupt kernel's basename.
    """

    with pytest.warns(UserWarning, match='unable to read comments') as caught:
        KernelFile(unreadable_binary_kernel)._info.comments

    message = str(caught[0].message)
    assert unreadable_binary_kernel in message
    assert 'OSError' in message


def test_times_from_the_basename_need_no_local_file(unique_name):
    """A kernel whose dates come from its basename reports them without being downloaded.

    Most of a catalog has no local copy until something asks for one, and the rules exist
    precisely so that a kernel can be selected on its dates beforehand. Reading the file
    is the last resort, not the first.

    The closing date is inclusive: a kernel labelled through 20010101 covers that whole
    day, so its upper limit is the start of the next one.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('20000101_20010101.bsp')
    prefix = basename.partition('_')[0]
    Rule(rf'{prefix}_(YYYYMMDD)_(YYYYMMDD)\.bsp', family='Test-SPK')

    kernel = KernelFile(basename)
    assert not kernel.exists

    (tmin, tmax) = kernel.time
    assert tmin == pytest.approx(julian.tdb_from_iso('2000-01-01'))
    assert tmax == pytest.approx(julian.tdb_from_iso('2001-01-02'))


def test_a_kernel_with_no_dates_anywhere_still_reports_its_absence(unique_name):
    """A kernel whose times can come only from the file raises when there is no file.

    The check for a local copy moved below the basename rules; it still has to fire for a
    kernel the rules say nothing about.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('undated.bsp')

    with pytest.raises(ValueError, match='kernel file does not exist'):
        KernelFile(basename).time

##########################################################################################
