##########################################################################################
# tests/test_dates.py: Tests of the fast ISO date parser and its callers
##########################################################################################
"""Tests of _fast_day_sec_from_iso() and the functions built on it.

The fast path exists as an optimization for kernel catalog dates, which are machine
generated and therefore known to be well formed. It recognizes strings by shape and takes
their field values at face value, so the contract it must honor is:

* For a date that exists, it returns exactly what julian.day_sec_from_string() returns.
* For a string of any other shape, it returns None and the caller falls back to julian,
  which raises whatever it always raised.

It does not check whether a recognized date is a real one. "2019-02-29" is normalized to
2019-03-01 rather than rejected, and the tests below record that rather than assert
against it. Most of these tests compare against julian directly rather than hard-coding
day numbers.
"""

import itertools

import julian
import pytest

from spyceman._utils import (_fast_day_sec_from_iso, validate_iso_time,
                             validate_release_date, validate_time)


def julian_result(string):
    """The day and second julian derives from a string, or None if it rejects it.

    Parameters:
        string (str): The string to interpret.

    Returns:
        (int, float), None: The day number and second, or None if julian raises.
    """

    try:
        return tuple(julian.day_sec_from_string(string))
    except Exception:               # julian raises several unrelated exception types
        return None


##########################################################################################
# Equivalence with julian
##########################################################################################

@pytest.mark.parametrize('string', [
    '2020-02-12',                   # the form every KTuple release date takes
    '2020-02-12T00:00:00',
    '2020-02-12T12:34:56',
    '2020-02-12T12:34:56.789',      # the form every KTuple time takes
    '2020-02-12 12:34:56',          # a space may replace the "T"
    '2020-02-29',                   # leap day
    '2000-02-29',                   # leap day in a century year divisible by 400
    '1582-10-15',                   # first day after the Gregorian reform
    '1582-10-04',                   # last day before it
    '0001-01-01',
    '9999-12-31',
])
def test_accepted_strings_match_julian(string):
    """Every string the fast path accepts yields exactly julian's answer.

    Parameters:
        string (str): A date or date-time string the fast path is expected to handle.
    """

    result = _fast_day_sec_from_iso(string)
    assert result is not None, 'the fast path declined a string it should handle'
    assert tuple(result) == julian_result(string)


@pytest.mark.parametrize('string, normalized', [
    ('2019-02-29', '2019-03-01'),   # not a leap year
    ('1900-02-29', '1900-03-01'),   # century year not divisible by 400
    ('2020-02-30', '2020-03-01'),
    ('2020-06-31', '2020-07-01'),
])
def test_impossible_dates_are_normalized_rather_than_rejected(string, normalized):
    """A date that does not exist carries over instead of raising.

    This records the cost of trusting the input: julian.day_from_ymd() does no validation,
    and the fast path adds none, so a date that julian's parser would reject is silently
    normalized. Catalog dates are machine generated and cannot reach this, but a
    hand-supplied one can.

    Parameters:
        string (str): A syntactically well-formed but impossible date.
        normalized (str): The real date it is taken to mean.
    """

    assert julian_result(string) is None, 'julian was expected to reject this'

    result = _fast_day_sec_from_iso(string)
    assert result is not None
    assert julian.format_day(result[0]) == normalized


@pytest.mark.parametrize('string', [
    '2016-12-31T23:59:60',          # a real leap second
    '2016-12-31T23:59:60.5',
])
def test_leap_seconds_still_match_julian(string):
    """A leap second on a day that carries one still agrees with julian.

    Seconds accumulate arithmetically, so a 60th second lands exactly where julian's
    leap-second table puts it.

    Parameters:
        string (str): A date-time string ending in a leap second.
    """

    assert tuple(_fast_day_sec_from_iso(string)) == julian_result(string)


@pytest.mark.parametrize('string', [
    '2020-044',                     # ordinal date
    '2020044',
    '2020/02/12',                   # slashes
    ' 2020-02-12 ',                 # surrounding whitespace
    '2020-2-12',                    # unpadded month
    '2020-02-12Z',
    '2020-02-12T12:34',             # no seconds field
    '-501-12-05T23:59:17.816',      # negative year, which julian cannot parse either
    '',
    'garbage',
    '12345678',                     # eight digits, but not a hyphenated date
    '20200212',                     # the compact ISO form is deliberately not handled
])
def test_unrecognized_forms_are_declined(string):
    """Anything outside the two supported shapes falls back to julian.

    Parameters:
        string (str): A string the fast path is not expected to handle.
    """

    assert _fast_day_sec_from_iso(string) is None


def test_a_leap_second_lands_one_second_before_midnight():
    """The 60th second of a leap-second day is the second before the next day begins.

    This is the end-to-end check that the arithmetic path handles a leap second, rather
    than merely returning the same numbers julian does for it.
    """

    assert validate_time('2016-12-31T23:59:60') == pytest.approx(
                                            validate_time('2017-01-01T00:00:00') - 1.)


def test_every_real_day_of_a_leap_year_matches_julian():
    """Across a full leap year, every date that exists matches julian exactly.

    This covers month lengths and the February boundary without a case per date. Dates
    that do not exist are skipped, since the fast path no longer judges them.
    """

    checked = 0
    for month, day in itertools.product(range(1, 13), range(1, 32)):
        string = f'2020-{month:02d}-{day:02d}'
        expected = julian_result(string)
        if expected is None:            # not a real date; julian rejects it
            continue

        assert tuple(_fast_day_sec_from_iso(string)) == expected, string
        checked += 1

    assert checked == 366, 'a leap year has 366 days'


##########################################################################################
# The callers
##########################################################################################

@pytest.mark.parametrize('date, expected', [
    ('2020-02-12', '2020-02-12'),
    ('20200212',   '2020-02-12'),   # compact form, normalized via julian
    ('2020/02/12', '2020-02-12'),   # goes through julian, formatted the same way
    ('2020-044',   '2020-02-13'),   # ordinal date, also via julian
])
def test_validate_release_date_formats_consistently(date, expected):
    """A release date is normalized to "YYYY-MM-DD" whichever path parses it.

    Parameters:
        date (str): The date as given.
        expected (str): The normalized form.
    """

    assert validate_release_date(date) == expected


@pytest.mark.parametrize('date', [None, '', 0])
def test_validate_release_date_of_nothing_is_empty(date):
    """An absent release date yields an empty string rather than raising.

    Parameters:
        date (str, optional): A value meaning the release date is unknown.
    """

    assert validate_release_date(date) == ''


def test_validate_release_date_normalizes_an_impossible_iso_date():
    """An impossible date in ISO form is normalized, not rejected.

    The same date written in a format the fast path does not recognize still raises,
    because that one reaches julian. The inconsistency is the price of trusting the
    catalog dates, and is recorded here so that it is a known property rather than a
    surprise.
    """

    assert validate_release_date('2019-02-29') == '2019-03-01'

    with pytest.raises(Exception):
        validate_release_date('2019/02/29')


def test_validate_time_matches_between_the_two_paths():
    """The same instant expressed two ways gives the same TDB seconds.

    "2020-02-12T00:00:00" takes the fast path and "2020/02/12" takes julian's, so this
    checks that the optimization did not shift the result.
    """

    assert validate_time('2020-02-12T00:00:00') == validate_time('2020/02/12')


def test_validate_time_is_seconds_within_the_day():
    """A time of day advances the result by exactly that many seconds."""

    midnight = validate_time('2020-02-12T00:00:00')
    later = validate_time('2020-02-12T12:34:56.500')
    assert later - midnight == pytest.approx(12 * 3600 + 34 * 60 + 56.5)


def test_validate_time_passes_numbers_through():
    """A numeric time is already in seconds TDB and is returned unchanged."""

    assert validate_time(-78895166399.99977) == pytest.approx(-78895166399.99977)


def test_validate_time_rejects_a_bad_type():
    """A time that is neither a string nor a real number raises ValueError."""

    with pytest.raises(ValueError, match='invalid type for time'):
        validate_time(['2020-02-12'])


@pytest.mark.parametrize('string', [
    '2020-02-12',
    '2020-02-12T00:00:00',
    '1997-10-15T09:26:08.390',      # the form KTuple start and stop times take
    '2015-02-02T05:58:52.815',
    '2016-12-31T23:59:60',          # leap second, handled by the fallback
])
def test_validate_iso_time_matches_julian(string):
    """validate_iso_time() returns exactly what julian.tdb_from_iso() returns.

    Parameters:
        string (str): An ISO date or date-time string.
    """

    assert validate_iso_time(string) == julian.tdb_from_iso(string)


@pytest.mark.parametrize('string', ['garbage', '2020/02/12', '2020-02-12Z'])
def test_validate_iso_time_does_not_widen_the_accepted_formats(string):
    """A string of a shape julian.tdb_from_iso() rejects is still rejected.

    The fast path must not widen the set of accepted formats; "2020/02/12" is a date
    julian's general parser handles but its ISO parser does not, and it must stay
    rejected here.

    Parameters:
        string (str): A string the ISO conversion is expected to reject.
    """

    with pytest.raises(Exception):
        julian.tdb_from_iso(string)

    with pytest.raises(Exception):
        validate_iso_time(string)

##########################################################################################
