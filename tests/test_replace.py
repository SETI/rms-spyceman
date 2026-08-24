##########################################################################################
# tests/test_replace.py: Tests of _KernelInfo.replace() and its manual-definition replay
##########################################################################################
"""Tests of what survives when a kernel file is replaced by another of the same basename.

KernelFile.use_path(..., override=True) discards the _KernelInfo object for a basename and
builds a new one for the replacement file. Anything the file itself supplies is re-derived
from the new file, but anything the user assigned by hand has no other source, so it is
recorded as it is assigned and replayed onto the new object.

The replay is what these tests cover. A value that is derived from another -- the
alias-expanded NAIF IDs, or the primary IDs with the aliases removed -- has to be replayed
through the setter that derives it, not written into the field it lands in, or the
derivation is skipped and the other fields keep the None they were constructed with.
"""

import pytest

from spyceman import KernelFile

# 601 is Mimas and 699 is Saturn; both carry frame aliases, so the assigned set and the
# alias-expanded set are different and a test can tell which one it is looking at.
ASSIGNED_IDS = {601, 699}


@pytest.fixture
def replaceable(tmp_path, unique_name):
    """A registered kernel file plus a second file of the same basename.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
        unique_name (function): Fixture supplying unique basenames.

    Returns:
        (str, function): The basename, and a function called as replace() that registers
            the second file in place of the first.
    """

    basename = unique_name('replaced.bsp')
    first = tmp_path / 'first' / basename
    second = tmp_path / 'second' / basename
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text('the original file\n')
    second.write_text('the replacement file, of different content\n')

    KernelFile.use_path(first)

    def replace():
        """Register the second file under the same basename.

        Returns:
            pathlib.Path: The path now associated with the basename.
        """

        KernelFile.use_path(second, override=True)
        return second

    return (basename, replace)


def test_assigned_naif_ids_survive_as_found(replaceable):
    """The IDs the user assigned are still reported as the "as found" set.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).naif_ids = ASSIGNED_IDS
    replace()

    assert KernelFile(basename).naif_ids_as_found == ASSIGNED_IDS


def test_assigned_naif_ids_survive_with_aliases(replaceable):
    """The alias-expanded set is re-derived from the assigned IDs.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).naif_ids = ASSIGNED_IDS
    expanded = KernelFile(basename).naif_ids
    assert expanded > ASSIGNED_IDS      # otherwise this test proves nothing

    replace()

    assert KernelFile(basename).naif_ids == expanded


def test_assigned_naif_ids_survive_without_aliases(replaceable):
    """The primary-ID set is re-derived too, rather than being left undefined.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).naif_ids = ASSIGNED_IDS
    primary = KernelFile(basename).naif_ids_wo_aliases

    replace()

    assert KernelFile(basename).naif_ids_wo_aliases == primary


def test_as_found_ids_are_usable_in_a_union(replaceable):
    """The "as found" set can be unioned, which is how a metakernel reads its members.

    A metakernel's naif_ids getter accumulates "naif_ids |= member.naif_ids_as_found",
    so a member left holding None raises TypeError there rather than where it was set.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).naif_ids = ASSIGNED_IDS
    replace()

    assert set() | KernelFile(basename).naif_ids_as_found == ASSIGNED_IDS


def test_added_naif_ids_are_replayed(replaceable):
    """An ID added after the assignment is added again to the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    kernel = KernelFile(basename)
    kernel.naif_ids = ASSIGNED_IDS
    kernel.add_naif_ids(502)
    replace()

    assert KernelFile(basename).naif_ids_as_found == ASSIGNED_IDS | {502}


def test_removed_naif_ids_are_replayed(replaceable):
    """An ID removed after the assignment is removed again from the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    kernel = KernelFile(basename)
    kernel.naif_ids = ASSIGNED_IDS
    kernel.remove_naif_ids(699)
    replace()

    assert KernelFile(basename).naif_ids_as_found == {601}


def test_assigned_version_survives(replaceable):
    """A hand-assigned version is replayed onto the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).version = 7
    replace()

    assert KernelFile(basename).version == 7


def test_assigned_family_survives(replaceable):
    """A hand-assigned family name is replayed onto the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).family = 'test-family'
    replace()

    assert KernelFile(basename).family == 'test-family'


def test_assigned_release_date_survives(replaceable):
    """A hand-assigned release date is replayed onto the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).release_date = '2019-02-14'
    replace()

    assert KernelFile(basename).release_date == '2019-02-14'


def test_assigned_time_survives(replaceable):
    """A hand-assigned time range is replayed onto the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).time = (100., 200.)
    replace()

    assert KernelFile(basename).time == (100., 200.)


def test_added_properties_survive(replaceable):
    """A property added by hand is added again to the replacement.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    KernelFile(basename).add_property('mission', 'Cassini')
    replace()

    assert KernelFile(basename).properties['mission'] == 'Cassini'


def test_manual_definitions_survive_a_second_replacement(replaceable, tmp_path,
                                                         unique_name):
    """Replaying a definition records it again, so the next replacement still has it.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
        unique_name (function): Fixture supplying unique basenames.
    """

    (basename, replace) = replaceable
    kernel = KernelFile(basename)
    kernel.naif_ids = ASSIGNED_IDS
    kernel.version = 7
    replace()

    third = tmp_path / 'third' / basename
    third.parent.mkdir()
    third.write_text('a third file, of different content again\n')
    KernelFile.use_path(third, override=True)

    assert KernelFile(basename).naif_ids_as_found == ASSIGNED_IDS
    assert KernelFile(basename).version == 7


def test_the_replacement_path_is_the_one_in_use(replaceable):
    """The basename resolves to the replacement file, not the original.

    Parameters:
        replaceable ((str, function)): Fixture supplying a basename and a replace()
            function.
    """

    (basename, replace) = replaceable
    second = replace()

    assert KernelFile(basename).abspath == str(second.resolve())

##########################################################################################
