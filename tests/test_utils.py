##########################################################################################
# tests/test_utils.py: Tests of the helper functions in spyceman._utils
##########################################################################################
"""Tests of the input-normalizing and version-comparing helpers.

These functions are pure, so they can be tested without any kernel files, any network
access, and any SPICE state.
"""

import pytest

from spyceman._utils import _input_list, _input_set, _test_version


class _FakeKernelFile:
    """Stand-in for a KernelFile that carries nothing but a version.

    Parameters:
        versions (set, list, tuple): The versions the file is to report.
        basename (str, optional): The name the file is to report. Defaults to "fake.bsp".
    """

    def __init__(self, versions, basename='fake.bsp'):
        self.version_as_set = set(versions)
        self.basename = basename


##########################################################################################
# _input_set
##########################################################################################

@pytest.mark.parametrize('value, expected', [
    (None,          set()),
    (set(),         set()),
    ([],            set()),
    ((),            set()),
    (0,             {0}),           # zero is a value, not an empty input
    (7,             {7}),
    ('abc',         {'abc'}),       # a string is one value, not a set of characters
    ([1, 2, 2],     {1, 2}),
    ({1, 2},        {1, 2}),
    ((1, 2),        {1, 2}),
])
def test_input_set(value, expected):
    """_input_set() converts scalars and collections alike to a set.

    Parameters:
        value (object): The value to convert.
        expected (set): The set it must produce.
    """

    assert _input_set(value) == expected


def test_input_set_uses_the_default_when_empty():
    """An empty input falls back to the default, and an empty default yields an empty
    set."""

    assert _input_set(None, default=5) == {5}
    assert _input_set(None, default=None) == set()
    assert _input_set(0, default=5) == {0}       # zero is not empty, so no fallback


def test_input_set_range_requires_a_list():
    """A two-element list expands to a range only when ranges is True; a tuple or set of
    two never does."""

    assert _input_set([2, 5], ranges=True) == {2, 3, 4, 5}
    assert _input_set([2, 5], ranges=False) == {2, 5}
    assert _input_set((2, 5), ranges=True) == {2, 5}
    assert _input_set({2, 5}, ranges=True) == {2, 5}


##########################################################################################
# _input_list
##########################################################################################

@pytest.mark.parametrize('value, expected', [
    (None,      []),
    ([],        []),
    (set(),     []),
    (0,         [0]),               # zero is a value, not an empty input
    ('abc',     ['abc']),
    ([1, 2],    [1, 2]),
    ((1, 2),    [1, 2]),
])
def test_input_list(value, expected):
    """_input_list() converts scalars and collections alike to a list.

    Parameters:
        value (object): The value to convert.
        expected (list): The list it must produce.
    """

    assert _input_list(value) == expected


##########################################################################################
# _test_version
##########################################################################################

@pytest.mark.parametrize('constraint, versions, expected', [
    ([1, 3],        [2],        True),      # inside the range
    ([1, 3],        [1],        True),      # lower limit is inclusive
    ([1, 3],        [3],        True),      # upper limit is inclusive
    ([1, 3],        [0],        False),     # below
    ([1, 3],        [4],        False),     # above
    ([None, 3],     [1],        True),      # unconstrained below
    ([None, 3],     [9],        False),
    ([1, None],     [9],        True),      # unconstrained above
    ([1, None],     [0],        False),
    (['', ''],      [5],        True),      # empty strings mean unconstrained
    ([1, 3],        [9, 2],     True),      # any one version inside suffices
])
def test_test_version_ranges(constraint, versions, expected):
    """A list constraint is an inclusive range, with None or "" leaving an end open.

    Parameters:
        constraint (list): The range to apply.
        versions (list): The versions the file reports.
        expected (bool): Whether the file is expected to satisfy the constraint.
    """

    assert _test_version(constraint, _FakeKernelFile(versions)) is expected


def test_test_version_incomparable_is_a_non_match_not_an_error():
    """A version that cannot be compared to the range is excluded rather than raising,
    and it does not disqualify the file's other versions."""

    assert _test_version([1, 3], _FakeKernelFile(['V2'])) is False
    assert _test_version([1, 3], _FakeKernelFile(['V2', 2])) is True


@pytest.mark.parametrize('constraint, versions, expected', [
    (2,             [1, 2],     True),      # a scalar is tested for membership
    (5,             [1, 2],     False),
    ({1, 5},        [5],        True),      # a set is tested for overlap
    ({7, 8},        [5],        False),
    ((1, 5),        [(1, 5)],   True),      # a tuple is one version, e.g. version 1.5
    ((1, 5),        [5],        False),     # ...so it does not mean the set {1, 5}
    ((1, 5),        [3],        False),     # ...nor the range 1 to 5
])
def test_test_version_sets(constraint, versions, expected):
    """A non-list constraint is compared for set overlap, never as a range.

    Parameters:
        constraint (object): The constraint to apply.
        versions (list): The versions the file reports.
        expected (bool): Whether the file is expected to satisfy the constraint.
    """

    assert _test_version(constraint, _FakeKernelFile(versions)) is expected


@pytest.mark.parametrize('constraint', [[1, 2, 3], [1], [3, 1], [1, 'a']])
def test_test_version_rejects_a_malformed_range(constraint):
    """A range must be exactly two comparable values in ascending order.

    Parameters:
        constraint (list): A malformed range.
    """

    with pytest.raises(ValueError):
        _test_version(constraint, _FakeKernelFile([2]))

##########################################################################################
