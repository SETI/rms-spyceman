##########################################################################################
# tests/test_ktupler.py: Tests of the KTuple table generator in programs/
##########################################################################################
"""Tests of programs/ktupler.py, which emits the machine-generated _UPPERCASE.py tables.

The generator writes 13,600 lines of the package's data, so an error here becomes an error
in every catalog that reads what it wrote, and only when a module far away tries to parse
it. That is what happened with the time formatting below: a date julian could produce but
could not read back was written into _SATURN_SPKS.py and raised on import months later.

Importing this module sets julian's UT model to "SPICE", as the generator does, so that
the times it produces match the ones already in the tables.
"""

import julian
import pytest

import ktupler

# The start of sat441xl_part-1.bsp, which spans 501 BCE to 4500 CE. Formatted as a date it
# reads "-501-12-05T23:59:18.816", which julian will produce but cannot parse back.
NEGATIVE_YEAR_TDB = -78895166399.99977

# A date in the year 10400, the other side of the four-digit range.
FIVE_DIGIT_YEAR_TDB = 265078526469.18292


@pytest.fixture(autouse=True)
def spice_ut_model():
    """Select the UT model the generator runs under, and restore julian's default after.

    The model is global to julian and the generator sets it at import, so a test that did
    not manage it would leave every later test in this process using it.

    Returns:
        None: The fixture exists for its side effects.
    """

    julian.set_ut_model('SPICE')
    yield
    julian.set_ut_model('LEAPS')


def test_an_undefined_time_is_reported_as_none():
    """A kernel with no time limit emits the bare word None, not a quoted string."""

    assert ktupler.format_time(None) == 'None'


def test_a_four_digit_year_is_quoted_without_a_zero_fraction():
    """An ordinary date is emitted as a quoted string, with a ".000" fraction dropped."""

    tdb = julian.tdb_from_tai(julian.tai_from_iso('2000-01-01T12:00:00'))

    assert ktupler.format_time(tdb) == "'2000-01-01T12:00:00'"


def test_fractional_seconds_are_kept():
    """A time that is not a whole second keeps its three-digit fraction."""

    tdb = julian.tdb_from_tai(julian.tai_from_iso('2000-01-01T12:00:00')) + 0.5

    assert ktupler.format_time(tdb) == "'2000-01-01T12:00:00.500'"


def test_a_negative_year_is_emitted_as_a_number():
    """A BCE date is emitted as seconds TDB, because julian cannot parse one back.

    Testing character 4 of the date alone let this through: "-501-12-05" carries "-"
    there just as "2000-01-01" does.
    """

    assert ktupler.format_time(NEGATIVE_YEAR_TDB) == str(NEGATIVE_YEAR_TDB)


def test_a_negative_year_round_trips_through_its_number():
    """The number emitted for a BCE date reads back as the time it came from."""

    assert float(ktupler.format_time(NEGATIVE_YEAR_TDB)) == NEGATIVE_YEAR_TDB


def test_a_five_digit_year_is_emitted_as_a_number():
    """A date beyond year 9999 is emitted as seconds TDB for the same reason."""

    assert ktupler.format_time(FIVE_DIGIT_YEAR_TDB) == str(FIVE_DIGIT_YEAR_TDB)


def test_a_five_digit_year_round_trips_through_its_number():
    """The number emitted for a far-future date reads back as the time it came from."""

    assert float(ktupler.format_time(FIVE_DIGIT_YEAR_TDB)) == FIVE_DIGIT_YEAR_TDB


def test_the_first_version_of_a_file_is_v1(tmp_path):
    """A file with no saved versions yet gets "_v1".

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
    """

    path = tmp_path / '_MARS_SPKS.py'
    path.write_text('current\n')

    assert ktupler.new_version(path) == tmp_path / '_MARS_SPKS_v1.py'


def test_the_next_version_follows_the_highest_saved_one(tmp_path):
    """The number chosen is one past the highest already in the directory.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
    """

    path = tmp_path / '_MARS_SPKS.py'
    path.write_text('current\n')
    for index in (1, 2, 3):
        (tmp_path / f'_MARS_SPKS_v{index}.py').write_text('saved\n')

    assert ktupler.new_version(path) == tmp_path / '_MARS_SPKS_v4.py'


def test_version_numbers_are_compared_as_numbers(tmp_path):
    """Past nine saved versions, the next number is still an unused one.

    Sorted as names, "_v10.py" precedes "_v2.py", so the highest version found would be
    "_v9.py" and the file already saved as "_v10.py" would be overwritten.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
    """

    path = tmp_path / '_MARS_SPKS.py'
    path.write_text('current\n')
    for index in range(1, 11):
        (tmp_path / f'_MARS_SPKS_v{index}.py').write_text('saved\n')

    assert ktupler.new_version(path) == tmp_path / '_MARS_SPKS_v11.py'


def test_unrelated_neighbors_are_ignored(tmp_path):
    """A file that shares the prefix but carries no version number does not count.

    Parameters:
        tmp_path (pathlib.Path): Fixture supplying a temporary directory.
    """

    path = tmp_path / '_MARS_SPKS.py'
    path.write_text('current\n')
    (tmp_path / '_MARS_SPKS_v1.py').write_text('saved\n')
    (tmp_path / '_MARS_SPKS_v1_backup.py').write_text('not a version\n')

    assert ktupler.new_version(path) == tmp_path / '_MARS_SPKS_v2.py'

##########################################################################################
