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
    """True if this string appears to be a valid kernel file basename.

    A valid basename consists of word characters, periods, and dashes, and ends with one
    of the recognized SPICE kernel file extensions.

    Parameters:
        basename (str): The string to test. A non-string input returns False rather than
            raising.

    Returns:
        bool: True if the string could be a SPICE kernel file basename.
    """

    return isinstance(basename, str) and bool(_BASENAME_REGEX.match(basename))


def basename_ext(basename):
    """The extension of this basename or regular expression.

    Parameters:
        basename (str, re.Pattern): A kernel file basename, or a regular expression whose
            trailing characters spell out the extension.

    Returns:
        str: The extension, including the leading period. If the input contains no
            period, the entire input is returned with a period prepended.
    """

    if isinstance(basename, re.Pattern):
        basename = basename.pattern

    ext = basename.rpartition('.')[-1]
    return '.' + ext


def basename_ktype(basename):
    """The ktype of this basename or regular expression; an empty string if unknown.

    Parameters:
        basename (str, re.Pattern): A kernel file basename, or a regular expression whose
            trailing characters spell out the extension.

    Returns:
        str: The kernel type, e.g., "SPK" or "CK"; an empty string if the extension is
            not one that spyceman recognizes.
    """

    ext = basename_ext(basename).lower()
    return _EXTENSIONS.get(ext, '')


##########################################################################################
# Validation tools
##########################################################################################


# A hyphenated ISO date, optionally followed by a time of day. julian's general-purpose
# parser accepts a far wider range of formats, but it is built on pyparsing and costs
# about a millisecond per call; every date in the kernel catalogs is written in one of
# these two forms, so recognizing them directly avoids the grammar entirely. Anything
# this does not match falls back to julian.
#
# The hyphens are required. Field values are not checked, so an unhyphenated form would
# read any eight digits as a date -- "12345678" as the 78th day of the 56th month of 1234
# -- and the catalogs contain no unhyphenated dates for it to buy anything on.
_ISO_DATETIME = re.compile(r'(\d{4})-(\d{2})-(\d{2})'
                           r'(?:[T ](\d{2}):(\d{2}):(\d{2}(?:\.\d*)?))?')


def _fast_day_sec_from_iso(string):
    """Day number and second of an ISO date-time string, without invoking the parser.

    This is an optimization of julian.day_sec_from_string() for the two formats that
    dominate the kernel catalogs, "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS.fff"; a space may
    replace the "T". A string of any other shape yields None, so that the caller falls
    back to julian.

    The field values are trusted rather than checked. For a date that exists, the result
    is identical to what julian.day_sec_from_string() returns. For one that does not, such
    as "2019-02-29", the surplus days carry over into the following month instead of
    raising, so this must not be used where the string is of unknown provenance.

    Parameters:
        string (str): The string to interpret.

    Returns:
        (int, float), None: The day number relative to 2000-01-01 and the second within
            that day, or None if the string is not of a recognized shape.
    """

    match = _ISO_DATETIME.fullmatch(string)
    if not match:
        return None

    (year, month, day) = (int(g) for g in match.group(1, 2, 3))
    daynum = julian.day_from_ymd(year, month, day)

    if match.group(4) is None:
        return (daynum, 0)

    (hours, minutes) = (int(g) for g in match.group(4, 5))
    return (daynum, hours * 3600 + minutes * 60 + float(match.group(6)))


def validate_release_date(date):
    """Format a given release date as "YYYY-MM-DD". None returns "".

    A date already written as "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS.fff" is converted
    arithmetically and its field values are taken at face value; a date in any other
    format is parsed, and a format that cannot be parsed raises. An impossible date in
    the first group, such as "2019-02-29", is therefore normalized rather than rejected.

    Parameters:
        date (str, optional): A date in nearly any recognizable format; None or an empty
            string means the release date is unknown.

    Returns:
        str: The date as "yyyy-mm-dd", or an empty string if no date was given.
    """

    if date:
        parsed = _fast_day_sec_from_iso(date) if isinstance(date, str) else None
        if parsed is None:
            parsed = julian.day_sec_from_string(date)

        return julian.format_day(parsed[0])

    return ''


def validate_iso_time(string):
    """The ISO date or date-time string converted to a number of seconds TDB.

    This is julian.tdb_from_iso() with the fast path applied first, so an ISO string is
    converted arithmetically and its field values are taken at face value. A string of any
    other shape is passed to julian.tdb_from_iso(), which raises what it always raised;
    use validate_time() instead where a wider range of date formats is to be allowed.

    Parameters:
        string (str): An ISO-format date or date-time string.

    Returns:
        float: The time in seconds TDB.
    """

    parsed = _fast_day_sec_from_iso(string)
    if parsed is None:
        return julian.tdb_from_iso(string)

    return julian.tdb_from_tai(julian.tai_from_day_sec(*parsed))


def validate_version(version, sets_ok=True):
    """Validate a version or set of versions.

    A valid version must be a string, int, or tuple of ints. Multiple versions can be
    included in a set. None returns "". A string containing integers separated by periods
    is converted to a tuple of ints.

    Parameters:
        version (int, str, tuple, set, optional): The version to validate. None means the
            version is undefined.
        sets_ok (bool, optional): True to accept a set of versions; False to reject one.

    Returns:
        int, str, tuple[int, ...], set: The validated version. A single-element tuple is
            reduced to an int; a dot-separated string of integers becomes a tuple of
            ints; any other string is returned unchanged; None becomes an empty string. A
            set input returns a set of validated versions with empty strings removed.

    Raises:
        ValueError: If the version is an empty tuple, contains a non-integer or negative
            component, or is of a type that cannot represent a version.
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
            raise ValueError(f'version as a tuple must contain integers: {version}')
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
                         f'{version!r}')

    validated = set()
    for v in version:
        validated.add(validate_version(v, sets_ok=False))

    validated -= {''}   # None inside a set is meaningless
    return validated


def _naif_id(naif_id):
    """Convert name to int if it is a body name or frame name.

    Parameters:
        naif_id (int, str): A NAIF ID, or the name of a body or frame to look up in the
            kernel pool.

    Returns:
        int: The NAIF ID.

    Raises:
        ValueError: If the input is neither an integer nor a string.
        KeyError: If the name matches no body or frame in the kernel pool.
    """

    if isinstance(naif_id, numbers.Integral):
        return int(naif_id)

    if not isinstance(naif_id, str):
        raise ValueError(f'invalid NAIF ID type: {naif_id!r}')

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

    Parameters:
        ids (int, str, set, list, tuple, optional): One NAIF ID or name, or a collection
            of them. None means no IDs are specified.

    Returns:
        set[int]: The validated NAIF IDs as a set of ints; an empty set if ids is None.

    Raises:
        ValueError: If any input is neither an integer nor a string.
        KeyError: If any name matches no body or frame in the kernel pool.
    """

    if ids is None:
        return set()

    if not isinstance(ids, (set, list, tuple)):
        ids = {ids}

    return {_naif_id(i) for i in ids}   # convert to ints


def naif_ids_with_aliases(ids):
    """Expand a set of NAIF IDs to include all aliases.

    Parameters:
        ids (int, set, list, tuple, optional): One NAIF ID or a collection of them. None
            means no IDs are specified.

    Returns:
        set[int]: The given IDs plus every body and frame alias of each; an empty set if
            ids is None.
    """

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
    """The given NAIF ID or set of IDs, with any aliases replaced by their primary ID.

    Note that an ID with no body or frame aliases defined does not appear in the result.

    Parameters:
        ids (int, set, list, tuple, optional): One NAIF ID or a collection of them. None
            means no IDs are specified.

    Returns:
        set[int]: The primary ID of each input; an empty set if ids is None.
    """

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
    """The time converted to a number of seconds TDB.

    Parameters:
        time (str, float, int): A date-time string in nearly any recognizable format, or
            a number already expressed in seconds TDB.

    Returns:
        float: The time in seconds TDB.

    Raises:
        ValueError: If the input is neither a string nor a real number.
    """

    if isinstance(time, str):
        parsed = _fast_day_sec_from_iso(time)
        if parsed is None:
            parsed = julian.day_sec_from_string(time)

        tai = julian.tai_from_day_sec(*parsed)
        return julian.tdb_from_tai(tai)

    if isinstance(time, numbers.Real):
        return float(time)

    raise ValueError(f'invalid type for time: {time!r}')


##########################################################################################
# Support tools for function inputs
##########################################################################################


def _input_set(value, default=set(), ranges=False):
    """Convert an input value to a set of values; return default if input is None.

    Note that zero is treated as a value rather than as an empty input.

    Parameters:
        value (object): The value to convert. None, or an empty list, set, or tuple, is
            replaced by the default.
        default (object, optional): The value to use when the input is empty. If it is
            also empty, an empty set is returned.
        ranges (bool, optional): True to read a two-element list of integers as an
            inclusive range and expand it into the integers it spans, matching the
            convention that _test_version() uses for versions. A tuple or set of two is
            not a range; only a list is.

    Returns:
        set: The input expressed as a set.
    """

    if not value and value != 0:    # None, empty set, list or tuple, but not zero
        value = default
        if not value and value != 0:
            return set()

    if (ranges and isinstance(value, list) and len(value) == 2
            and all(isinstance(v, numbers.Integral) for v in value)):
        return set(range(value[0], value[1] + 1))

    if isinstance(value, (list, set, tuple)):
        return set(value)

    return {value}


def _input_list(value):
    """Convert an input value to a list of values if it is not currently a list.

    Note that zero is treated as a value rather than as an empty input.

    Parameters:
        value (object): The value to convert. None, or an empty list, set, or tuple,
            yields an empty list.

    Returns:
        list: The input expressed as a list.
    """

    if not value and value != 0:    # None, empty set, list or tuple, but not zero
        return []

    if isinstance(value, (list, set, tuple)):
        return list(value)

    return [value]


def _test_version(input_version, kfile):
    """Compare an input version or a set or range of versions to a KernelFile's
    version(s).

    Parameters:
        input_version (int, str, tuple, set, list): The version constraint. A list of two
            values defines an inclusive range, in which either limit may be None or an
            empty string to leave that end unconstrained. Any other input is compared for
            set overlap with the file's version(s).
        kfile (KernelFile): The kernel file whose version is to be tested.

    Returns:
        bool: True if the file's version satisfies the constraint.

    Raises:
        ValueError: If a range is not a list of exactly two values, if its first value
            exceeds its second, or if the two values cannot be compared.
    """

    # Check a list, which indicates an input range
    if isinstance(input_version, list):
        if len(input_version) != 2:
            raise ValueError(f'a range must be a list of two versions: {input_version}')

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
                                     f'{input_version!r}')
            except TypeError:
                raise ValueError('a range must contain two like values: '
                                 f'{input_version!r}')

        for v in kfile.version_as_set:
            v = (v,) if isinstance(v, numbers.Integral) else v  # int to (int,)

            # A None limit leaves that end of the range unconstrained. A limit that is
            # present but of an incomparable type (a string version against an integer
            # range, say) makes this version a non-match; it does not disqualify the
            # other versions of this file or the other files being filtered.
            try:
                if limits[0] is not None and v < limits[0]:
                    continue                    # below the range
                if limits[1] is not None and v > limits[1]:
                    continue                    # above the range
            except TypeError:
                continue                        # incomparable, so not in the range

            return True

        return False

    # Otherwise, compare sets for overlap
    else:
        if not isinstance(input_version, set):
            input_version = {input_version}

        return bool(input_version & kfile.version_as_set)

##########################################################################################
