##########################################################################################
# spyceman/cspyce.py
##########################################################################################
"""Defines CSPYCE as either the cspyce or the spicepy module.

To use:
    from spyceman.cspyce import CSPYCE
Elsewhere, use "CSPYCE" where you would normally type "cspyce" or "spicepy".

If the environment variable "SPICEMODULE" is defined, this is interpreted as the name of
the module. Otherwise, CSPYCE is defined as the cspyce module if it is installed, and
otherwise the spicepy module.

Note that the spicepy module does not support aliases or array operations.

This module also defines two additional variables that are available for import:
    CSPYCE_NAME     the name of the module, either "cspyce" or "spicepy".
    CSPYCE_ALIASES  True if alias support is available; False otherwise.

CSPYCE.get_body_aliases() and CSPYCE.get_frame_aliases() are memoized here, because
resolving the NAIF IDs of a large kernel catalog calls them tens of thousands of times
with only a few dozen distinct arguments. Every function that can change SPICE's body or
frame tables is wrapped to discard the cache, so the memoization is invisible; a caller
that alters those tables without going through CSPYCE can call clear_alias_caches().
"""

import functools
import importlib
import numbers
import os

##########################################################################################
# Define CSPYCE and CSPYCE_NAME
##########################################################################################

CSPYCE = None
CSPYCE_NAME = ''

if 'SPICEMODULE' in os.environ:
    CSPYCE_NAME = os.environ['SPICEMODULE']
    CSPYCE = importlib.import_module(CSPYCE_NAME)

else:
    for name in ('cspyce', 'spicepy'):
        try:
            CSPYCE_NAME = name
            CSPYCE = importlib.import_module(name)
            break
        except ModuleNotFoundError:
            pass

if CSPYCE is None:
    raise ImportError('unable to import cspyce or spicepy')

##########################################################################################
# Either define cspyce aliases or fake them for spicepy
##########################################################################################

def _fake_get_body_aliases(item):
    """Stand-in for cspyce.get_body_aliases() when the module is spicepy.

    spicepy has no alias support, so a body has at most one code and one name. This
    returns those as one-element lists, mimicking the cspyce signature.

    Parameters:
        item (int, str): A NAIF body ID or body name.

    Returns:
        (list[int], list[str]): The body's IDs and names. Both lists are empty if the
            body is not recognized; otherwise each holds exactly one element.
    """

    if isinstance(item, str):
        code, found = CSPYCE.bodn2c(item)
    else:
        code, found = (item, True)
    if found:
        name, found = CSPYCE.bodc2n(code)
    if not found:
        return ([], [])
    return ([code], [name])

def _fake_get_frame_aliases(item):
    """Stand-in for cspyce.get_frame_aliases() when the module is spicepy.

    spicepy has no alias support, so a frame has at most one code and one name. This
    returns those as one-element lists, mimicking the cspyce signature.

    Parameters:
        item (int, str): A NAIF frame ID or frame name.

    Returns:
        (list[int], list[str]): The frame's IDs and names. Both lists are empty if the
            frame is not recognized; otherwise each holds exactly one element.
    """

    if isinstance(item, str):
        code, found = CSPYCE.namfrm(item)
    else:
        code, found = (item, True)
    if found:
        name, found = CSPYCE.frmnam(code)
    if not found:
        return ([], [])
    return ([code], [name])

def _fake_define_body_aliases(*items):
    """Stand-in for cspyce.define_body_aliases() when the module is spicepy.

    spicepy has no alias support, so the best that can be done is to associate the first
    given ID with the first given name via boddef(). An association that already exists
    with the same name is left alone.

    Parameters:
        *items (int, str): One or more NAIF body IDs and body names in any order. The
            first ID and the first name are the ones used; any others are ignored.

    Raises:
        IndexError: If no integer ID or no name is among the given items.
    """

    code = [i for i in items if isinstance(i, numbers.Integral)][0]
    name = [i for i in items if isinstance(i, str)][0]
    test_name, found = CSPYCE.bodc2n(code)
    if found:
        if test_name.upper() != name.upper():   # don't repeat existing boddef's
            CSPYCE.boddef(name, code)
    else:
        CSPYCE.boddef(name, code)

CSPYCE_ALIASES = (CSPYCE_NAME == 'cspyce')

if CSPYCE_ALIASES:
    import cspyce.aliases

    # Disable Python errors for a few core functions
    CSPYCE.bodn2c = cspyce.bodn2c.flag
    CSPYCE.bodc2n = cspyce.bodc2n.flag
    CSPYCE.cidfrm = cspyce.cidfrm.flag
    CSPYCE.namfrm = cspyce.namfrm.flag
    CSPYCE.frmnam = cspyce.frmnam.flag

else:
    CSPYCE.use_aliases = lambda *args: None
    CSPYCE.use_noaliases = lambda *args: None
    CSPYCE.get_body_aliases = _fake_get_body_aliases
    CSPYCE.get_frame_aliases = _fake_get_frame_aliases
    CSPYCE.define_body_aliases = _fake_define_body_aliases
    CSPYCE.define_frame_aliases = lambda *args: None

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

for _name in _MUTATORS:
    if hasattr(CSPYCE, _name):
        setattr(CSPYCE, _name, _clear_caches_after(getattr(CSPYCE, _name)))

del _name

##########################################################################################
