##########################################################################################
# spyceman/_downloads.py
##########################################################################################
"""Online file retrieval support."""

import os
import pathlib
import requests

if 'SPICE-DOWNLOADS' in os.environ:
    _DOWNLOADS = pathlib.Path(os.environ['SPICE-DOWNLOADS']
elif 'SPICEPATH' in os.environ:
    _DOWNLOADS = pathlib.Path(os.environ['SPICEPATH'].partition(':')[0]) / 'downloads'
else
    _DOWNLOADS = pathlib.Path('spice-downloads')

_HTML_TAG = re.compile(r'<.*?>')
_FIELDS = re.compile(r' *([^ ]+) +(\d\d\d\d-\d\d-\d\d \d\d:\d\d(?:|:\d\d)) +([^ ]+) *')

_FANCY_INDEX_CACHE = {}
_FANCY_INDEX_DATES_CACHE = {}


def get_fancy_index_table(url):
    """The content of a fancy index page as a list of tuples (filename, date, size)."""

    if url in _FANCY_INDEX_CACHE:
        return _FANCY_INDEX_CACHE[url]

    request = requests.get(url, allow_redirects=True)
    if request.status_code != 200:
        raise ConnectionError(f'response {request.status_code} received from {url}')

    text = request.content.decode('latin8')

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
        parts = row.split('<')
        parts = _HTML_TAG.split(row)
        row = ''.join(parts)

        # Interpret the fields
        row_tuples.append(_FIELDS.match(row).groups())

    _FANCY_INDEX_CACHE[url] = row_tuples
    return row_tuples


def get_fancy_index_dates(url):
    """A dictionary mapping file basenames to date strings from a fancy index page."""

    if url in _FANCY_INDEX_DATES_CACHE:
        return _FANCY_INDEX_DATES_CACHE[url]

    table = get_fancy_index_table(url)
    dates = {row[0]:row[1] for row in table}
    _FANCY_INDEX_DATES_CACHE[url] = dates
    return dates


def retrieve_online_file(source, dest, basename, dates=None, label=True):
    """Save a specified file from an online directory. Return the path to the saved file.

    Input:
        source      the online URL source directory of the file.
        dest        subdirectory of the SPICE downloads directory where the file is to be
                    saved.
        basename    the basename of the file.
        dates       optional dictionary mapping basename to date for all the files in this
                    source directory.
        label       True to download any ".lbl" and ".cmt" files as well.
    """

    url = source.rstrip('/') + '/' + basename
    request = requests.get(url, allow_redirects=True)
    if request.status_code != 200:
        raise ConnectionError(f'response {request.status_code} received when downloading '
                              f'kernel file "{basename}" from {source}')

    dest = _DOWNLOADS / dest
    dest.mkdir(parents=True, exist_ok=True)
    destpath = dest / basename
    with destpath.open('wb') as f:
        f.write(request.content)

    # Fix the file date if provided
    if dates:
        timestamp = datetime.datetime.fromisoformat(dates[basename]).timestamp()
        os.utime(destpath.resolve(), (timestamp, timestamp))

    # Download labels if necessary
    if label:
        stem = url.rpartition('.')[0]
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

    Input:
        pattern     regular expression.
        url         the online URL of a fancy index.
        flags       compile flags for a regular expression.
    """

    date_dict = get_fancy_index_dates(url)

    if isinstance(pattern, str):
        if pattern in date_dict:
            return pattern
        else:
            pattern = re.compile(pattern, flags=flags)

    return {b for b in date_dict.keys() if pattern.match(b)}

##########################################################################################
