##########################################################################################
# tests/test_cspyce.py: Tests of the CSPYCE indirection and its memoized alias lookups
##########################################################################################
"""Tests of spyceman._cspyce.

The memoized alias lookups are the subject of most of these. A cache that returns a stale
answer would corrupt every kernel's NAIF ID set silently, so the invalidation is tested on
each kind of mutation rather than assumed.
"""

import pytest

import cspyce
import cspyce.alias_support

from spyceman._cspyce import (CSPYCE, _BODY_ALIAS_CACHE, _FRAME_ALIAS_CACHE, _MUTATORS,
                              clear_alias_caches)

# IDs that no SPICE kernel defines. Defining a body or frame alias changes SPICE state for
# the rest of the process and cannot be undone, so the test that defines one uses an ID of
# its own: sharing an ID with the test that expects a lookup to miss would make the two
# order-dependent, and pytest-xdist gives no control over which lands in which worker.
UNDEFINED_ID = 91919191                 # only ever looked up, never defined
DEFINABLE_BODY_ID = 91919192            # defined by one test, used by no other
DEFINABLE_FRAME_IDS = (-919193, -919194)


@pytest.fixture
def clean_caches():
    """Empty both alias caches before the test and again afterward.

    Returns:
        None: The fixture exists for its side effects.
    """

    clear_alias_caches()
    yield
    clear_alias_caches()


def test_cspyce_is_the_cspyce_module():
    """The indirection resolves to cspyce itself."""

    assert CSPYCE is cspyce


def test_alias_support_is_available():
    """Importing the module makes cspyce's alias functions available."""

    assert callable(CSPYCE.define_body_aliases)


@pytest.mark.parametrize('name', _MUTATORS)
def test_every_mutator_is_wrapped(name):
    """Each function that can change the body or frame tables is wrapped to clear them.

    An unwrapped mutator would let the caches go stale silently, so every name is checked
    rather than only the four whose clearing is exercised below. A bare cspyce function
    carries no __wrapped__ attribute; one of ours carries the function it replaced.

    Parameters:
        name (str): The name of one mutating function.
    """

    assert hasattr(getattr(CSPYCE, name), '__wrapped__')


@pytest.mark.parametrize('item', [-82, 699, 601, 501, 399, 0, -31, 10016, 12345678,
                                  'SATURN', 'CASSINI', 'NOT_A_BODY_AT_ALL'])
def test_memoized_lookups_match_the_unwrapped_originals(item, clean_caches):
    """A memoized lookup returns what the underlying cspyce function returns.

    Parameters:
        item (int, str): The NAIF ID or name to look up.
        clean_caches (None): Fixture that empties the caches around the test.
    """

    assert CSPYCE.get_body_aliases(item) == cspyce.alias_support.get_body_aliases(item)
    assert CSPYCE.get_frame_aliases(item) == cspyce.alias_support.get_frame_aliases(item)


def test_repeated_lookups_are_cached(clean_caches):
    """A second lookup of the same item is answered from the cache.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    assert 699 not in _FRAME_ALIAS_CACHE
    first = CSPYCE.get_frame_aliases(699)
    assert 699 in _FRAME_ALIAS_CACHE
    assert CSPYCE.get_frame_aliases(699) == first


def test_a_missing_item_is_cached_too(clean_caches):
    """An item with no aliases is cached, since the miss is what costs the most.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    assert CSPYCE.get_body_aliases(UNDEFINED_ID) == ([], [])
    assert UNDEFINED_ID in _BODY_ALIAS_CACHE


def test_the_caller_cannot_modify_what_the_cache_holds(clean_caches):
    """Each call returns fresh lists, so mutating a result cannot corrupt the cache.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    first = CSPYCE.get_frame_aliases(699)
    assert first[0] == [10016]
    first[0].append(999999)
    first[1].append('BOGUS')

    second = CSPYCE.get_frame_aliases(699)
    assert second[0] == [10016]
    assert 'BOGUS' not in second[1]


def test_returned_values_are_lists(clean_caches):
    """The memoized functions return lists, as the cspyce originals do.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    (ids, names) = CSPYCE.get_frame_aliases(699)
    assert isinstance(ids, list)
    assert isinstance(names, list)


def test_define_body_aliases_invalidates_a_cached_miss(clean_caches):
    """Defining a body must not leave an earlier "no such body" answer in the cache.

    This is the failure the memoization most plausibly introduces: four modules in the
    package define aliases at import time, after other kernels have been catalogued.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    assert CSPYCE.get_body_aliases(DEFINABLE_BODY_ID) == ([], [])

    CSPYCE.define_body_aliases(DEFINABLE_BODY_ID, 'SPYCEMAN_TEST_BODY')

    assert not _BODY_ALIAS_CACHE
    assert CSPYCE.get_body_aliases(DEFINABLE_BODY_ID)[0] == [DEFINABLE_BODY_ID]


def test_define_frame_aliases_clears_the_caches(clean_caches):
    """Defining a frame drops the memoized lookups.

    The frame IDs are ones no kernel uses, so that this test cannot disturb the Voyager
    camera frames that spyceman.hosts.Voyager aliases at import time.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    CSPYCE.get_frame_aliases(699)
    assert _FRAME_ALIAS_CACHE

    CSPYCE.define_frame_aliases('SPYCEMAN_TEST_FRAME', *DEFINABLE_FRAME_IDS)

    assert not _FRAME_ALIAS_CACHE


def test_furnsh_clears_the_caches(tmp_path, clean_caches):
    """Furnishing a kernel drops the caches, because a kernel can define bodies or frames.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
        clean_caches (None): Fixture that empties the caches around the test.
    """

    path = tmp_path / 'test_naif.tls'
    path.write_text('\\begindata\nDELTET/DELTA_T_A = 32.184\n\\begintext\n')

    CSPYCE.get_body_aliases(699)
    assert _BODY_ALIAS_CACHE

    CSPYCE.furnsh(str(path))
    try:
        assert not _BODY_ALIAS_CACHE
    finally:
        CSPYCE.unload(str(path))


def test_unload_clears_the_caches(tmp_path, clean_caches):
    """Unloading a kernel drops the caches, because its definitions go away with it.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
        clean_caches (None): Fixture that empties the caches around the test.
    """

    path = tmp_path / 'test_naif.tls'
    path.write_text('\\begindata\nDELTET/DELTA_T_A = 32.184\n\\begintext\n')

    CSPYCE.furnsh(str(path))
    CSPYCE.get_body_aliases(699)
    assert _BODY_ALIAS_CACHE

    CSPYCE.unload(str(path))

    assert not _BODY_ALIAS_CACHE


def test_a_failed_mutator_still_clears_the_caches(clean_caches):
    """A mutator that raises may have changed the tables anyway, so it clears the caches.

    Parameters:
        clean_caches (None): Fixture that empties the caches around the test.
    """

    CSPYCE.get_body_aliases(699)
    assert _BODY_ALIAS_CACHE

    with pytest.raises(Exception):
        CSPYCE.furnsh('/no/such/directory/no_such_kernel.tls')

    assert not _BODY_ALIAS_CACHE


def test_clear_alias_caches_empties_both():
    """clear_alias_caches() drops every memoized entry from both caches."""

    CSPYCE.get_body_aliases(699)
    CSPYCE.get_frame_aliases(699)

    clear_alias_caches()

    assert not _BODY_ALIAS_CACHE
    assert not _FRAME_ALIAS_CACHE


def test_wrapped_functions_keep_their_identity():
    """The wrappers report the names of the functions they stand in for."""

    assert CSPYCE.get_body_aliases.__name__ == 'get_body_aliases'
    assert CSPYCE.get_frame_aliases.__name__ == 'get_frame_aliases'
    assert CSPYCE.furnsh.__name__ == 'furnsh'

##########################################################################################
