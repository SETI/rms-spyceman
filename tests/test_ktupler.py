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

import io

import julian
import pytest

import ktupler
from spyceman import KernelFile, KTuple

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


def test_the_banner_matches_the_wrap_width():
    """A generated file is bannered at the width its lines are wrapped to.

    A table bannered at one width and wrapped to another reads as hand-edited, and the
    package is written to 90 throughout.
    """

    (before, after) = ktupler.new_file_text('_TEST.py', '_TEST')
    banners = [line for line in (before + after).split('\n') if set(line) == {'#'}]

    assert len(banners) == 3
    assert {len(b) for b in banners} == {90}


def test_a_generated_file_opens_and_closes_its_list():
    """The surrounding text declares the list and imports what its entries need."""

    (before, after) = ktupler.new_file_text('a/b/_TEST.py', '_TEST')

    assert 'from spyceman.kernelfile import KTuple' in before
    assert before.endswith('_TEST = [\n')
    assert after.startswith(']\n')
    assert '# a/b/_TEST.py' in before


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


@pytest.fixture
def emit():
    """A factory that catalogs one kernel and returns the lines ktupler writes for it.

    Returns:
        function: Called as emit(basename, tmin, tmax, ids, date); returns the emitted
            text as a list of lines with no trailing newline.
    """

    def make(basename, tmin, tmax, ids, date):
        """Catalog one kernel from its KTuple and emit it.

        Parameters:
            basename (str): The basename to catalog.
            tmin (str, float, optional): Start time; None if undefined.
            tmax (str, float, optional): Stop time; None if undefined.
            ids (set[int], optional): The NAIF IDs; None if the kernel covers all of them.
            date (str, optional): The release date; None if unknown.

        Returns:
            list[str]: The lines ktupler writes for this kernel.
        """

        KernelFile.set_info(KTuple(basename, tmin, tmax, ids, date))
        out = io.StringIO()
        ktupler.print_ktuple(basename, out=out)
        return out.getvalue().split('\n')[:-1]

    return make


def test_the_ktuple_line_is_indented_by_four(emit, unique_name):
    """Each KTuple opens one level inside the list that holds it.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('indent.bsp')
    lines = emit(basename, None, None, {499}, '2019-02-14')

    assert lines[0] == f"    KTuple('{basename}',"


def test_the_arguments_are_indented_by_eight(emit, unique_name):
    """Every argument line sits one level inside its KTuple.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('args.bsp')
    lines = emit(basename, None, None, {499}, '2019-02-14')

    assert lines[1:] == ['        None, None,',
                         '        {499},',
                         "        '2019-02-14'),"]


def test_an_undefined_release_date_is_emitted_as_none(emit, unique_name):
    """A kernel with no release date ends with a bare None at the argument indent.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('undated.bsp')
    lines = emit(basename, None, None, {499}, None)

    assert lines[-1] == '        None),'


def test_a_kernel_covering_all_ids_emits_none(emit, unique_name):
    """An empty ID set is emitted as None rather than as an empty set.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('allids.tls')
    lines = emit(basename, None, None, None, '2019-02-14')

    assert lines[2] == '        None,'


def test_a_wrapped_id_set_stays_within_ninety_columns(emit, unique_name):
    """No emitted line exceeds the width the package is written to.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('wide.bsp')
    lines = emit(basename, None, None, set(range(60000, 60100)), '2019-02-14')

    assert max(len(line) for line in lines) <= 90


def test_a_wrapped_id_set_fills_the_available_width(emit, unique_name):
    """Wrapping happens only where the next ID would not fit.

    A line that stops short would still be under the limit, so the test that no line is
    too wide cannot catch a width set too low.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('full.bsp')
    lines = emit(basename, None, None, set(range(60000, 60100)), '2019-02-14')
    id_lines = lines[2:-1]

    assert min(len(line) for line in id_lines[:-1]) > 90 - len('60099, ')


def test_wrapped_ids_line_up_under_the_opening_brace(emit, unique_name):
    """Continuation lines are indented one space past the brace that opens the set.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('aligned.bsp')
    lines = emit(basename, None, None, set(range(60000, 60100)), '2019-02-14')

    assert lines[3].startswith('         6')


def test_the_emitted_text_parses_back_to_the_same_ktuple(emit, unique_name):
    """What ktupler writes is valid Python that reconstructs the kernel's metadata.

    Parameters:
        emit (function): Fixture that catalogs a kernel and returns its emitted lines.
        unique_name (function): Fixture supplying unique basenames.
    """

    basename = unique_name('roundtrip.bsp')
    ids = set(range(60000, 60100))
    text = '\n'.join(emit(basename, None, None, ids, '2019-02-14'))

    namespace = {'KTuple': KTuple}
    exec(f'_TABLE = [\n{text}\n]', namespace)

    assert namespace['_TABLE'][0] == KTuple(basename, None, None, ids, '2019-02-14')

##########################################################################################
