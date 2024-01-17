##########################################################################################
# spyceman/rule.py
##########################################################################################
"""Class defining rules for extracting a release date, time range, version, and/or other
property information from a file basename.
"""

import julian
import re

from spyceman._ktypes import _EXTENSIONS
from spyceman._utils  import validate_version

_MON_DICT = {'jan':'01', 'feb':'02', 'mar':'03', 'apr':'04', 'may':'05', 'jun':'06',
             'jul':'07', 'aug':'08', 'sep':'09', 'oct':'10', 'nov':'11', 'dec':'12'}

# Construct the regular expression for each date option
_YYYY = r'(?:19[7-9]\d|20\d\d)'
_YY   = r'\d\d'
_MON  = (r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
             'JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|'
             'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)')
_MM   = r'(?:0[1-9]|1[0-2])'
_DD   = r'(?:0[1-9]|[12]\d|3[01])'
_DOY  = r'(?:00[1-9]|0[1-9]\d|[12]\d\d|3[0-5]\d|36[0-6])'

##########################################################################################
# General Rule class
##########################################################################################

class Rule:
    """Class defining one rule for how to interpret a SPICE file basename containing a
    release date, time range, version, and/or other property information.

    If the file basename matches a specified pattern, then
        rule.match(basename)
    will return a dictionary containing the extracted information, keyed as follows:
        "date"      the identified release date in "YYYY-MM-DD" format.
        "time"      a tuple containing the start and stop times represented as seconds
                    TDB.
        "version"   the version identification, identified by an integer, tuple of
                    integers, or a string.
        "family"    the family name, which identifies the file basename after the other
                    information has been removed.
    If additional properties are defined by the basename, they will appear as additional
    keys in the dictionary.

    As each Rule is defined, it is saved in an internal dictionary. Use
        Rule.apply(basename)
    to search the list of defined rules for the one that matches the basename, and then
    return the information extracted from it.
    """

    # _RULES is an internal dictionary of all rules, keyed by file extension (in lower
    # case) and then by the number of embedded fields, counting the time limits as two
    # and all properties employing a group as one. When matching basenames, the rules with
    # the larger number of fields are tested later, giving them higher precedence.

    rules_by_count = {1:[], 2:[], 3:[], 4:[], 5:[]}

    _RULES = {}
    for ext in _EXTENSIONS:
        _RULES = rules_by_count.copy()

    _RULES[''] = rules_by_count.copy()  # if the file extension is not explicit

    def __init__(self, pattern, family='', flags=re.I, *, datefirst=True, inclusive=True,
                       case='mixed', version=None, group=1, **properties):
        """Constructor for a Rule.

        Input:
            pattern     a regular expression string that matches the file basename.
                        However, that components of this expression that indicate a
                        release date, time limits, or version must be replaced by special
                        tags, which are always enclosed in parentheses.

                        A date or a time limit must be replaced by one of these tags:
                            "YYYYMONDD"     e.g., "2022Dec01"
                            "YYYY_MON_DD"   e.g., "2022_Dec_01"
                            "YYYY-MON-DD"   e.g., "2022-Dec-01"
                            "YYYYMMDD"      e.g., "20221201"
                            "YYYY_MM_DD"    e.g., "2022_12_01"
                            "YYYY-MM-DD"    e.g., "2022-12-01"
                            "YYMONDD"       e.g., "22Dec01"
                            "YY_MON_DD"     e.g., "22_Dec_01"
                            "YY-MON-DD"     e.g., "22-Dec-01"
                            "YYMMDD"        e.g., "221201"
                            "YY_MM_DD"      e.g., "22_12_01"
                            "YY-MM-DD"      e.g., "22-12-01"
                            "YYYYDOY"       e.g., "2022305"
                            "YYYY_DOY"      e.g., "2022_305"
                            "YYYY-DOY"      e.g., "2022-305"
                            "YYDOY"         e.g., "22305"
                            "YY_DOY"        e.g., "22_305"
                            "YY-DOY"        e.g., "22-305"
                            "DDMONYYYY"     e.g., "01Dec2022"
                            "DD_MON_YYYY"   e.g., "01_Dec_2022"
                            "DD-MON-YYYY"   e.g., "01-Dec-2022"
                            "DDMMYYYY"      e.g., "01122022"
                            "DD_MM_YYYY"    e.g., "01_12_2022"
                            "DD-MM-YYYY"    e.g., "01-12-2022"
                            "DDMONYY"       e.g., "01Dec22"
                            "DD_MON_YY"     e.g., "01_Dec_22"
                            "DD-MON-YY"     e.g., "01-Dec-22"
                            "DDMMYYYY"      e.g., "011222"
                            "DD_MM_YY"      e.g., "01_12_22"
                            "DD-MM-YY"      e.g., "01-12-22"

                        A version number of known width must be tagged by an equal number
                        of "N" characters. For example, a three-digit version number is
                        represented by "NNN". A version number of variable width with must
                        be replaced by "N+". Note that a version number can be indicated
                        by multiple fields in a file name, e.g. "kernel_v10.2.3.ck" would
                        be matched by "kernel_v(NN).(N).(N).ck".

                        A version can also be represented by an embedded substring. If
                        that embedded substring has a known length, replace it by an equal
                        number of "X" characters. If it has a variable width, represent it
                        by "X+. A name string must be composed exclusively of letters,
                        digits, dashes, and underscores. It cannot begin or end with an
                        underscore or dash.

            family      an optional regular expression capture pattern to define the
                        family name after the embedded information has been removed. By
                        default, a family name is created by using the given basename and
                        replacing each embedded field with its tag. You can override this
                        default behavior by providing a string containing replacement
                        patterns "\\1", "\\2", etc.

            flags       the flags to use when compiling the pattern; default is
                        re.IGNORECASE.

            datefirst   if a pattern contains three dates, use True to indicate that the
                        release date appears before the start/stop times; False if
                        the release date appear after them.

            inclusive   True if the stop time includes the entire 24 hours of the second
                        embedded date; False if it is excluded.

            version     if provided, this value will be assigned to the version of any
                        file matching the given pattern. This can be useful if file names
                        are inconsistent, such that different versions of a file match
                        different patterns.

                        Alternatively, the value can be a dictionary or a function. If it
                        is a dictionary, the capture pattern is converted to lower case
                        and used as a key into this dictionary. If it is a function, the
                        the value returned by this function will be returned. For example,
                        to convert the captured substring to upper case, use
                        "version=str.upper".

            name=value  one or more name/value pairs that will be defined as properties.
                        The value can be any of these:
                            None            use the captured match pattern identified by
                                            group.
                            any function    the value of this function applied to the
                                            matched pattern. Use "name=int" to conver to
                                            integer; "name=str.upper" to convert to upper
                                            case, etc.
                            any dictionary  convert the matched pattern to lower case and
                                            use it as a key to this dictionary; if the key
                                            is not in the dictionary, leave this property
                                            unassigned;
                            anything else   return this given value for the property.
                        If the property name is associated with a captured substring, then
                        the pattern must contain a capture pattern using the same name,
                        via "(?P<name>...)".
        """

        # Identify the file extension; use "" if it cannot be inferred
        self.pattern = pattern
        ext = '.' + pattern.rpartition('.')[-1].lower()
        if ext not in Rule._RULES:
            ext = ''

        # Update the pattern, replacing tags with their regular expressions
        # Track the location and type of each tag among the match patterns
        parts = pattern.split('(')
        new_parts = [parts[0]]

        tagged_groups = [[],[],[]]  # (group index, tag) for dates, numbers, names
        group_index = 0
        for part in parts[1:]:
            if part[:2] in ('?:', '?#', '?!') or part[:3] in ('?P=', '?<=', '?<!'):
                new_parts.append(part)
                continue

            group_index += 1
            subparts = part.partition(')')
            if not subparts[1]:
                raise ValueError('nested capture patterns are not permitted: '
                                 + repr(pattern))

            for i, func in enumerate([Rule._date_pattern,
                                      Rule._version_number_pattern,
                                      Rule._version_name_pattern]):

                pattern = func(subparts[0])
                if pattern:
                    break

            if pattern:
                new_parts += ['(', pattern, ')', subparts[2]]
                tagged_groups[i].append((group_index, subparts[0]))
            else:
                new_parts += ['('] + list(subparts)

        self.regex = re.compile(''.join(new_parts), flags=flags)

        # Identify the date and time groups
        date_groups = tagged_groups[0]      # = list of tuples (group index, matched tag)
        if len(date_groups) > 3:
            raise ValueError('more than three embedded date tags')

        if len(date_groups) == 3 and not datefirst:
            date_groups = date_groups[2:] + date_groups[:2]     # move date to front

        if len(date_groups) in (1,3):
            (self._date_group, self._date_tag) = date_groups[0]
        else:
            (self._date_group, self._date_tag) = (0, '')

        if len(date_groups) >= 2:
            time_groups = date_groups[-2:]
            self._time_groups = [t[0] for t in time_groups]
            self._time_tags = [t[1] for t in time_groups]
        else:
            self._time_groups = []
            self._time_tag = ''

        self._inclusive = bool(inclusive)

        # Identify the version
        value_needed = (isinstance(version, (type(None), dict))
                        or hasattr(version, '__call__'))
        if value_needed:
            self._version = version
        else:
            self._version = validate_version(version)

        number_groups = tagged_groups[1]
        name_groups = tagged_groups[2]
        if number_groups and name_groups:
            raise ValueError('version numbers and version name tags cannot both be '
                             'present')
        if len(name_groups) > 1:
            raise ValueError('duplicated version name tags')

        if number_groups or name_groups:
            if not value_needed:
                raise ValueError('embedded version tags are incompatible with the input '
                                 'literal value of version')
        elif value_needed:
            raise ValueError('missing embedded version tag(s)')

        if name_groups:
            self._version_groups = [name_groups[0][0]]
            self._version_tags = [name_groups[0][1]]
            self._version_type = 'str'
        else:
            self._version_groups = [t[0] for t in number_groups]
            self._version_tags = [t[1] for t in number_groups]
            self._version_type = 'tuple' if len(number_groups) > 1 else 'int'

        # Identify the family
        self._family = family and re.compile(family)

        # Save the additional properties
        self._properties = properties
        self._captures = []
        for name, value in properties.items():
            if isinstance(value, (dict, type(None))) or hasattr(value, '__call__'):
                self._captures.append(name)

        # Register in the global dictionary of rules
        field_count = len(date_groups) + bool(self._version_groups) + bool(self._captures)
        Rule._RULES[ext][field_count].append(self)

    def match(self, basename):
        """Return a dictionary of information about the given basename assuming that this
        rule applies.

        If the rule does not appy, the returned dictionary is empty. Otherwise, the
        dictionary has the following keys:
            "date"      the identified release date in "YYYY-MM-DD" format.
            "time"      a tuple containing the start and stop times represented as
                        seconds TDB.
            "version"   the version, identified by an integer, tuple of integers, or
                        a string.
            "family"    the family name, which identifies the file basename after the
                        tagged information has been removed.
        If additional properties are defined by the basename, they will appear as
        additional keys in the dictionary.
        """

        match = self.regex.fullmatch(basename)
        if not match:
            return {}

        results = {}

        # Handle release date
        if self._date_group:
            iso = Rule._date_iso(match.group(self.date_group), self._date_tag)
            results['date'] = iso

        # Handle time limits
        if self._time_groups:
            times = []
            for time_group, time_tag in zip(self._time_groups, self._time_tags):
                iso = Rule._date_iso(match.group(time_group), time_tag)
                times.append(julian.tdb_from_iso(iso))

            if self._inclusive:
                times[1] += 86400.

            results['time'] = tuple(times)

        # Handle version ID
        if self._version_groups:
            if self._version_type == 'str':
                version = match.group(self._version_groups[0])
            elif self.version_type == 'int':
                version = int(match.group(self._version_groups[0]))
            else:
                ints = []
                for version_group in self._version_groups:
                    ints.append(int(match.group(version_group)))
                version = tuple(ints)

            if hasattr(self._version, '__call__'):
                version = self._version(version)
            elif isinstance(self._version, dict):
                if self._version_type == 'str':
                    version = version.lower()
                version = self._version[version]

            results['version'] = version

        elif self._version is not None:
            results['version'] = version

        # Create the family name
        if self._family:
            results['family'] = match.expand(self._family)
        else:
            groups_and_tags = [(self._date_group, self._date_tag)]
            if self._time_groups:
                groups_and_tags += [(self._time_groups[0], self._time_tags[0]),
                                    (self._time_groups[1], self._time_tags[1])]
            groups_and_tags += list(zip(self._version_groups, self._version_tags))

            groups_and_tags.sort(reverse=True)      # work backwards from the end!
            family = basename
            for (group, tag) in groups_and_tags:
                i = match.start(group)
                j = match.end(group)
                family = family[:i] + tag + family[j:]

            results['family'] = family

        # Check for additional properties
        for name, value in self._properties.items():
            if name in self._captures:
                capture = match.group(name)

            try:
                if value is None:
                    results[name] = capture
                elif isinstance(value, dict):
                    capture = capture.lower()
                    if capture in value:
                        results[name] = value[capture]
                elif hasattr(value, '__call__'):
                    test = value.__call__(capture)
                    if test is not None:
                        results[name] = test
                else:
                    results[name] = value
            except Exception:
                pass

    @staticmethod
    def apply(basename):
        """Extract the rule-based info from a SPICE kernel basename that matches any of
        the defined rules.
        """

        ext = '.' + basename.rpartition('.')[-1].lower()
        if ext in Rule._RULES:
            key_list = ('', ext)
        else:
            key_list = ('')

        results = {}
        for fields in range(1, 6):
            for key in key_list:
                for rule in Rule._RULES[key][fields]:
                    results.update(rule.match(basename))

        return results

    ######################################################################################
    # Utilities
    ######################################################################################

    @staticmethod
    def _date_pattern(tag):
        """The regular expression associated with this date tag.

        If it is not a recognized date tag, return an empty string.
        """

        # If this is not a valid date tag, return ""
        test = tag
        test = test.replace('YYYY', 'YY')

        if 'DOY' in test:
            if test not in ('YYDOY', 'YY_DOY', 'YY-DOY'):
                return ''
        else:
            test = test.replace('MON', 'MM')
            if test not in ('YYMMDD', 'YY_MM_DD', 'YY-MM-DD',
                            'DDMMYY', 'DD_MM_YY', 'DD-MM-YY'):
                return ''

        # Convert the tag to a regular expression
        pattern = tag
        pattern.replace('YYYY', _YYYY)
        pattern.replace('YY',   _YY)
        pattern.replace('MM',   _MM)
        pattern.replace('MON',  _MON)
        pattern.replace('DD',   _DD)
        pattern.replace('DOY',  _DOY)

        return pattern

    @staticmethod
    def _date_iso(string, tag):
        """The matched date string in "yyyy-mm-dd" format."""

        if 'YYYY' in tag:
            i = tag.index('YYYY')
            year = int(string[i:i+4])
        else:
            i = tag.index('YY')
            year = 2000 + int(string[i:i+2])
            if year >= 2070:
                year -= 100

        if 'DOY' in tag:
            i = tag.index('DOY')
            day = julian.day_from_yd(year, int(string[i:i+3]))
            return julian.iso_from_day(day)
        elif 'MON' in tag:
            i = tag.index('MON')
            mm = _MON_DICT[string[i:i+3].lower()]
        else:
            i = tag.index('MM')
            mm = string[i:i+2]

        i = tag.index('DD')
        dd = int(string[i:i+2])
        return f'{year}-{mm}-{dd}'

    @staticmethod
    def _version_number_pattern(tag):
        """The regular expression associated with this version number tag.

        If it is not a recognized version tag, return an empty string.
        """

        if tag == 'N+':
            return r'\d+'

        if all(t == 'N' for t in tag):
            return tag.replace('N', r'\d')

        return ''

    @staticmethod
    def _version_name_pattern(tag):
        """The regular expression associated with this version name tag."""

        if tag == 'X+':
            return r'[a-zA-Z0-9](?:|[\w-]*[a-zA-Z0-9])'

        if not all(t == 'X' for t in tag):
            return ''

        if len(tag) == 1:
            return '[a-zA-Z0-9]'

        if len(tag) == 2:
            return '[a-zA-Z0-9]{2}'

        return r'[a-zA-Z0-9][\w-]{' + str(len(tag)-2) + '}[a-zA-Z0-9]'

##########################################################################################
# Default rule support
##########################################################################################

class _DefaultRule:
    """Instance-free class defining the default rule for matching basenames."""

    def apply(basename):

        results = {}

        (family, dates) = _default_dates_from_basename(basename)
        if len(dates) in (1,3):
            results['date'] = dates[0]
        if len(dates) in (2,3):
            results['time'] = (julian.tdb_from_iso(dates[-2]),
                               julian.tdb_from_iso(dates[-1]))

        (family, version) = _default_version_from_basename(basename)
        if version is not None:
            results['version'] = version

        if family != basename:
            results['family'] = family

        return results


_MON_MM  = '(?:' + _MON  + '|' + _MM + ')'
_YYYY_YY = '(?:' + _YYYY + '|' + _YY + ')'

_SEP = '(?:|_|-)'

_SPLIT_OPTIONS = [
    r'(?<!\d)' + _YYYY_YY + _SEP + _MON_MM + _SEP + _DD      + r'(?!\d)',
    r'(?<!\d)' + _DD      + _SEP + _MON_MM + _SEP + _YYYY_YY + r'(?!\d)',
    r'(?<!\d)' + _YYYY_YY + _SEP + _DOY    +                   r'(?!\d)',
]

_NAMED_YEAR = '(?P<y>' + _YYYY_YY + ')'
_NAMED_MON  = '(?P<m>' + _MON_MM  + ')'
_NAMED_DAY  = '(?P<d>' + _DD      + ')'
_NAMED_DOY  = '(?P<d>' + _DOY     + ')'
_NAMED_SEP  = '(?P<x>|_|-)'
_REPEAT_SEP = '(?P=x)'

_PARSE_OPTIONS = [
    _NAMED_YEAR + _NAMED_SEP + _NAMED_MON + _REPEAT_SEP + _NAMED_DAY,
    _NAMED_DAY  + _NAMED_SEP + _NAMED_MON + _REPEAT_SEP + _NAMED_YEAR,
    _NAMED_YEAR + _NAMED_SEP + _NAMED_DOY,
]

# Compile the above
for _k in range(len(_SPLIT_OPTIONS)):
    _SPLIT_OPTIONS[_k] = re.compile(_SPLIT_OPTIONS[_k])
    _PARSE_OPTIONS[_k] = re.compile(_PARSE_OPTIONS[_k])

_YYDOY_MINIMUM  = '02001'


def _default_dates_from_basename(basename):
    """Extract up to three plausible dates from a file basename and return (family, list
    of dates in "yyyy-mm-dd" format); return (basename, []) on failure.
    """

    # Look for up to three embedded dates
    # Dictionary is keyed by the index into the string where the matched date appears.
    capture_by_index = {}
    family = basename
    for k, regex in enumerate(_SPLIT_OPTIONS):
        parts = regex.split(basename)
        for i in range(1, len(parts), 2):           # odd indices are the dates
            start = sum(len(p) for p in parts[:i])  # sum of lengths before this index

            # Create replacement tag
            match = _PARSE_OPTIONS[k].fullmatch(parts[i])
            vals = match.groupdict()
            ytag = len(vals['y']) * 'Y'
            mtag = '' if 'm' not in vals else 'MM' if len(vals['m']) == 2 else 'MON'
            dtag = 'DD' if len(vals['d']) == 2 else 'DOY'
            sep = vals['x']
            if match.group(1) == vals['y']:         # if year is first
                tag = ytag + sep + mtag + (sep if mtag else '') + dtag
            else:
                tag = dtag + sep + mtag + (sep if mtag else '') + ytag

            capture_by_index[start] = (parts[i], tag, vals, k)
                # index -> (date substring, tag, dictionary of date values, pattern index)

            # Replace date with tag in basename to avoid repeat captures, prepare family
            parts[i] = tag

        family = ''.join(parts)

    # We don't know how to interpret more than three dates
    if not capture_by_index or len(capture_by_index) > 3:
        return (basename, [])

    # Sort the dates into order of increasing index
    indices = list(capture_by_index.keys())
    indices.sort()
    captures = [capture_by_index[i] for i in indices]

    # We require special skepticism about YYDOY formats, because a five-digit version
    # number beginning with "00" or maybe "01" could be misinterpreted as a date.
    # (But two or three YYDOY dates inside the basename are OK.)
    yydoy_count = len([c for c in captures if c[1] == 'YYDOY'])
    if yydoy_count == 1:
        new_captures = []
        for capture in captures:
            if capture[1] == 'YYDOY' and capture[0] < _YYDOY_MINIMUM:
                continue
            new_captures.append(capture)

        captures = new_captures

    if not captures:
        return (basename, [])

    # Interpret each date
    dates = []
    for (_, _, vals, _) in captures:
        y = int(vals['y'])
        y = 2000 + y if y < 70 else 1900 + y if y < 100 else y
        d = int(vals['d'])
        if 'm' in vals:
            m = vals['m'].lower()
            m = _MON_DICT.get(m, m)
        else:
            (y, m, d) = julian.ymd_from_day(julian.day_from_yd(y, d))

        date = f'{y}-{m:02d}-{d:02}'
        dates.append(date)

    return (family, dates)


_V_PATTERN = re.compile(r'.*_v(\d+)\.\w+', re.I)        # must be last thing before dot
_VERSION_PATTERN = re.compile(r'.*_version(\d+).*', re.I)


def _default_version_from_basename(basename):
    """Extract a version number from a basename, indicated by "_v" or "_version" followed
    by an integer.

    Return (family, version number) on success; (basename, None) on failure.
    """

    for pattern in (_V_PATTERN, _VERSION_PATTERN):
        match = pattern.fullmatch(basename)
        if match:
            version = int(match.group(1))
            i = match.start(1)
            j = match.end(1)
            family = basename[:i] + (j-i) * 'N' + basename[j:]
            return (family, version)

    return (basename, None)

##########################################################################################
