##########################################################################################
# spyceman/_utils.py
##########################################################################################
"""Utilities."""

import julian
import numbers

import cspyce


def validate_release_date(date):
    """Format a given release date as "YYYY-MM-DD"."""

    if date:
        (day, _) = julian.day_sec_from_string(date)
        return julian.format_day(day)

    return ''


def validate_version(version):
    """Validate version or set of versions."""

    if version is None:
        return ''

    if isinstance(version, set):
        validated = set()
        for v in version:
            validated.add(_validate_version(v))
        return validated

    if isinstance(version, numbers.Integral):
        if version < 0:
            raise ValueError('version cannot be negative: ' + version)

        return int(version)

    if isinstance(version, (tuple, list)):
        if len(version) == 0:
            raise ValueError('version tuple is empty')

        version = tuple(version)
        if not all((isinstance(i, numbers.Integral) for i in value)):
            raise ValueError('version as a tuple must contain integers: '
                             + repr(version))
        if not all((i >= 0 for i in value)):
            raise ValueError('version cannot be negative: ' + repr(version))

        if len(version) == 1:
            return int(version[0])

        return tuple(int(i) for i in version)

    if not isinstance(version, str):
        raise TypeError('invalid version, must be string, int, or tuple of ints: '
                        + repr(value))

    # Convert a dot-separated string of ints to a tuple
    parts = version.split('.')
    try:
        test = [int(p) for p in parts]
    except ValueError:
        pass
    else:
        return _KernelInfo._validate_version(test)

    return version


def naif_ids_with_aliases(ids):

    if isinstance(ids, numbers.Integral):
        ids = {ids}

    all_ids = set(ids)
    for naif_id in ids:
        all_ids |= set(cspyce.get_body_aliases(naif_id)[0])

        # Insert the spacecraft ID for any spacecraft frame ID
        if naif_id < -1000:
            all_ids.add(-(-naif_id//1000))

    # Include body IDs for frame IDs, but not the other way around
    if any(i for i in all_ids if i >= 10000 and i < 50000):
        for naif_id in ids:
            all_ids |= set(cspyce.get_frame_aliases(naif_id)[0] + [naif_id])

    return all_ids


def naif_ids_wo_aliases(ids):

    if isinstance(ids, numbers.Integral):
        ids = {ids}

    return {(cspyce.get_body_aliases(naif_id)[0] + [naif_id])[0] for naif_id in ids}

##########################################################################################
