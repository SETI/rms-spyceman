##########################################################################################
# tests/test_furnish.py: Behavioral tests of furnishing and unloading
##########################################################################################
"""Tests of what actually gets loaded into SPICE, in what order, and what gets unloaded.

These run with the Kernel layer in debug mode, so furnish() and unload() record what they
would have done instead of calling SPICE, and downloads are switched off. That makes the
tests hermetic and lets them assert on the load order, which is the part that matters:
SPICE resolves a body from the most recently furnished kernel that covers it, so a kernel
loaded in the wrong position produces wrong geometry rather than an error.

Every assertion here is on the record of what was furnished. A test that only checked
that furnish() returned without raising would have passed throughout the period when
Recipe.furnish() was silently dropping the leapseconds kernel.
"""

import pytest

from spyceman import Kernel, KernelFile, KernelStack, KTuple


@pytest.fixture
def mars_spks(unique_name, kernel_dir):
    """Two consecutive Mars SPKs, written to disk and catalogued.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.

    Returns:
        list[str]: The two basenames, in increasing order of precedence.
    """

    names = [unique_name('2000.bsp'), unique_name('2001.bsp')]
    kernel_dir(*names)
    KernelFile.set_info([
        KTuple(names[0], '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(names[1], '2001-01-01', '2002-01-01', {499}, '2011-01-01'),
    ])
    return names


##########################################################################################
# Furnishing one kernel
##########################################################################################

def test_furnishing_a_kernel_records_it(mars_spks, furnished):
    """A furnished kernel appears in the record for its own ktype.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(mars_spks[0]).furnish()

    assert furnished('SPK') == [mars_spks[0]]


def test_furnishing_twice_does_not_duplicate_the_entry(mars_spks, furnished):
    """Furnishing an already-furnished kernel leaves it furnished exactly once.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    kfile = KernelFile(mars_spks[0])
    kfile.furnish()
    kfile.furnish()

    assert furnished('SPK') == [mars_spks[0]]


def test_unloading_removes_the_kernel(mars_spks, furnished):
    """An unloaded kernel is no longer recorded as furnished.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    kfile = KernelFile(mars_spks[0])
    kfile.furnish()
    kfile.unload()

    assert furnished('SPK') == []


def test_unloading_one_kernel_leaves_the_other(mars_spks, furnished):
    """Unloading is specific to the kernel asked for.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(mars_spks[0]).furnish()
    KernelFile(mars_spks[1]).furnish()
    KernelFile(mars_spks[0]).unload()

    assert furnished('SPK') == [mars_spks[1]]


##########################################################################################
# The empty-ID case that §6.20 got wrong
##########################################################################################

@pytest.fixture
def universal_lsk(unique_name, kernel_dir):
    """A leapseconds kernel that constrains neither time nor NAIF ID.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.

    Returns:
        str: The basename of the kernel.
    """

    name = unique_name('leap.tls')
    kernel_dir(name)
    KernelFile.set_info(KTuple(name, None, None, None, '2010-01-01'))

    kfile = KernelFile(name)
    assert kfile.naif_ids == set(), 'this kernel is meant to apply to every ID'
    assert kfile.time == (None, None), 'and to every time'
    return name


def test_a_kernel_for_all_ids_is_furnished_by_an_unconstrained_request(universal_lsk,
                                                                      furnished):
    """A kernel applying to every NAIF ID is furnished when no IDs are requested.

    This is the §6.20 case exactly. Both sides of the comparison are empty: the kernel
    constrains no IDs and the request names none. Reading that as "no IDs in common"
    rather than "no constraint on either side" left every leapseconds kernel unfurnished,
    and nothing raised -- furnish() completed and simply omitted the file.

    Parameters:
        universal_lsk (str): Fixture supplying an unconstrained LSK basename.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(universal_lsk).furnish()

    assert furnished('LSK') == [universal_lsk]


def test_a_kernel_for_all_ids_is_furnished_when_specific_ids_are_requested(universal_lsk,
                                                                          furnished):
    """A kernel applying to every NAIF ID is furnished for a request naming one.

    Here only one side is empty, which id_overlap() resolves by returning the requested
    IDs. It is the companion to the test above rather than a repeat of it: that one has
    both sides empty, and the two are handled by different code.

    Parameters:
        universal_lsk (str): Fixture supplying an unconstrained LSK basename.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(universal_lsk).furnish(ids=499)

    assert furnished('LSK') == [universal_lsk]


def test_a_kernel_for_all_times_is_furnished_for_a_bounded_query(universal_lsk,
                                                                 furnished):
    """A kernel with no time limits is furnished for a query naming a time range.

    Unconstrained coverage is the same trap as unconstrained IDs, one axis over.

    Parameters:
        universal_lsk (str): Fixture supplying an unconstrained LSK basename.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(universal_lsk).furnish(tmin='2005-01-01', tmax='2006-01-01')

    assert furnished('LSK') == [universal_lsk]


def test_a_kernel_outside_the_requested_range_is_not_furnished(mars_spks, furnished):
    """A constrained furnish leaves out the kernels that do not overlap.

    This is the counterpart to the two tests above: the unconstrained cases must be
    furnished, but a kernel that genuinely does not apply must not be.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelFile(mars_spks[0]).furnish(tmin='2001-06-01', tmax='2001-07-01')

    assert furnished('SPK') == []


def test_a_kernel_for_another_body_is_not_furnished(unique_name, kernel_dir, furnished):
    """A kernel covering only other NAIF IDs is left out.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.
        furnished (function): Fixture reporting what has been furnished.
    """

    name = unique_name('jupiter.bsp')
    kernel_dir(name)
    KernelFile.set_info(KTuple(name, '2000-01-01', '2001-01-01', {599}, '2010-01-01'))

    KernelFile(name).furnish(ids=499)

    assert furnished('SPK') == []


##########################################################################################
# Load order
##########################################################################################

def test_kernels_are_furnished_in_precedence_order(mars_spks, furnished):
    """A KernelStack furnishes its members lowest precedence first.

    SPICE resolves a body from the most recently furnished kernel that covers it, so the
    last name in this list is the one that wins.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelStack([KernelFile(name) for name in mars_spks]).furnish()

    assert furnished('SPK') == mars_spks


def test_a_prerequisite_is_furnished_below_the_kernel_that_requires_it(unique_name,
                                                                      kernel_dir,
                                                                      furnished):
    """A prerequisite is furnished first, so the requiring kernel takes precedence.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.
        furnished (function): Fixture reporting what has been furnished.
    """

    base_name = unique_name('base.bsp')
    top_name = unique_name('top.bsp')
    kernel_dir(base_name, top_name)
    KernelFile.set_info([
        KTuple(base_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(top_name, '2000-01-01', '2001-01-01', {499}, '2011-01-01'),
    ])

    top = KernelFile(top_name)
    top.require(KernelFile(base_name))
    top.furnish()

    assert furnished('SPK') == [base_name, top_name]


def test_a_corequisite_of_another_ktype_is_furnished_too(unique_name, kernel_dir,
                                                         furnished):
    """Furnishing an SPK that requires an LSK furnishes both.

    The two are recorded under their own ktypes, so this checks that the requirement is
    honored across types rather than quietly dropped.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.
        furnished (function): Fixture reporting what has been furnished.
    """

    lsk_name = unique_name('leap.tls')
    spk_name = unique_name('mars.bsp')
    kernel_dir(lsk_name, spk_name)
    KernelFile.set_info([
        KTuple(lsk_name, None, None, None, '2010-01-01'),
        KTuple(spk_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
    ])

    spk = KernelFile(spk_name)
    spk.require(KernelFile(lsk_name))
    spk.furnish()

    assert furnished('LSK') == [lsk_name]
    assert furnished('SPK') == [spk_name]


##########################################################################################
# used()
##########################################################################################

def test_used_reports_the_winning_kernel_for_a_time(mars_spks, furnished):
    """used() names the kernel that would supply a given time, not every candidate.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    stack = KernelStack([KernelFile(name) for name in mars_spks])

    assert stack.used(tmin='2000-06-01', tmax='2000-07-01') == [mars_spks[0]]
    assert stack.used(tmin='2001-06-01', tmax='2001-07-01') == [mars_spks[1]]


def test_used_does_not_furnish_anything(mars_spks, furnished):
    """Asking what would be used has no effect on what is furnished.

    Parameters:
        mars_spks (list[str]): Fixture supplying two catalogued SPK basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    KernelStack([KernelFile(name) for name in mars_spks]).used()

    assert furnished() == []


##########################################################################################
# Exclusions
##########################################################################################

def test_an_excluded_kernel_is_unloaded_when_its_rival_is_furnished(unique_name,
                                                                   kernel_dir,
                                                                   furnished):
    """Furnishing a kernel unloads a kernel it excludes.

    Two kernels covering the same body and time would otherwise both be loaded, and which
    one SPICE used would depend on the order they happened to arrive in.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.
        furnished (function): Fixture reporting what has been furnished.
    """

    old_name = unique_name('old.bsp')
    new_name = unique_name('new.bsp')
    kernel_dir(old_name, new_name)
    KernelFile.set_info([
        KTuple(old_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(new_name, '2000-01-01', '2001-01-01', {499}, '2011-01-01'),
    ])

    KernelFile(old_name).furnish()
    assert furnished('SPK') == [old_name]

    new_kernel = KernelFile(new_name)
    new_kernel.exclude(old_name)
    new_kernel.furnish()

    assert furnished('SPK') == [new_name]


@pytest.fixture
def rival_spks(unique_name, kernel_dir):
    """Two catalogued SPKs covering different years, 2000 and 2002.

    Parameters:
        unique_name (function): Fixture supplying unique basenames.
        kernel_dir (function): Fixture that writes and registers stub kernel files.

    Returns:
        (str, str): The earlier basename, covering 2000, and the later one, covering
            2002.
    """

    early_name = unique_name('early.bsp')
    late_name = unique_name('late.bsp')
    kernel_dir(early_name, late_name)
    KernelFile.set_info([
        KTuple(early_name, '2000-01-01', '2001-01-01', {499}, '2010-01-01'),
        KTuple(late_name, '2002-01-01', '2003-01-01', {499}, '2011-01-01'),
    ])
    return (early_name, late_name)


def test_an_exclusion_applies_across_the_whole_range_when_none_is_given(rival_spks,
                                                                       furnished):
    """An unconstrained furnish unloads an excluded kernel whatever it covers.

    The overlap that decides this is between the excluded kernel and the range asked
    for, not between the two kernels. With no range given, the request covers everything,
    so the exclusion applies everywhere.

    Parameters:
        rival_spks ((str, str)): Fixture supplying the earlier and later basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    (early_name, late_name) = rival_spks
    KernelFile(early_name).furnish()

    late = KernelFile(late_name)
    late.exclude(early_name)
    late.furnish()

    assert furnished('SPK') == [late_name]


def test_an_exclusion_is_limited_to_the_requested_range(rival_spks, furnished):
    """Furnishing for a range the excluded kernel does not cover leaves it loaded.

    This is the same pair as the test above, differing only in that the furnish names a
    range. It is what shows the exclusion to be scoped rather than absolute.

    Parameters:
        rival_spks ((str, str)): Fixture supplying the earlier and later basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    (early_name, late_name) = rival_spks
    KernelFile(early_name).furnish()

    late = KernelFile(late_name)
    late.exclude(early_name)
    late.furnish(tmin='2002-01-01', tmax='2003-01-01')

    assert furnished('SPK') == [early_name, late_name]


def test_an_exclusion_belongs_to_the_kernel_object_not_the_basename(rival_spks,
                                                                   furnished):
    """Excluding through one KernelFile does not affect another for the same file.

    Exclusions describe a particular selection rather than the file itself, which is how
    a generated selection function attaches them to the Kernel it returns. A test that
    set an exclusion on a throwaway object and furnished a fresh one would silently
    exercise nothing, so this pins the behavior down.

    Parameters:
        rival_spks ((str, str)): Fixture supplying the earlier and later basenames.
        furnished (function): Fixture reporting what has been furnished.
    """

    (early_name, late_name) = rival_spks
    KernelFile(late_name).exclude(early_name)       # set on an object then discarded

    assert KernelFile(late_name).exclusions == set()

    KernelFile(early_name).furnish()
    KernelFile(late_name).furnish()

    assert furnished('SPK') == [early_name, late_name]


##########################################################################################
# The sandbox itself
##########################################################################################

def test_debug_mode_is_active_so_nothing_reaches_spice(spice_sandbox):
    """The sandbox fixture leaves the Kernel layer in debug mode with downloads off.

    If this ever stops holding, the tests in this file would start loading kernels into
    the real SPICE toolkit and reaching for the network.

    Parameters:
        spice_sandbox (dict): Fixture providing the furnished-basename record.
    """

    assert Kernel.debug() is True
    assert Kernel.download() is False


def test_the_furnish_record_starts_empty(furnished):
    """Each test begins with nothing furnished, whatever ran before it.

    Parameters:
        furnished (function): Fixture reporting what has been furnished.
    """

    assert furnished() == []

##########################################################################################
