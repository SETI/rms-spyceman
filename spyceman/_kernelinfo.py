##########################################################################################
# kernel/_kernelinfo.py
##########################################################################################
"""_KernelInfo class to hold attributes of SPICE kernel files."""

import datetime
import numbers
import numpy as np
import os
import re

import cspyce
import cspyce.aliases
import julian
import textkernel

from spyceman.rule    import Rule, _DefaultRule
from spyceman._ktypes import _EXTENSIONS


class _KernelInfo(object):

    ABSPATHS = {}               # basename -> abspath
    BASENAMES_BY_KTYPE = {}     # ktype -> set of associated basenames
    KERNELINFO = {}             # basename -> unique _KernelInfo object

    # Configuration attributes for how to use information from rules
    _USE_RULES           = True
    _USE_DEFAULT_RULES   = True
    _USE_INTERNAL_DATES  = True
    _USE_TIMESTAMP_DATES = True

    def __init__(self, basename):

        if basename in _KernelInfo.KERNELINFO:
            raise ValueError('_KernelInfo already defined for ' + basename)

        self._basename = basename
        self._ext = _KernelInfo.basename_ext(basename)
        self._ktype = _EXTENSIONS.get(self._ext.lower(), '')
        if not self._ktype:
            raise ValueError('invalid kernel file extension: ' + repr(basename))

        # These attributes are filled in lazily as needed
        self._label_abspath = None
        self._label = None
        self._comments = None
        self._text = None
        self._text_content = None
        self._text_comments = None
        self._dict_content = None

        self._naif_ids = None
        self._naif_ids_without_aliases = None
        self._time = None
        self._release_date = None
        self._version = None
        self._family = None

        # Special support for metakernels
        self._meta_basenames = None

        # Info derived via basename rules
        self.__rule_values = None
        self.__default_values = None
        self._properties = None

        # Track manual definitions for cases where an abspath changes
        self._manual_defs = []

        _KernelInfo.KERNELINFO[basename] = self

    @staticmethod
    def lookup(basename):
        """A _KernelInfo object for this basename, constructed anew if necessary."""

        try:
            return _KernelInfo.KERNELINFO[basename]
        except KeyError:
            return _KernelInfo(basename)

    def __str__(self):
        return '_KernelInfo("' + self._basename + '")'

    def __repr__(self):
        return self.__str__()

    @property
    def _rule_values(self):
        """Rule values as a dictionary."""

        if self.__rule_values is None:
            self.__rule_values = Rule.apply(self._basename)
            if not _KernelInfo._USE_RULES:
                for key in ('date', 'time', 'version', 'family'):
                    if key in self.__rule_values:
                        del self.__rule_values[key]

        return self.__rule_values

    @property
    def _default_values(self):
        """Default rule values as a dictionary."""

        if self.__default_values is None:
            if _KernelInfo._USE_DEFAULT_RULES:
                self.__default_values = _DefaultRule.apply(self._basename)
            else:
                self.__default_values = {}

        return self.__default_values

    @property
    def abspath(self):
        """Absolute path to this kernel file; an empty string if this file doesn't exist.
        """
        return _KernelInfo.ABSPATHS.get(self._basename, '')

    @property
    def exists(self):
        """True if this kernel file exists."""
        return self._basename in _KernelInfo.ABSPATHS

    @property
    def ext(self):
        """The file extension, after the period."""
        return self._ext

    @property
    def ktype(self):
        """Kernel type of this file: "SPK", "CK", "LSK", etc."""
        return self._ktype

    @property
    def is_text(self):
        """True if this is a text kernel file."""
        return self._ext[1] == 't'

    @property
    def is_binary(self):
        """True if this is a binary kernel file."""
        return self._ext[1] == 'b'

    @property
    def label_abspath(self):
        """Absolute path to a label file, if any; blank otherwise."""

        if self._label_abspath is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            (kernel_path, ext) = os.path.splitext(self.abspath)
            for label_ext in ('.lbl', ext + '.lbl'):
                label_path = kernel_path + label_ext
                if os.path.exists(label_path):
                    self._label_abspath = label_path
                    return label_path

            self._label_abspath = ''

        return self._label_abspath

    @property
    def label(self):
        """Content of the PDS label, if any, as a list of strings."""

        if self._label is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            if self.label_abspath:
                with open(self.label_abspath, 'r', encoding='latin8') as f:
                    self._label = f.readlines()
            else:
                self._label = []

        return self._label

    @property
    def comments(self):
        """Any available comments as a list of strings."""

        if self._comments is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            # First look for a comment file
            (kernel_path, ext) = os.path.splitext(self.abspath)
            for comment_ext in ('.cmt', ext + '.cmt'):
                comment_path = kernel_path + comment_ext
                if os.path.exists(comment_path):
                    with open(comment_path, encoding='latin8') as f:
                        self._comments = f.readlines()
                        return self._comments

            # For a binary kernel, look inside the file
            if self.is_binary:
                try:
                    with open(self.abspath, encoding='latin8') as f:
                        buffer = f.read(20)
                    spice_type = buffer.split('/')[0]
                    if spice_type in ('DAF', 'DAS', 'NAIF'):
                        try:
                            cspyce.furnsh(self.abspath)
                            handle = cspyce.kinfo(self.abspath)[-1]
                            if spice_type == 'DAF':
                                self._comments = cspyce.dafec(handle)
                            else:
                                self._comments = cspyce.dasec(handle)
                        finally:
                            cspyce.unload(self.abspath)

                        if self._comments is None:
                            self._comments = []

                except Exception:
                    self._comments = []

            # For a text kernel, the comments are content with the data stripped
            else:
                self._comments = self.text_comments

        return self._comments

    @property
    def text(self):
        """Content of a text kernel as a list of strings; an empty list for a binary
        kernel.
        """

        if self._text is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            if self.is_text:
                with open(self.abspath, 'r', encoding='latin8') as f:
                    self._text = f.readlines()
            else:
                self._text = []

        return self._text

    @property
    def text_content(self):
        """Data content of a text kernel as a list of strings; an empty list for a binary
        kernel.
        """

        if self._text_content is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            # Split the content into
            comment_recs = []
            content_recs = []
            is_comment = True
            for rec in self.text:
                rec_lc = rec.lower()
                if r'\begindata' in rec_lc:
                    is_comment = False
                elif r'\begintext' in rec_lc:
                    is_comment = True
                    comment_recs.append(rec)
                elif is_comment:
                    comment_recs.append(rec)
                else:
                    content_recs.append(rec)

            self._text_content = content_recs
            self._text_comments = comment_recs

        return self._text_content

    @property
    def text_comments(self):
        """All comments embedded within a text kernel as a list of strings; an empty list
        for a binary kernel.
        """

        if self._text_comments is None:
            _ = self.text_content       # this fills in both

        return self._text_comments

    @property
    def dict_content(self):
        """Content of this text kernel as parsed into a dictionary."""

        if self._dict_content is None:
            if not self.abspath:
                raise ValueError('kernel file does not exist: ' + repr(self._basename))

            content = self.text_content
            if content:
                self._dict_content = textkernel.from_text(content)
            else:
                self._dict_content = {}

        return self._dict_content

    ######################################################################################
    # NAIF IDs
    ######################################################################################

    @property
    def naif_ids(self):
        """The set of all NAIF IDs, including aliases, described by the file.

        If this kernel applies to all NAIF IDs, return an empty set.
        """

        if self._naif_ids is not None:
            return self._naif_ids

        # LSKs are applicable to all NAIF IDs
        if self.ktype == 'LSK':
            self._naif_ids = set()
            return self._naif_ids

        # In any other case, file access is needed
        if not self.abspath:
            raise ValueError('kernel file does not exist: ' + repr(self._basename))

        if self.ktype == 'SPK':
            naif_ids = {int(k) for k in cspyce.spkobj(self.abspath)}
                # use int() because cspyce.spkobj returns values as an array of int32

        elif self.ktype == 'CK':
            naif_ids = {int(k) for k in cspyce.ckobj(self.abspath)}
                # use int() because cspyce.spkobj returns values as an array of int32

        elif self.ktype == 'META':
            naif_ids = set()
            for basename in self.meta_basenames:
                if basename not in _KernelInfo.ABSPATHS:
                    raise FileNotFoundError('file referenced in metakernel '
                                            f'{self._basename} not found: ' + basename)
                naif_ids |= _KernelInfo.KERNELINFO[basename].naif_ids

        elif self.is_text:              # any text kernel
            naif_ids = self._naif_ids_from_text_kernel()
            if not naif_ids:
                naif_ids = {0}

        else:                           # some weird binary kernel
            naif_ids = set()
            tmin =  np.inf
            tmax = -np.inf

            # This is based on the SPACIT code SPKGSS and SUMPCK
            handle = cspyce.dafopr(self.abspath)            # open the file
            cspyce.dafbfs(handle)                           # begin forward search
            while cspyce.daffna():                          # for each array in DAF...
                _ = cspyce.dafgn()                          # read array name
                summary = cspyce.dafgs()                    # get summary record
                floats, ints = cspyce.dafus(summary, 2, 5)  # unpack into floats & ints

                # Get the info we care about
                tmin = min(floats[0], tmin)
                tmax = max(floats[1], tmax)

                body  = ints[0]
                frame = ints[1]
                naif_ids |= {int(body), int(frame)}

            cspyce.dafcls(handle)

            self._time = (tmin, tmax)   # also define the time limits

        self._naif_ids_without_aliases = naif_ids
        self._naif_ids = _KernelInfo._all_id_aliases(naif_ids)
        return self._naif_ids

    @naif_ids.setter
    def naif_ids(self, ids):
        """Define the set of NAIF IDs for this object."""

        if isinstance(ids, numbers.Integral):
            self._naif_ids = {ids}
        elif not ids:
            self._naif_ids = set()
        else:
            self._naif_ids = set(ids)

        self._naif_ids = _KernelInfo._all_id_aliases(self._naif_ids)
        self._manual_defs.append(('_naif_ids', self._naif_ids))

    def add_naif_ids(self, *ids):
        """Add one or more NAIF IDs to the set."""

        ids = _KernelInfo._all_id_aliases(ids)

        if self._naif_ids is None:
            self._naif_ids = ids
        else:
            self._naif_ids |= ids

        self._manual_defs.append(('add_naif_ids', *ids))

    def remove_naif_ids(self, *ids):
        """Remove one or more NAIF IDs from the set."""

        ids = _KernelInfo._all_id_aliases(ids)

        if self._naif_ids is None:
            return

        self._naif_ids -= ids
        self._manual_defs.append(('remove_naif_ids', *ids))

    @property
    def naif_ids_without_aliases(self):
        """The set of all NAIF IDs described by the file, excluding aliases."""

        if self._naif_ids_without_aliases is None:
            _ = self.naif_ids

        return self._naif_ids_without_aliases

    _BODY_FRAME_INS = re.compile(r' *(?:FRAME|BODY|INS)_?(-?\d+)_', re.I)
    _SCLK_DATA_TYPE = re.compile(r' *SCLK_DATA_TYPE_(\d+)', re.I)

    def _naif_ids_from_text_kernel(self):
        """Internal method to extract the set of NAIF IDs from any text kernel."""

        naif_ids = set()

        # It is very slow to parse a text kernel, but we can use the info if a content
        # dictionary was already created.
        if self._dict_content:
            for key in ('BODY', 'FRAME', 'NAIF_BODY_CODE'):
                if key in self.dict_content:
                    item = self.dict_content[key]
                    if isinstance(item, dict):
                        ids = set(self.dict_content[key].keys())
                    else:
                        ids = self.dict_content[key]
                        if isinstance(ids, numbers.Integral):
                            ids = {ids}
                        else:
                            ids = set(ids)
                    naif_ids |= {i for i in ids
                                 if isinstance(i, numbers.Integral)}

            # SCLKs require special handling
            if self.ktype == 'SCLK':
                for key, value in self.dict_content.items():
                    parts = key.split('SCLK_DATA_TYPE_')
                    if len(parts) == 2:
                        naif_ids.add(-int(parts[1]))

            return naif_ids

        # We save a LOT of time by avoiding pyparsing. This is a brute-force approach

        # Search for IDs in the text
        for rec in self.text_content:
            match = _KernelInfo._BODY_FRAME_INS.match(rec)
            if match:
                naif_ids.add(int(match.group(1)))
            match = _KernelInfo._SCLK_DATA_TYPE.match(rec)
            if match:
                naif_ids.add(-int(match.group(1)))

        return naif_ids

    @staticmethod
    def _all_id_aliases(ids):

        all_ids = set(ids)
        for naif_id in ids:
            all_ids |= set(cspyce.get_body_aliases(naif_id)[0])

            # Insert the spacecraft ID for any spacecraft frame ID
            if naif_id < -1000:
                all_ids.add(-(-naif_id//1000))

        # Include body IDs for frame IDs, but not the other way around
        if any(i for i in all_ids if i >= 10000 and i < 50000):
            for naif_id in ids:
                all_ids |= set(cspyce.get_frame_aliases(naif_id)[0])

        return all_ids

    ######################################################################################
    # Time range
    ######################################################################################

    @property
    def time(self):
        """Time limits as a tuple of two times in seconds TDB.

        The kernel might have gaps in time coverage, but it must not have any
        applicability before the earliest time or after the latest.

        For kernels with no time dependence, the interval Kernel.ALL_TIME is returned.
        """

        if self._time is not None:
            return self._time

        # LSKs, DSKs, SCLKs, and text-based PCKs are applicable to all times
        if self.ktype in ('LSK', 'DSK', 'SCLK') or self._ext.lower() == '.tpc':
            self._time = (None, None)
            return self._time

        # In any other case, file access is needed
        if not self.abspath:
            raise ValueError('kernel file does not exist: ' + repr(self._basename))

        # Extract times from the basename
        time = (None, None)
        if 'time' in self._rule_values:
            time = self._rule_values['time']
        elif time in self._default_values:
            time = self._default_values['time']

        if time[0] is not None:
            self._time = time
            return self._time

        # Initialize to an impossible range of times
        tmin =  np.inf
        tmax = -np.inf

        # Handle SPK
        if self.ktype == 'SPK':
            for naif_id in self.naif_ids_without_aliases:
                for (t0, t1) in cspyce.spkcov(self.abspath, naif_id):
                    tmin = min(tmin, t0)
                    tmax = max(tmax, t1)

            self._time = (tmin, tmax)

        # Handle CK
        elif self.ktype == 'CK':

            # Note that this only works if a SCLK has been furnished!
            for naif_id in self.naif_ids_without_aliases:
                try:
                    times = cspyce.ckcov(self.abspath, naif_id, needav=False,
                                         level='INTERVAL', tol=0., timsys='TDB')
                    for (t0, t1) in times:
                        tmin = min(tmin, t0)
                        tmax = max(tmax, t1)

                except KeyError:
                    raise RuntimeError('Unable to determine time limits for '
                                       + self._basename
                                       + '; clock kernel must be furnishded for ID '
                                       + str(naif_id))

            self._time = (tmin, tmax)

        # For other binary kernels, the time limits are filled in as a side-effect of
        # checking the NAIF IDs
        elif self.is_binary:
            _ = self.naif_ids

        # The time limits of metakernels depend on the time limits of the referenced files
        elif self.ktype == 'META':
            tmins = []
            tmaxes = []
            for basename in self.meta_basenames:
                time = _KernelInfo(basename).time
                if time[0] is not None:
                    tmins.append(time[0])
                    tmaxes.append(time[1])
            if tmins:
                self._time = (min(tmins), max(tmaxes))
            else:
                self._time = (None, None)

        # Otherwise, assume no time-dependence
        else:
            self._time = (None, None)

        return self._time

    @time.setter
    def time(self, tmin_tmax):
        """Define the time range of this kernel file.

        Dates can be specified by ISO-format string or number of seconds TDB.
        """

        (tmin, tmax) = tmin_tmax

        if isinstance(tmin, str):
            tmin = julian.tdb_from_iso(tmin)

        if isinstance(tmax, str):
            tmax = julian.tdb_from_iso(tmax)

        self._time = (tmin, tmax)
        self._manual_defs.append(('_time', self._time))

    ######################################################################################
    # Release date
    ######################################################################################

    _JANUARY_1995 = julian.day_from_yd(1995, 1)

    # Match for lines that contain some other kind of date, not a release date
    _IGNORE1 = re.compile(r'.*((BEGIN|END|START|STOP)[_ ]TIME|Timespan)', re.I)

    # Ignore textkernel dates, which always begin with "@"
    _IGNORE2 = re.compile(r'@\d\d\d\d-.*', re.I)

    @property
    def release_date(self):
        """Release date as an ISO date string "yyyy-mm-dd"; empty string if unavailable.
        """

        if self._release_date is not None:
            return self._release_date

        # File access is needed
        if not self.abspath:
            raise ValueError('kernel file does not exist: ' + repr(self._basename))

        # 1. Check the file basename rules without defaults
        if 'date' in self._rule_values:
            self._release_date = self._rule_values['date']
            return self._release_date

        # 2. Check the most reliable internal comment fields
        daylist = []
        for rec in self.comments + self.label:
            for match_pattern in ('SATEPHMERGE', 'SATMERGE', 'SATGEN', 'Release to',
                                  '; Created ', 'Run Date:', 'CREATION_TIME'):
                if match_pattern in rec:
                    daylist += julian.days_in_strings(rec)

        daylist = [d for d in daylist if d > _KernelInfo._JANUARY_1995]
        if daylist:
            self._release_date = julian.format_day(min(daylist))
            return self._release_date

        # 3. This appears to work reliably in SLCKs
        if self.ktype == 'SCLK':
            daylist = []
            for rec in self.text_content:
                if 'SCLK_KERNEL_ID' in rec.upper():
                    daylist = julian.days_in_strings(rec)
                    if daylist:
                        self._release_date = julian.format_day(daylist[0])
                        return self._release_date

        # 4. Check the file basename rules with defaults allowed
        if 'date' in self._default_values:
            self._release_date = self._default_values['date']
            return self._release_date

        # 5. Search for the latest internal date not defining time limits
        if _KernelInfo._USE_INTERNAL_DATES:
            daylist = []
            for source in (self.label, self.comments):
                for rec in source:
                    if _KernelInfo._IGNORE1.match(rec):
                        continue
                    if _KernelInfo._IGNORE2.match(rec):
                        continue
                    daylist += julian.days_in_strings(rec)
                if daylist:
                    break

            # ... but omit dates later than the file timestamp
            timestamp = min(os.path.getmtime(self.abspath),
                            os.path.getctime(self.abspath))
            timestamp_date = datetime.date.fromtimestamp(timestamp)
            timestamp_day = julian.day_from_ymd(timestamp_date.year,
                                                timestamp_date.month,
                                                timestamp_date.day)

            daylist = [d for d in daylist if d <= timestamp_day]
            if daylist:
                self._release_date = julian.format_day(max(daylist))
                return self._release_date

        # 6. Use the file timestamp
        if _KernelInfo._USE_TIMESTAMP_DATES:
            self._release_date = datetime.date.isoformat(timestamp_date)
            return self._release_date

        return ''

    @property
    def _validate_release_date(date):
        """Format the given release date properly."""

        if date:
            (day, _) = julian.day_sec_from_string(date)
            self._release_date = julian.format_day(day)
        else:
            return ''

    @release_date.setter
    def release_date(self, date):
        """Define the release date for this kernel file."""

        self._release_date = _KernelInfo._validate_release_date(date)
        self._manual_defs.append(('_release_date', self._release_date))

    ######################################################################################
    # Family and version
    ######################################################################################

    @property
    def version(self):
        """Version of this kernel file as a string, integer, or tuple of integers; "" if
        unavailable.
        """

        if self._version is not None:
            return self._version

        if 'version' in self._rule_values:
            self._version = self._rule_values['version']
        elif 'version' in self._default_values:
            self._version = self._default_values['version']
        else:
            self._version = self.release_date

        return self._version

    @staticmethod
    def _validate_version(version):

        if version is None:
            return ''

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
            return pass
        else:
            return _KernelInfo._validate_version(test)

        return version

    @version.setter
    def version(self, value):
        self._version = _KernelInfo._validate_version(value)
        self._manual_defs.append(('_version', self._version))

    @property
    def family(self):
        """Family name applicable to this kernel file; "" if unavailable."""

        if self._family is not None:
            return self._family

        if 'family' in self._rule_values:
            self._family = self._rule_values['family']
        elif 'family' in self._default_values:
            self._family = self._default_values['family']
        else:
            self._family = ''

        return self._family

    @family.setter
    def family(self, value):
        if value is None:
            value = ''

        self._family = str(value)
        self._manual_defs.append(('_family', self._family))

    ######################################################################################
    # Custom properties
    ######################################################################################

    @property
    def properties(self):
        """The dictionary of special properties for this kernel file."""

        if self._properties is None:
            properties = self._rule_values.copy()
            for key in ('date', 'time', 'version', 'family'):
                if key in properties:
                    del properties[key]

            self._properties = properties

        return self._properties

    ######################################################################################
    # Metakernel support
    ######################################################################################

    @property
    def meta_basenames(self):
        """The list of enclosed basenames if this is a metakernel; an empty list
        otherwise.
        """

        if self._meta_basenames is None:
            if self.ktype == 'META':
                basenames = []
                for filepath in self.dict_content['KERNELS_TO_LOAD']:
                    basename = os.path.basename(filepath)
                    basenames.append(basename)
                self._meta_basenames = basenames
            else:
                self._meta_basenames = []

        return self._meta_basenames

    ######################################################################################
    # Utilities
    ######################################################################################

    # Regular expression that matches any standard file basename
    ext_regex = '(' + '|'.join(ext[1:] for ext in _EXTENSIONS) + ')'
    BASENAME_REGEX = re.compile(r'[\w.-]+\.' + ext_regex + '$', re.I)

    @staticmethod
    def is_basename(basename):
        """True if this string appears to be a valid kernel file basename."""

        return (isinstance(basename, str)
                and bool(_KernelInfo.BASENAME_REGEX.match(basename))

    @staticmethod
    def basename_ext(basename):
        """The extension of this basename or regular expression."""

        if isinstance(basename, re.Pattern):
            basename = basename.pattern

        ext = basename.rpartition('.')[-1]
        return '.' + ext

    @staticmethod
    def basename_ktype(basename):
        """The ktype of this basename or regular expression; an empty string if unknown.
        """

        ext = _KernelInfo.basename_ext(basename).lower()
        return _EXTENSIONS.get(ext, '')

    @staticmethod
    def match(pattern, flags=re.I):
        """The set of existing basenames that match the given regular expression.

        Input:
            pattern     regular expression as a string or re.Pattern object.
            flags       compile flags to use if the pattern is a string.
        """

        if isinstance(pattern, str):
            pattern = re.compile(pattern, flags=flags)

        basenames = {b for b in _KernelInfo.ABSPATHS if pattern.match(b)}

##########################################################################################
