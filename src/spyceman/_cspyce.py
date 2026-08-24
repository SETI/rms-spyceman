##########################################################################################
# spyceman/_cspyce.py
##########################################################################################
"""Defines CSPYCE as the cspyce module, with its alias lookups memoized.

To use:
    from spyceman._cspyce import CSPYCE
Elsewhere, use "CSPYCE" where you would normally type "cspyce".

CSPYCE.get_body_aliases() and CSPYCE.get_frame_aliases() are memoized here, because
resolving the NAIF IDs of a large kernel catalog calls them tens of thousands of times
with only a few dozen distinct arguments. Every function that can change SPICE's body or
frame tables is wrapped to discard the cache, so the memoization is invisible; a caller
that alters those tables without going through CSPYCE can call clear_alias_caches().
"""

import functools

import cspyce
import cspyce.aliases

##########################################################################################
# Define CSPYCE
##########################################################################################

CSPYCE = cspyce

# Disable Python errors for a few core functions, so that an unrecognized body or frame
# reports "not found" rather than raising.
CSPYCE.bodn2c = cspyce.bodn2c.flag
CSPYCE.bodc2n = cspyce.bodc2n.flag
CSPYCE.cidfrm = cspyce.cidfrm.flag
CSPYCE.namfrm = cspyce.namfrm.flag
CSPYCE.frmnam = cspyce.frmnam.flag

##########################################################################################
# Memoize the alias lookups
##########################################################################################
#
# get_body_aliases() and get_frame_aliases() dominate the cost of importing a kernel
# catalog. Each catalogued kernel resolves its NAIF IDs through both of them, and an ID
# that is not a recognized body or frame makes SPICE signal an error, which costs about a
# millisecond. Since the same few dozen IDs recur across every kernel in a catalog, nearly
# all of that work is repeated: importing spyceman.hosts.Cassini spent about 140 seconds
# in cspyce.sigerr() alone.
#
# Both functions are pure functions of SPICE's current body and frame tables, so their
# results can be cached as long as the cache is dropped whenever those tables can change.
# _MUTATORS below names every such function; each is wrapped to clear the caches after it
# runs. Furnishing or unloading a kernel counts, because a frame kernel defines frames and
# a text kernel can assign NAIF_BODY_NAME and NAIF_BODY_CODE.

_BODY_ALIAS_CACHE = {}
_FRAME_ALIAS_CACHE = {}

# Every function through which the body or frame tables can change. Wrapping the pool
# functions as well as furnsh/unload means a caller who edits the kernel pool directly
# does not silently invalidate the cache.
_MUTATORS = ('define_body_aliases', 'define_frame_aliases', 'boddef', 'furnsh', 'unload',
             'kclear', 'clpool', 'ldpool', 'pdpool', 'pcpool', 'pipool')


def clear_alias_caches():
    """Discard the memoized results of get_body_aliases() and get_frame_aliases().

    This is called automatically whenever SPICE's body or frame tables can have changed,
    so it is needed only by a caller that reaches past CSPYCE to alter those tables.
    """

    _BODY_ALIAS_CACHE.clear()
    _FRAME_ALIAS_CACHE.clear()


def _memoize_alias_lookup(func, cache):
    """Wrap an alias lookup function so that repeated queries are answered from a cache.

    Parameters:
        func (function): The alias lookup function to wrap, called as func(item) and
            returning a (list[int], list[str]) pair.
        cache (dict): The dictionary in which to record results, keyed by item.

    Returns:
        function: A function with the same signature and return value as func.
    """

    def wrapper(item):
        """Return the aliases of one body or frame, consulting the cache first.

        Parameters:
            item (int, str): A NAIF ID or name.

        Returns:
            (list[int], list[str]): The IDs and names, as new lists on every call so that
                a caller cannot modify what the cache holds.
        """

        try:
            (ids, names) = cache[item]
        except KeyError:
            (ids, names) = func(item)
            cache[item] = (tuple(ids), tuple(names))
        except TypeError:                   # an unhashable item cannot be cached
            return func(item)

        return (list(ids), list(names))

    functools.update_wrapper(wrapper, func)
    return wrapper


def _clear_caches_after(func):
    """Wrap a function so that the alias caches are dropped once it has run.

    Parameters:
        func (function): The function to wrap, which can change SPICE's body or frame
            tables.

    Returns:
        function: A function with the same signature and return value as func.
    """

    def wrapper(*args, **kwargs):
        """Call the wrapped function, then discard the memoized alias lookups.

        The caches are cleared even if the call raises, because a call that fails partway
        may still have changed the tables.

        Parameters:
            *args: Passed through to the wrapped function.
            **kwargs: Passed through to the wrapped function.

        Returns:
            object: Whatever the wrapped function returns.
        """

        try:
            return func(*args, **kwargs)
        finally:
            clear_alias_caches()

    functools.update_wrapper(wrapper, func)
    return wrapper


CSPYCE.get_body_aliases = _memoize_alias_lookup(CSPYCE.get_body_aliases,
                                                _BODY_ALIAS_CACHE)
CSPYCE.get_frame_aliases = _memoize_alias_lookup(CSPYCE.get_frame_aliases,
                                                 _FRAME_ALIAS_CACHE)

# No hasattr() guard: a name that cspyce stops providing must fail here rather than
# leave that mutator unwrapped, because an unwrapped mutator makes the caches go stale
# silently and every NAIF ID resolved afterward is suspect.
for _name in _MUTATORS:
    setattr(CSPYCE, _name, _clear_caches_after(getattr(CSPYCE, _name)))

del _name

##########################################################################################
