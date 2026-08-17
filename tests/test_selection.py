##########################################################################################
# tests/test_selection.py: Behavioral tests of kernel selection
##########################################################################################
"""Tests of which kernels a generated selection function chooses.

Every public spk(), ck(), pck() in the package is built by _spicefunc(), so these tests
build small synthetic catalogs and assert on what comes back. Selection reads only the
metadata carried by the KTuples, so no file has to exist and nothing reaches SPICE or the
network.

The failure mode these guard against is silence. A constraint that is quietly ignored, or
a kernel quietly dropped, produces a result that looks entirely reasonable; §6.20 of the
2026-08-16 critique was a leapseconds kernel that was never furnished while every call
reported success. So each test asserts the exact set of basenames chosen, never merely
that something was returned.
"""

import pytest

from spyceman import Kernel, KernelFile, KernelSet, KTuple
from spyceman._spicefunc import _spicefunc


def basenames_of(kernel):
    """The sorted basenames of a selection result.

    Parameters:
        kernel (Kernel, optional): The result of a selection function, or None if nothing
            was selected.

    Returns:
        list[str]: The basenames, sorted; an empty list if nothing was selected.
    """

    if kernel is None:
        return []

    return sorted(kernel.basenames)


@pytest.fixture
def spk_catalog(unique_name):
    """Three consecutive SPKs, two for Mars and one for Jupiter.

    Coverage is contiguous and non-overlapping, one year each through 2000-2003, so that
    a time constraint has exactly one right answer.

    Parameters:
        unique_name (function): Fixture supplying basenames unique to this test.

    Returns:
        (function, list[str]): The generated selection function and the basenames it
            knows, in order of increasing precedence.
    """

    names = [unique_name('2000.bsp'), unique_name('2001.bsp'), unique_name('2002.bsp')]
    ktuples = [
        KTuple(names[0], '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(names[1], '2001-01-01', '2002-01-01', {499}, '2011-01-01'),
        KTuple(names[2], '2002-01-01', '2003-01-01', {599}, '2012-01-01'),
    ]
    return (_spicefunc('spk', 'Test SPK', known=ktuples), names)


##########################################################################################
# No constraints, and no match
##########################################################################################

def test_an_unconstrained_call_returns_every_known_kernel(spk_catalog):
    """With no constraints, every catalogued kernel is selected.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk()) == sorted(names)


def test_a_constraint_matching_nothing_returns_none(spk_catalog):
    """A constraint no kernel satisfies yields None rather than an empty Kernel.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, _) = spk_catalog
    assert spk(ids=999) is None


def test_one_match_returns_a_kernelfile_and_several_return_a_kernelset(spk_catalog):
    """A single selected file comes back as a KernelFile, several as a KernelSet.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert isinstance(spk(basename=names[0]), KernelFile)
    assert isinstance(spk(ids=499), KernelSet)


##########################################################################################
# Time
##########################################################################################

def test_a_time_window_selects_only_the_overlapping_kernel(spk_catalog):
    """A window inside one kernel's coverage selects that kernel alone.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(tmin='2001-06-01', tmax='2001-07-01')) == [names[1]]


def test_a_time_window_spanning_two_kernels_selects_both(spk_catalog):
    """A window crossing a boundary selects both kernels that cover part of it.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    selected = basenames_of(spk(tmin='2001-06-01', tmax='2002-06-01'))
    assert selected == sorted([names[1], names[2]])


def test_a_time_window_outside_all_coverage_selects_nothing(spk_catalog):
    """A window no kernel covers yields None.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, _) = spk_catalog
    assert spk(tmin='1990-01-01', tmax='1991-01-01') is None


def test_only_tmin_leaves_the_upper_end_unconstrained(spk_catalog):
    """Supplying tmin alone selects every kernel whose coverage reaches it or later.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(tmin='2002-06-01')) == [names[2]]


##########################################################################################
# NAIF IDs
##########################################################################################

def test_a_naif_id_selects_only_the_kernels_that_cover_it(spk_catalog):
    """An ID constraint drops the kernels that do not mention that body.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(ids=499)) == sorted([names[0], names[1]])
    assert basenames_of(spk(ids=599)) == [names[2]]


def test_a_set_of_naif_ids_selects_the_union(spk_catalog):
    """Several IDs select every kernel covering at least one of them.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(ids={499, 599})) == sorted(names)


def test_a_kernel_with_no_naif_ids_applies_to_every_id(unique_name):
    """A kernel that specifies no NAIF IDs is selected whatever IDs are requested.

    An empty ID set means "applies to everything", not "applies to nothing". Reading it
    the second way is what made §6.20 drop every leapseconds kernel, and nothing raised:
    the call returned a Kernel and simply omitted the file.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    universal = unique_name('all.bsp')
    specific = unique_name('mars.bsp')
    spk = _spicefunc('spk', 'Test SPK', known=[
        KTuple(universal, '2000-01-01', '2003-01-01', None, '2010-01-01'),
        KTuple(specific, '2000-01-01', '2003-01-01', {499}, '2010-01-01'),
    ])

    assert KernelFile(universal).naif_ids == set()
    assert basenames_of(spk(ids=499)) == sorted([universal, specific])
    assert basenames_of(spk(ids=699)) == [universal]
    assert basenames_of(spk()) == sorted([universal, specific])


##########################################################################################
# Basename, version, and release date
##########################################################################################

def test_a_basename_selects_exactly_that_file(spk_catalog):
    """Naming a basename selects it and nothing else.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(basename=names[1])) == [names[1]]


def test_a_pattern_selects_every_matching_file(unique_name):
    """A regular expression selects each basename it matches in full.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    keep_a = unique_name('keep_a.bsp')
    keep_b = unique_name('keep_b.bsp')
    drop = unique_name('drop.bsp')
    spk = _spicefunc('spk', 'Test SPK', known=[
        KTuple(keep_a, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(keep_b, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(drop, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
    ])

    assert basenames_of(spk(basename=r'.*keep_.\.bsp')) == sorted([keep_a, keep_b])


def test_a_release_date_is_an_upper_limit(spk_catalog):
    """A single release date selects the kernels released on or before it.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert basenames_of(spk(release_date='2011-06-01')) == sorted([names[0], names[1]])


def test_a_release_date_range_selects_between_its_limits(spk_catalog):
    """A pair of release dates selects the kernels released within them.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    selected = basenames_of(spk(release_date=['2010-06-01', '2012-06-01']))
    assert selected == sorted([names[1], names[2]])


@pytest.mark.parametrize('version, expected_index', [(1, 0), (2, 1), (3, 2)])
def test_a_version_selects_the_matching_file(unique_name, version, expected_index):
    """A version constraint selects the file carrying that version.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        version (int): The version to request.
        expected_index (int): Index into the catalog of the file that must be selected.
    """

    names = [unique_name(f'v{n}.bsp') for n in (1, 2, 3)]
    spk = _spicefunc('spk', 'Test SPK', known=[
        KTuple(name, '2000-01-01', '2001-01-01', {499}, '2010-01-01') for name in names
    ])
    for name, number in zip(names, (1, 2, 3)):
        KernelFile(name).version = number

    assert basenames_of(spk(version=version)) == [names[expected_index]]


def test_a_version_range_selects_its_span(unique_name):
    """A two-element list of versions is an inclusive range.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    names = [unique_name(f'v{n}.bsp') for n in (1, 2, 3)]
    spk = _spicefunc('spk', 'Test SPK', known=[
        KTuple(name, '2000-01-01', '2001-01-01', {499}, '2010-01-01') for name in names
    ])
    for name, number in zip(names, (1, 2, 3)):
        KernelFile(name).version = number

    assert basenames_of(spk(version=[2, 3])) == sorted(names[1:])


##########################################################################################
# Exclusion
##########################################################################################

def test_exclude_keeps_only_the_highest_precedence_file(unique_name):
    """With exclude=True, only the last file in precedence order survives.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    names = [unique_name(f'v{n}.bsp') for n in (1, 2, 3)]
    spk = _spicefunc('spk', 'Test SPK', exclude=True, known=[
        KTuple(name, '2000-01-01', '2001-01-01', {499}, '2010-01-01') for name in names
    ])

    assert basenames_of(spk()) == [names[-1]]


def test_without_exclude_every_candidate_survives(unique_name):
    """The same catalog without exclude=True keeps all three files.

    This is the control for the test above: it shows that the single result there comes
    from the exclusion rule and not from the catalog.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    names = [unique_name(f'v{n}.bsp') for n in (1, 2, 3)]
    spk = _spicefunc('spk', 'Test SPK', known=[
        KTuple(name, '2000-01-01', '2001-01-01', {499}, '2010-01-01') for name in names
    ])

    assert basenames_of(spk()) == sorted(names)


##########################################################################################
# The returned Kernel
##########################################################################################

def test_unselected_files_are_recorded_as_exclusions(spk_catalog):
    """A catalogued file that was filtered out is excluded from the result.

    The exclusions are what let furnish() unload a competing kernel that is already
    loaded, so a file being merely absent from the result is not enough.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    result = spk(ids=599)

    assert basenames_of(result) == [names[2]]
    assert set(result.exclusions) >= {names[0], names[1]}


def test_a_required_kernel_of_another_ktype_becomes_a_corequisite(unique_name):
    """Requiring an LSK from an SPK makes it a corequisite, not a prerequisite.

    Precedence only orders kernels of the same type, so a requirement across types has
    no precedence relationship to express and is recorded separately.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    lsk_name = unique_name('leap.tls')
    spk_name = unique_name('mars.bsp')
    KernelFile.set_info(KTuple(lsk_name, None, None, None, '2010-01-01'))
    lsk = KernelFile(lsk_name)

    spk = _spicefunc('spk', 'Test SPK', require=(lsk,), known=[
        KTuple(spk_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
    ])
    result = spk()

    assert result.corequisites == {lsk}
    assert result.prerequisites == set()


def test_a_required_kernel_of_the_same_ktype_becomes_a_prerequisite(unique_name):
    """Requiring one SPK from another makes it a prerequisite, furnished below it.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    base_name = unique_name('base.bsp')
    top_name = unique_name('top.bsp')
    KernelFile.set_info(KTuple(base_name, '2000-01-01', '2001-01-01', {499},
                               '2010-01-01'))
    base = KernelFile(base_name)

    spk = _spicefunc('spk', 'Test SPK', require=(base,), known=[
        KTuple(top_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
    ])

    assert spk().prerequisites == {base}


##########################################################################################
# Ordering
##########################################################################################

def test_results_are_ordered_by_increasing_precedence(spk_catalog):
    """The basenames come back in load order, lowest precedence first.

    Order is what decides which kernel wins where two cover the same body and time, so
    it is part of the contract rather than an incidental detail.

    Parameters:
        spk_catalog ((function, list[str])): Fixture supplying the function and names.
    """

    (spk, names) = spk_catalog
    assert spk().basenames == names


def test_a_version_sort_orders_by_version_not_alphabetically(unique_name):
    """With sort="version", version 10 follows version 9 rather than preceding it.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
    """

    names = [unique_name(f'v{n}.bsp') for n in (2, 9, 10)]
    spk = _spicefunc('spk', 'Test SPK', sort='version', known=[
        KTuple(name, '2000-01-01', '2001-01-01', {499}, '2010-01-01') for name in names
    ])
    for name, number in zip(names, (2, 9, 10)):
        KernelFile(name).version = number

    assert spk().basenames == names
    assert sorted(names) != names, 'the alphabetical order must differ, or this proves '\
                                   'nothing'

##########################################################################################
