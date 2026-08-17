##########################################################################################
# spyceman/rule.py
##########################################################################################
"""Class defining rules for extracting a release date, time range, version, and/or other
property information from a file basename.
"""

import julian
import re

from spyceman._ktypes import _EXTENSIONS
from spyceman._utils  import validate_iso_time, validate_version

##########################################################################################
# Tag support including remove_tags()
##########################################################################################

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


def _split_balanced_parens(string):
    r"""Split the given string into individual parts that alternate between being inside
    and outside balanced parentheses.

    Parameters:
        string (str): The string to split, typically a regular expression.

    Returns:
        list[str]: The alternating substrings. Parenthesized expressions occupy the
            odd-indexed locations, and each includes its enclosing parentheses. "\(" and
            "\)" are treated as literals, not parentheses.
    """

    parts = []
    chars = []
    depth = 0
    slashed = False
    for c in string:
        chars.append(c)
        if c == '\\':
            slashed = True
        elif slashed:
            slashed = False
        elif c == '(':
            if depth == 0:
                parts.append(''.join(chars[:-1]))
                chars = [c]
            depth += 1
        elif c == ')':
            if depth == 1:
                parts.append(''.join(chars))
                chars = []
            depth -= 1

    parts.append(''.join(chars))
    return parts


def _date_regex(tag):
    """The regular expression associated with this date tag.

    Parameters:
        tag (str): The interior of a date tag, e.g., "YYYYMMDD", "YY-DOY", or
            "DD_MON_YYYY".

    Returns:
        str: The regular expression matching dates in this format; an empty string if the
            tag is not a recognized date format.
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

    # Convert the tag to a regular expression. str.replace() returns a new string, so each
    # result has to be assigned. "YYYY" must be substituted before "YY", and "DOY" is
    # substituted after "DD" only because no tag contains both; none of the replacement
    # expressions contains a tag substring, so no substitution can be re-matched by a
    # later one.
    pattern = tag
    pattern = pattern.replace('YYYY', _YYYY)
    pattern = pattern.replace('YY',   _YY)
    pattern = pattern.replace('MM',   _MM)
    pattern = pattern.replace('MON',  _MON)
    pattern = pattern.replace('DD',   _DD)
    pattern = pattern.replace('DOY',  _DOY)

    return pattern


def _number_regex(tag):
    """The regular expression associated with this version number tag.

    Parameters:
        tag (str): The interior of a version tag: "N+" for a variable number of digits, or
            a run of "N" characters for that fixed number of digits.

    Returns:
        str: The regular expression matching version numbers in this format; an empty
            string if the tag is not a recognized version format.
    """

    if tag == 'N+':
        return r'\d+'

    if all(t == 'N' for t in tag):
        return tag.replace('N', r'\d')

    return ''


def _name_regex(tag):
    """The regular expression associated with this version name tag.

    Parameters:
        tag (str): The interior of a version name tag: "X+" for a variable number of
            characters, or a run of "X" characters for that fixed number.

    Returns:
        str: The regular expression matching version names in this format; an empty string
            if the tag is not a recognized version name format.
    """

    if tag == 'X+':
        return r'[a-zA-Z0-9](?:|[\w-]*[a-zA-Z0-9])'

    if not all(t == 'X' for t in tag):
        return ''

    if len(tag) == 1:
        return '[a-zA-Z0-9]'

    if len(tag) == 2:
        return '[a-zA-Z0-9]{2}'

    return r'[a-zA-Z0-9][\w-]{' + str(len(tag)-2) + '}[a-zA-Z0-9]'


def _count_capturing_groups(pattern):
    """The number of capturing groups inside a regular expression fragment.

    A group captures only if it is a plain "(...)" or a named "(?P<name>...)"; everything
    else beginning "(?" does not. Escaped parentheses and parentheses inside a character
    class are not groups at all.

    Parameters:
        pattern (str): A regular expression or fragment of one.

    Returns:
        int: The number of capturing groups it contains, at any depth.
    """

    count = 0
    slashed = False
    in_class = False
    for i, c in enumerate(pattern):
        if slashed:
            slashed = False
        elif c == '\\':
            slashed = True
        elif in_class:
            if c == ']':
                in_class = False
        elif c == '[':
            in_class = True
        elif c == '(':
            if pattern[i+1:i+2] != '?' or pattern[i+1:i+4] == '?P<':
                count += 1

    return count


def _interpret_tags(string):
    """Replace any rule tags ("YYDOY", "NNN", etc.) with their regular expressions.

    Parameters:
        string (str): A rule pattern, which may contain date, version number, and version
            name tags inside capturing parentheses.

    Returns:
        (str, list[(int, str)]): The pattern with every recognized tag replaced by its
            regular expression, followed by a list of (group index, tag) pairs sorted by
            group index.
    """

    # Update the pattern, replacing tags with their regular expressions
    # Track the location and type of each tag among the match patterns
    parts = _split_balanced_parens(string)
    new_parts = []
    tags = []

    group_index = 0
    for part in parts:

        # A part outside parentheses, or one whose group does not capture -- "(?:...)",
        # lookaround, comment, inline flags, conditional -- contributes only whatever
        # capturing groups are nested inside it. Counting the part as a whole, as an
        # earlier version did, both over-counted the non-capturing group and missed every
        # group nested within it.
        if not part.startswith('(') or (part.startswith('(?')
                                        and not part.startswith('(?P<')):
            new_parts.append(part)
            group_index += _count_capturing_groups(part)
            continue

        # Identify and translate tags
        interior = part[1:-1]
        for func in [_date_regex, _number_regex, _name_regex]:
            pattern = func(interior)
            if pattern:
                break

        if pattern:
            # A tag becomes exactly one capturing group: every expression substituted for
            # a tag is itself non-capturing.
            group_index += 1
            new_parts += ['(', pattern, ')']
            tags.append((group_index, interior))
        else:
            new_parts.append(part)
            group_index += _count_capturing_groups(part)

    pattern = ''.join(new_parts)
    tags.sort()

    return (pattern, tags)


def remove_tags(string):
    """Replace any rule tags ("YYDOY", "NNN", etc.) with their regular expressions.

    Parameters:
        string (str): A rule pattern, which may contain date, version number, and version
            name tags inside capturing parentheses.

    Returns:
        str: The pattern with every recognized tag replaced by its regular expression.
    """

    return _interpret_tags(string)[0]

##########################################################################################
# Rule class
##########################################################################################

class Rule:
    """Class defining one rule for how to interpret a SPICE file basename containing a
    release date, time range, version, and/or other property information.

    If the file basename matches a specified pattern, then::

        rule.match(basename)

    will return a dictionary containing the extracted information, keyed as follows:

    * `"release_date"`: If found, the identified release date in "YYYY-MM-DD" format.
    * `"time"`: If found, a tuple containing the start and stop times represented as
      seconds TDB.
    * `"version"`: If found, the version identification, identified by an integer, tuple
      of integers, or a string.
    * `"family"`: The family name, which identifies the file basename after the other
      information has been removed.
    If additional properties are defined by the basename, they will appear as additional
    keys in the dictionary.

    As each Rule is defined, it is saved in an internal dictionary. Use::

        Rule.apply_all(basename)

    to search the list of defined rules for the one that matches the basename, and then
    return the information extracted from it.
    """

    # _RULES is an internal dictionary of all rules, keyed by file extension (in lower
    # case) and then by the number of embedded fields, counting the time limits as two
    # and all properties employing a group as one. When matching basenames, the rules with
    # the larger number of fields are tested later, giving them higher precedence.

    # Each extension gets its own six lists. A dict.copy() of a shared template would be
    # shallow, leaving every extension pointing at one set of lists, so that a rule
    # registered for ".bsp" would also be tried against every ".bc" and ".tf" basename.
    # The "" key holds the rules whose extension cannot be inferred from the pattern.
    # A field count runs 0 to 5: at most three dates, plus one for a version and one for
    # the captured properties.
    _RULES = {ext: {count: [] for count in range(6)}
              for ext in list(_EXTENSIONS) + ['']}

    def __init__(self, pattern, family='', flags=re.I, *, datefirst=True, inclusive=True,
                 version=None, naif_ids=None, source=None, dest=None, **properties):
        """Constructor for a Rule.

        A rule describes how to read a release date, time range, version, family name,
        and arbitrary properties out of a kernel file basename. Each new Rule registers
        itself in an internal dictionary keyed by file extension and by the number of
        embedded fields it identifies; rules identifying more fields take precedence.

        Within the pattern, a component that encodes a release date or time limit is
        written as a tag inside capturing parentheses rather than as a regular
        expression. The recognized date tags are::

            "(YYYYMONDD)"   e.g., "2022Dec01"        "(DDMONYYYY)"   e.g., "01Dec2022"
            "(YYYY_MON_DD)" e.g., "2022_Dec_01"      "(DD_MON_YYYY)" e.g., "01_Dec_2022"
            "(YYYY-MON-DD)" e.g., "2022-Dec-01"      "(DD-MON-YYYY)" e.g., "01-Dec-2022"
            "(YYYYMMDD)"    e.g., "20221201"         "(DDMMYYYY)"    e.g., "01122022"
            "(YYYY_MM_DD)"  e.g., "2022_12_01"       "(DD_MM_YYYY)"  e.g., "01_12_2022"
            "(YYYY-MM-DD)"  e.g., "2022-12-01"       "(DD-MM-YYYY)"  e.g., "01-12-2022"
            "(YYMONDD)"     e.g., "22Dec01"          "(DDMONYY)"     e.g., "01Dec22"
            "(YY_MON_DD)"   e.g., "22_Dec_01"        "(DD_MON_YY)"   e.g., "01_Dec_22"
            "(YY-MON-DD)"   e.g., "22-Dec-01"        "(DD-MON-YY)"   e.g., "01-Dec-22"
            "(YYMMDD)"      e.g., "221201"           "(DDMMYY)"      e.g., "011222"
            "(YY_MM_DD)"    e.g., "22_12_01"         "(DD_MM_YY)"    e.g., "01_12_22"
            "(YY-MM-DD)"    e.g., "22-12-01"         "(DD-MM-YY)"    e.g., "01-12-22"
            "(YYYYDOY)"     e.g., "2022305"          "(YYDOY)"       e.g., "22305"
            "(YYYY_DOY)"    e.g., "2022_305"         "(YY_DOY)"      e.g., "22_305"
            "(YYYY-DOY)"    e.g., "2022-305"         "(YY-DOY)"      e.g., "22-305"

        One date tag identifies a release date; two identify a time range; three identify
        a release date plus a time range, ordered according to `datefirst`.

        An embedded version is written using one of these tags:

        * `"(NN)"`: An integer version of exactly two digits, and likewise for any other
          fixed number of "N" characters;
        * `"(N+)"`: An integer version of a variable number of digits;
        * `"(XX)"`: A version name of exactly two characters, and likewise for any other
          fixed number of "X" characters;
        * `"(X+)"`: A version name of a variable number of characters.

        A hierarchical version number is written as multiple "N" tags. For example, the
        basename "kernel_v10.2.3.ck" is matched by "kernel_v(N+).(N).(N).ck", returning
        the version as the tuple (10, 2, 3).

        A version, NAIF ID, or named property can also be located explicitly using a
        named capture "(?P<name>...)", where "name" is the attribute or property name.

        Parameters:
            pattern (str): A regular expression that might match a kernel file basename,
                using the date and version tags described above in place of the
                corresponding regular expressions.
            family (str, optional): The family name, or a replacement pattern containing
                backreferences such as "\\1" and "\\2". By default, the family name is the
                basename with each embedded field replaced by its tag.
            flags (RegexFlag, optional): Compile flags for the pattern; default is
                re.IGNORECASE.
            datefirst (bool, optional): For a pattern containing three dates, True if the
                release date precedes the start and stop times; False if it follows them.
            inclusive (bool, optional): True if the stop time includes the whole 24 hours
                of the second embedded date; False if that day is excluded.
            version (int, str, tuple, dict, function, optional): A literal version to
                assign to every file matching this pattern, which is useful when file
                names are inconsistent enough that different versions need different
                patterns. Alternatively, a dictionary or function used to transform the
                value captured by an "N" or "X" tag or by "(?P<version>...)"; see below.
            naif_ids (int, set, dict, function, optional): The NAIF IDs associated with a
                matching kernel. Alternatively, if "(?P<naif_ids>...)" appears in the
                pattern, a dictionary or function used to transform the captured value.
            source (str, list[str], optional): A URL, or list of URLs, of online
                directories that might contain a file matching this pattern.
            dest (str, optional): The local subdirectory in which a matching file should
                be stored when downloaded.
            **properties: Additional name/value pairs defining attributes or properties.
                A value that is a dictionary or function transforms the value captured by
                "(?P<name>...)"; any other value is assigned literally.

        Where `version`, `naif_ids`, or a named property is given as a function, the value
        used is the result of applying that function to the captured substring. Useful
        choices are `int` to convert the capture to an integer, and `str.upper` or
        `str.lower` to change its case.

        Where one of these is given as a dictionary, the captured substring is lower-cased
        and used as the key. If that key is absent from the dictionary, the associated
        attribute is left undefined.

        Raises:
            ValueError: If the pattern contains more than three date tags, more than one
                version tag, or a named property whose "(?P<name>...)" capture is missing;
                or if a dictionary or function is given for a version with no version tag.
        """

        # Identify the file extension; use "" if it cannot be inferred
        ext = '.' + pattern.rpartition('.')[-1].lower()
        if ext not in Rule._RULES:
            ext = ''

        # Update the pattern, replacing tags with their regular expressions
        # Track the location and type of each tag among the match patterns
        string, tags = _interpret_tags(pattern)
        self.regex = re.compile(string, flags=flags)
        self.pattern = self.regex.pattern

        # Organize the tags by category
        date_groups   = [tag for tag in tags if 'Y' in tag[1]]
        number_groups = [tag for tag in tags if tag[1][0] == 'N']
        name_groups   = [tag for tag in tags if tag[1][0] == 'X']

        # Identify the date and time groups
        if len(date_groups) > 3:
            raise ValueError('more than three embedded date tags: ' + repr(pattern))

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
            self._time_tags = []

        self._inclusive = bool(inclusive)

        # Identify an implicit or explicit version
        has_explicit_tag = '(?P<version>' in pattern
        count = len(name_groups) + bool(number_groups) + has_explicit_tag
        if count > 1:
                raise ValueError('duplicate version tags: ' + repr(pattern))

        if count == 0 and (isinstance(version, dict) or hasattr(version, '__call__')):
            raise ValueError('missing version tags: ' + repr(pattern))

        self._version = version
        if name_groups:
            self._version_type = 'str'
            self._version_groups = [name_groups[0][0]]
            self._version_tags = [name_groups[0][1]]
        elif number_groups:
            self._version_type = 'int'
            self._version_groups = [tag[0] for tag in number_groups]
            self._version_tags = [tag[1] for tag in number_groups]
        elif has_explicit_tag:
            self._version_type = 'str'
            self._version_groups = ['version']
            self._version_tags = []
        else:
            self._version = version and validate_version(version)
            self._version_type = 'literal'
            self._version_groups = []
            self._version_tags = []

        # Identify the family
        self._family = family

        # Save the additional properties plus naif_ids, source, dest
        if naif_ids is not None:
            properties['naif_ids'] = naif_ids
        if source:
            properties['source'] = source
        if dest:
            properties['dest'] = dest

        self._properties = properties
        self._captures = []
        for name, value in properties.items():
            if isinstance(value, (dict, type(None))) or hasattr(value, '__call__'):
                self._captures.append(name)
                if '(?P<' + name + '>' not in pattern:
                    raise ValueError(f'expression "(?P<{name}>" missing from pattern: '
                                     + repr(pattern))

        # Register in the global dictionary of rules
        field_count = len(date_groups) + bool(self._version_groups) + bool(self._captures)
        Rule._RULES[ext][field_count].append(self)

    def match(self, basename):
        """Return a dictionary of information about the given basename using this rule.

        Parameters:
            basename (str): The kernel file basename to match against this rule.

        Returns:
            dict: The name and value of each attribute or property this rule identifies in
                the basename, using the keys "release_date", "time", "version", and
                "family" plus any additional property names. The dictionary is empty if
                the rule does not match.
        """

        match = self.regex.fullmatch(basename)
        if not match:
            return {}

        results = {}

        # Handle release date
        if self._date_group:
            iso = Rule._date_iso(match.group(self._date_group), self._date_tag)
            results['release_date'] = iso

        # Handle time limits
        if self._time_groups:
            times = []
            for time_group, time_tag in zip(self._time_groups, self._time_tags):
                iso = Rule._date_iso(match.group(time_group), time_tag)
                times.append(validate_iso_time(iso))

            if self._inclusive:
                times[1] += 86400.

            results['time'] = tuple(times)

        # Handle version ID
        parts = [match.group(g) for g in self._version_groups]
        if len(parts) == 0:
            version = self._version
        elif len(parts) == 1:
            version = int(parts[0]) if self._version_type == 'int' else parts[0]
        else:
            version = tuple([int(p) for p in parts])

        if hasattr(self._version, '__call__'):
            version = self._version(version)
        elif isinstance(self._version, dict):
            version = version.lower() if isinstance(version, str) else version
            version = self._version.get(version, None)

        if version is not None:
            results['version'] = validate_version(version)

        # Create the family name
        if self._family:
            results['family'] = match.expand(self._family)
        else:
            groups = []
            tags = []
            if self._date_tag:
                groups = [self._date_group]
                tags = [self._date_tag]
            if self._time_tags:
                groups += self._time_groups
                tags += self._time_tags
            if self._version_tags:
                groups += self._version_groups
                tags += self._version_tags

            if tags:
                groups_and_tags = list(zip(groups, tags))   # list of (group, tag)
                groups_and_tags.sort(reverse=True)          # work backwards from the end!
                family = basename
                for (group, tag) in groups_and_tags:
                    i = match.start(group)
                    j = match.end(group)
                    family = family[:i] + tag + family[j:]

                results['family'] = family

        # Check for additional properties. A name in self._captures takes its value from
        # the named group; every other property has a literal value. The two cases are
        # kept apart so that a captured substring can never leak from one property to the
        # next, which is what happened when a single `capture` variable spanned both.
        for name, value in self._properties.items():
            if name not in self._captures:
                results[name] = value           # a literal value
                continue

            capture = match.group(name)
            if capture is None:                 # an optional group that did not match
                continue

            if value is None:                   # capture it verbatim
                results[name] = capture
            elif isinstance(value, dict):       # look the capture up, case-insensitively
                key = capture.lower()
                if key in value:
                    results[name] = value[key]
            else:                               # transform it through the given function
                test = value(capture)
                if test is not None:
                    results[name] = test

        return results

    @staticmethod
    def apply_all(basename):
        """Extract the rule-based info from a SPICE kernel basename that matches any of
        the defined rules.

        Rules are applied in order of increasing field count, so a rule that identifies
        more embedded fields overrides one that identifies fewer.

        Parameters:
            basename (str): The kernel file basename to interpret.

        Returns:
            dict: The merged results of every rule that matches this basename. The
                dictionary is empty if no rule matches.
        """

        ext = '.' + basename.rpartition('.')[-1].lower()
        if ext in Rule._RULES:
            key_list = ('', ext)
        else:
            key_list = ('',)    # note the comma: ('') is the empty string, not a tuple

        results = {}
        for fields in range(6):
            for key in key_list:
                for rule in Rule._RULES[key][fields]:
                    results.update(rule.match(basename))

        return results

    @staticmethod
    def _date_iso(string, tag):
        """The matched date string in "yyyy-mm-dd" format.

        A two-digit year is interpreted as 20xx, except that a value implying a year of
        2070 or later is shifted back one century.

        Parameters:
            string (str): The substring captured by a date tag.
            tag (str): The date tag that captured it, e.g., "YYYYMMDD" or "YY-DOY",
                used to locate each date component within the string.

        Returns:
            str: The date as "yyyy-mm-dd".
        """

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
            return julian.format_day(day)
        elif 'MON' in tag:
            i = tag.index('MON')
            mm = _MON_DICT[string[i:i+3].lower()]
        else:
            i = tag.index('MM')
            mm = string[i:i+2]

        i = tag.index('DD')
        dd = int(string[i:i+2])
        return f'{year:04d}-{mm}-{dd:02d}'

##########################################################################################
# Default rule support
##########################################################################################

class _DefaultRule:
    """Instance-free class defining the default rule for matching basenames."""

    def apply(basename):
        """Extract release date, time range, version, and family from a basename.

        This is the fallback applied when no explicit Rule matches, and it recognizes
        dates and "_v"/"_version" numbers embedded in the name.

        Parameters:
            basename (str): The kernel file basename to interpret.

        Returns:
            dict: Any of the keys "date", "time", "version", and "family" that could be
            derived from the basename. The dictionary is empty if none could be.
        """

        results = {}

        (family, dates) = _default_dates_from_basename(basename)
        if len(dates) in (1,3):
            results['release_date'] = dates[0]
        if len(dates) in (2,3):
            results['time'] = (validate_iso_time(dates[-2]),
                               validate_iso_time(dates[-1]))

        # Chain from the date-tagged family rather than restarting from the basename, so
        # that a name carrying both a date and a version keeps a tag for each.
        (family, version) = _default_version_from_basename(family)
        if version is not None:
            results['version'] = version

        if family != basename:
            results['family'] = family

        return results


_MON_MM  = '(?:' + _MON  + '|' + _MM + ')'
_YYYY_YY = '(?:' + _YYYY + '|' + _YY + ')'

_SEP = '(?:|_|-)'

_SPLIT_OPTIONS = [
    r'(?<!\d)(' + _YYYY_YY + _SEP + _MON_MM + _SEP + _DD      + r')(?!\d)',
    r'(?<!\d)(' + _DD      + _SEP + _MON_MM + _SEP + _YYYY_YY + r')(?!\d)',
    r'(?<!\d)(' + _YYYY_YY + _SEP + _DOY    +                   r')(?!\d)',
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

    A basename containing more than three dates is rejected, because there is no way to
    tell which is the release date and which are the time limits. A lone YYDOY-format date
    below "02001" is also rejected, on the grounds that it is more likely a five-digit
    version number.

    Parameters:
        basename (str): The kernel file basename to interpret.

    Returns:
        (str, list[str]): The family name, formed by replacing each date with its tag, and
            the list of dates in "yyyy-mm-dd" format, ordered by their position in the
            basename. On failure, the basename itself and an empty list.
    """

    # Look for up to three embedded dates
    # Dictionary is keyed by the index into the string where the matched date appears.
    capture_by_index = {}
    for k, regex in enumerate(_SPLIT_OPTIONS):
        parts = regex.split(basename)
        for i in range(1, len(parts), 2):           # odd indices are the dates
            start = sum(len(p) for p in parts[:i])  # sum of lengths before this index

            # Create replacement tag. The split patterns allow a date's two separators to
            # differ but the parse patterns require them to match, so a substring such as
            # "2022-12_01" splits and then fails to parse. Skip what cannot be parsed.
            match = _PARSE_OPTIONS[k].fullmatch(parts[i])
            if match is None:
                continue

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

    # Note that every split option is applied to the original basename, so the captures
    # are keyed by an index that means the same thing across all three. The family name is
    # built once, from the surviving captures, after the filtering below; building it
    # inside the loop would keep only the last option's replacements.

    # We don't know how to interpret more than three dates
    if not capture_by_index or len(capture_by_index) > 3:
        return (basename, [])

    # Sort the dates into order of increasing index
    indices = list(capture_by_index.keys())
    indices.sort()
    captures = [capture_by_index[i] for i in indices]

    # We require special skepticism about YYDOY formats, because a five-digit version
    # number beginning with "00" or maybe "01" could be misinterpreted as a date. (But two
    # or three YYDOY dates inside the basename are OK.)
    yydoy_count = len([c for c in captures if c[1] == 'YYDOY'])
    if yydoy_count == 1:
        keep = [(i, c) for i, c in zip(indices, captures)
                if not (c[1] == 'YYDOY' and c[0] < _YYDOY_MINIMUM)]
    else:
        keep = list(zip(indices, captures))

    if not keep:
        return (basename, [])

    captures = [c for _, c in keep]

    # Build the family name by replacing each surviving date with its tag. Work from the
    # end of the basename backwards so that the earlier indices stay valid.
    family = basename
    for start, capture in sorted(keep, key=lambda kc: kc[0], reverse=True):
        text, tag = capture[0], capture[1]
        family = family[:start] + tag + family[start + len(text):]

    # Interpret each date
    dates = []
    for (_, _, vals, _) in captures:
        y = int(vals['y'])
        y = 2000 + y if y < 70 else 1900 + y if y < 100 else y
        d = int(vals['d'])
        if 'm' in vals:
            m = vals['m'].lower()
            m = int(_MON_DICT.get(m, m))    # "dec" -> "12" -> 12, and "12" -> 12
        else:
            (y, m, d) = julian.ymd_from_day(julian.day_from_yd(y, d))

        date = f'{y:04d}-{m:02d}-{d:02d}'
        dates.append(date)

    return (family, dates)


_V_PATTERN = re.compile(r'.*_v(\d+)\.\w+', re.I)        # must be last thing before dot
_VERSION_PATTERN = re.compile(r'.*_version(\d+).*', re.I)


def _default_version_from_basename(basename):
    """Extract a version number from a basename, indicated by "_v" or "_version" followed
    by an integer.

    Parameters:
        basename (str): The kernel file basename to interpret.

    Returns:
        (str, int), (str, None): The family name, formed by replacing the digits of the
            version with an equal number of "N" characters, and the version number. On
            failure, the basename itself and None.
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
