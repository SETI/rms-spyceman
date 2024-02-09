##########################################################################################
# spyceman/_utils.py
##########################################################################################
"""Utilities."""

import julian
import numbers
import re

from spyceman._cspyce import CSPYCE
from spyceman._ktypes import _EXTENSIONS

##########################################################################################
# Basename recognition
##########################################################################################

_EXT_REGEX = '(' + '|'.join(ext[1:] for ext in _EXTENSIONS) + ')'
_BASENAME_REGEX = re.compile(r'[\w.-]+\.' + _EXT_REGEX + '$', re.I)

def is_basename(basename):
    """True if this string appears to be a valid kernel file basename."""

    return (isinstance(basename, str)
            and bool(_BASENAME_REGEX.match(basename)))

def basename_ext(basename):
    """The extension of this basename or regular expression."""

    if isinstance(basename, re.Pattern):
        basename = basename.pattern

    ext = basename.rpartition('.')[-1]
    return '.' + ext

def basename_ktype(basename):
    """The ktype of this basename or regular expression; an empty string if unknown."""

    ext = basename_ext(basename).lower()
    return _EXTENSIONS.get(ext, '')

##########################################################################################
# Validation tools
##########################################################################################

def validate_release_date(date):
    """Format a given release date as "YYYY-MM-DD". None returns ""."""

    if date:
        (day, _) = julian.day_sec_from_string(date)
        return julian.format_day(day)

    return ''


def validate_version(version, sets_ok=True):
    """Validate a version or set of versions.

    A valid version must be a string, int, or tuple of ints. Multiple versions can be
    included in a set. None returns "". A string containing integers separated by periods
    is converted to a tuple of ints.
    """

    # An isolated None becomes "" because a version cannot be None
    if version is None:
        return ''

    # Convert int to tuple
    if isinstance(version, numbers.Integral):
        version = (version,)

    # Check tuple
    if isinstance(version, tuple):
        if len(version) == 0:
            raise ValueError('version tuple is empty')

        if not all((isinstance(i, numbers.Integral) for i in version)):
            raise ValueError('version as a tuple must contain integers: '
                             + repr(version))
        if not all(i >= 0 for i in version):
            raise ValueError('version cannot be negative: '
                             + repr(version if len(version) > 1 else version[0]))

        # Convert a single-element tuple back to int
        if len(version) == 1:
            return int(version[0])

        return tuple(int(i) for i in version)

    # Check string
    if isinstance(version, str):

        # Convert a dot-separated string of ints to a tuple
        parts = version.split('.')
        try:
            test = [int(p) for p in parts]
        except ValueError:
            pass
        else:
            return validate_version(tuple(test))

        return version

    # A set is the only remaining valid type
    if not isinstance(version, set) or not sets_ok:
        raise ValueError('invalid version, must be string, int, or tuple of ints: '
                         + repr(version))

    validated = set()
    for v in version:
        validated.add(validate_version(v, sets_ok=False))

    validated -= {''}   # None inside a set is meaningless
    return validated


def _naif_id(naif_id):
    """Convert name to int if it is a body name or frame name."""

    if isinstance(naif_id, numbers.Integral):
        return int(naif_id)

    if not isinstance(naif_id, str):
        raise ValueError('invalid NAIF ID type: ' + repr(naif_id))

    naif_name = naif_id

    # See if it is a body name
    naif_id, found = CSPYCE.bodn2c(naif_name)
    if found:
        return naif_id

    # See if it is a frame name
    naif_id, found = CSPYCE.namfrm(naif_name)
    if found:
        return naif_id

    raise KeyError(f'body/frame name "{naif_name}" not found in kernel pool')


def validate_naif_ids(ids):
    """Validate a NAIF ID/name or set/list/tuple of NAIF IDs/names.

    The validated values are returned as a set of ints. An input of None returns an empty
    set.
    """

    if ids is None:
        return set()

    if not isinstance(ids, (set, list, tuple)):
        ids = {ids}

    return {_naif_id(i) for i in ids}   # convert to ints


def naif_ids_with_aliases(ids):
    """Expand a set of NAIF IDs to include all aliases."""

    if ids is None:
        return set()

    if not isinstance(ids, (set, list, tuple)):
        ids = {ids}

    # Augment set with all body and frame aliases
    all_ids = ids.copy()
    for naif_id in ids:
        alias_ids = CSPYCE.get_body_aliases(naif_id)[0]
        all_ids |= set(alias_ids)

        alias_ids = CSPYCE.get_frame_aliases(naif_id)[0]
        all_ids |= set(alias_ids)

    return all_ids


def naif_ids_wo_aliases(ids):
    """The given NAIF ID or set of IDs, with any aliases replaced by their primary ID."""

    if ids is None:
        return set()

    if not isinstance(ids, (set, list, tuple)):
        ids = {ids}

    primary_ids = set()
    for naif_id in ids:
        alias_ids = CSPYCE.get_body_aliases(naif_id)[0]
        if alias_ids:
            primary_ids.add(alias_ids[0])

        alias_ids = CSPYCE.get_frame_aliases(naif_id)[0]
        if alias_ids:
            primary_ids.add(alias_ids[0])

    return primary_ids


def validate_time(time):
    """The time converted to a number of seconds TDB."""

    if isinstance(time, str):
        day, sec = julian.day_sec_from_string(time)
        tai = julian.tai_from_day_sec(day, sec)
        return julian.tdb_from_tai(tai)

    if isinstance(time, numbers.Real):
        return float(time)

    raise ValueError('invalid type for time: ' + repr(time))

##########################################################################################
# Support tools for function inputs
##########################################################################################

def _input_set(value, default=set()):
    """Convert an input value to a set of values; return default if input is None."""

    if not value and value != 0:    # None, empty set, list or tuple, but not zero
        value = default
        if not value and value != 0:
            return set()

    if isinstance(value, (list, set, tuple)):
        return set(value)

    return {value}


def _input_list(value):
    """Convert an input value to a list of values if it is not currently a list."""

    if not value and value != 0:    # None, empty set, list or tuple, but not zero
        return []

    if isinstance(value, (list, set, tuple)):
        return list(value)

    return [value]


def _test_version(input_version, kfile):
    """Compare an input version or a set or range of versions to a KernelFile's
    version(s).
    """

    # Check a list, which indicates an input range
    if isinstance(input_version, list):
        if len(input_version) != 2:
            raise ValueError('a range must be a list of two versions: '
                             + repr(input_version))

        limits = []
        for v in input_version:
            v = None if v == '' else v                          # empty string to None
            v = (v,) if isinstance(v, numbers.Integral) else v  # int to (int,)
            limits.append(v)

        if all(l is None for l in limits):                      # not a constraint
            return True

        if not any(l is None for l in limits):
            try:
                if limits[0] > limits[1]:
                    raise ValueError('first value in range must be <= second: '
                                     + repr(input_version))
            except TypeError:
                raise ValueError('a range must contain two like values: '
                                 + repr(input_version))

        for v in kfile.version_as_set:
            v = (v,) if isinstance(v, numbers.Integral) else v  # int to (int,)

            tests = []
            try:
                tests.append(v < limits[0])     # True means outside
            except TypeError:
                pass
            try:
                tests.append(v > limits[1])     # True means outside
            except TypeError:
                pass

            if tests and not any(tests):
                return True

        return False

    # Otherwise, compare sets for overlap
    else:
        if not isinstance(input_version, set):
            input_version = {input_version}

        return bool(input_version & kfile.version_as_set)

##########################################################################################
# Support tools for spicefunc inputs
##########################################################################################

_BASENAME_PATTERN = re.compile(r'[\w.-]+$')

def _intersect_basenames(basenames, choices, flags=re.I):
    """The intersection of two sets of basenames. Either set can contain one or more
    regular expressions.
    """

    # Check for empty input
    if not basenames:
        return set()

    # Convert each input to a set
    basenames = {basenames} if isinstance(basenames, str) else set(basenames)
    choices   = {choices}   if isinstance(choices,   str) else set(choices)

    # Augment the set of basenames with known files matching a regular expression
    patterns = {b for b in basenames if _BASENAME_PATTERN.match(b) is None}
    basenames -= patterns
    for pattern in patterns:
        more = KernelFile.find_all(pattern, exists=False, flags=flags)
        basenames |= set(more)

    # Augment the set of choices with known files matching a regular expression
    patterns = {b for b in choices if _BASENAME_PATTERN.match(b) is None}
    choices -= patterns
    for pattern in patterns:
        more = KernelFile.find_all(pattern, exists=False, flags=flags)
        choices |= set(more)

    # Return the intersection
    return basenames & choices

##########################################################################################

