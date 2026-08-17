##########################################################################################
# spyceman/_downloads.py
##########################################################################################
"""Online file retrieval support."""

import datetime
import os
import pathlib
import re

import requests

if 'SPICE-DOWNLOADS' in os.environ:
    _DOWNLOADS = pathlib.Path(os.environ['SPICE-DOWNLOADS'])
elif 'SPICEPATH' in os.environ:
    _DOWNLOADS = pathlib.Path(os.environ['SPICEPATH'].partition(':')[0]) / 'downloads'
else:
    _DOWNLOADS = pathlib.Path('spice-downloads')

_HTML_TAG = re.compile(r'<.*?>')
_FIELDS = re.compile(r' *([^ ]+) +(\d\d\d\d-\d\d-\d\d \d\d:\d\d(?:|:\d\d)) +([^ ]+) *')

_FANCY_INDEX_CACHE = {}
_FANCY_INDEX_DATES_CACHE = {}


def get_fancy_index_table(url):
    """The content of a fancy index page as a list of tuples (filename, date, size).

    The result is cached, so a given URL is fetched at most once per session. A page that
    is not a fancy index yields an empty list, which is cached as well.

    Parameters:
        url (str): URL of an online directory presented as an Apache "fancy index".

    Returns:
        list[(str, str, str)]: One tuple per table row, containing the file name, the
            modification date as "yyyy-mm-dd hh:mm[:ss]", and the size as displayed. The
            list is empty if the page is not a fancy index.

    Raises:
        ConnectionError: If the server returns a status other than 200.
    """

    if url in _FANCY_INDEX_CACHE:
        return _FANCY_INDEX_CACHE[url]

    request = requests.get(url, allow_redirects=True)
    if request.status_code != 200:
        raise ConnectionError(f'response {request.status_code} received from {url}')

    text = request.content.decode('latin-1')

    # The first line of the fancy index always contains "Parent Directory".
    # The index is printed as pre-formatted text so rows are split by "\n".
    parts = text.rpartition('Parent Directory')
    if not parts[-1]:
        _FANCY_INDEX_CACHE[url] = []
        return []           # not a fancy index!

    rows = parts[-1].split('\n')

    # The record after the last table row always contains "</pre>"
    last = [k for k, row in enumerate(rows) if '</pre>' in row]

    # Select the table rows
    rows = rows[1:last[0]]

    # Interpret each row
    row_tuples = []
    for row in rows:

        # Remove anything inside quotes
        parts = row.split('"')
        row = ''.join(parts[::2])

        # Remove anything inside HTML tags
        parts = _HTML_TAG.split(row)
        row = ''.join(parts)

        # Interpret the fields. A fancy index carries header and separator rows that do
        # not describe a file; skip whatever does not parse rather than abandoning the
        # whole page.
        match = _FIELDS.match(row)
        if match:
            row_tuples.append(match.groups())

    _FANCY_INDEX_CACHE[url] = row_tuples
    return row_tuples


def get_fancy_index_dates(url):
    """A dictionary mapping file basenames to date strings from a fancy index page.

    The result is cached, so a given URL is summarized at most once per session.

    Parameters:
        url (str): URL of an online directory presented as an Apache "fancy index".

    Returns:
        dict[str, str]: Each file basename on the page mapped to its modification date,
            expressed as "yyyy-mm-dd hh:mm[:ss]". The dictionary is empty if the page is
            not a fancy index.

    Raises:
        ConnectionError: If the server returns a status other than 200.
    """

    if url in _FANCY_INDEX_DATES_CACHE:
        return _FANCY_INDEX_DATES_CACHE[url]

    table = get_fancy_index_table(url)
    dates = {row[0]:row[1] for row in table}
    _FANCY_INDEX_DATES_CACHE[url] = dates
    return dates


def retrieve_online_file(source, dest, basename, dates=None, label=True):
    """Save a specified file from an online directory. Return the path to the saved file.

    Parameters:
        source (str): URL of the online directory that contains the file.
        dest (str, pathlib.Path): Subdirectory of the SPICE downloads directory in which
            the file is to be saved.
        basename (str): Basename of the file to retrieve.
        dates (dict, optional): Dictionary mapping basename to date string for every file
            in this source directory. If provided, the saved file's timestamp is set from
            it, and only labels listed in it are downloaded.
        label (bool, optional): True to download any ".lbl" and ".cmt" files that
            accompany the kernel.

    Returns:
        pathlib.Path: Path to the saved file within the local downloads directory.

    Raises:
        ConnectionError: If the server returns a status other than 200 for the kernel
            file itself. Failures on accompanying label files are ignored when no dates
            dictionary is given.
    """

    url = source.rstrip('/') + '/' + basename
    request = requests.get(url, allow_redirects=True)
    if request.status_code != 200:
        raise ConnectionError(f'response {request.status_code} received when downloading '
                              f'kernel file "{basename}" from {source}')

    # Keep `dest` as given: it is passed unchanged to the recursive calls below, which
    # prefix it with _DOWNLOADS themselves. Prefixing it here as well placed labels under
    # "spice-downloads/spice-downloads/..." whenever _DOWNLOADS was a relative path.
    destdir = _DOWNLOADS / dest
    destdir.mkdir(parents=True, exist_ok=True)
    destpath = destdir / basename
    with destpath.open('wb') as f:
        f.write(request.content)

    # Fix the file date if provided
    if dates:
        timestamp = datetime.datetime.fromisoformat(dates[basename]).timestamp()
        os.utime(destpath.resolve(), (timestamp, timestamp))

    # Download labels if necessary
    if label:
        stem = basename.rpartition('.')[0]
        for name in (basename + '.lbl', stem + '.lbl', stem + '.cmt'):
            if dates:
                if name in dates:
                    retrieve_online_file(source, dest, name, dates=dates, label=False)
            else:   # without a dictionary, try each option and ignore failure
                try:
                    retrieve_online_file(source, dest, name, dates=dates, label=False)
                except ConnectionError:
                    pass

    return destpath


def search_fancy_index(pattern, url, flags=re.IGNORECASE):
    """The set of files matching a regular expression at a given URL.

    Parameters:
        pattern (str, re.Pattern): A file basename or regular expression to match against
            the names on the page. A string that is itself a name on the page is returned
            directly rather than being treated as a pattern.
        url (str): URL of an online directory presented as an Apache "fancy index".
        flags (RegexFlag, optional): Compile flags to use if the pattern is a string;
            default is re.IGNORECASE.

    Returns:
        set[str]: The basenames on the page that match the pattern. A pattern that names
            a file on the page exactly yields a one-element set.

    Raises:
        ConnectionError: If the server returns a status other than 200.
    """

    date_dict = get_fancy_index_dates(url)

    if isinstance(pattern, str):
        if pattern in date_dict:
            return {pattern}
        pattern = re.compile(pattern, flags=flags)

    return {b for b in date_dict.keys() if pattern.match(b)}

##########################################################################################
