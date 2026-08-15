##########################################################################################
# spyceman/_kernelinfo.py
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
from spyceman._ktypes import _EXTENSIONS, _KTYPES
from spyceman._utils  import validate_release_date, validate_version, validate_naif_ids, \
                             naif_ids_with_aliases, naif_ids_wo_aliases


class _KernelInfo(object):

    ABSPATHS = {}               # basename -> abspath
    KERNELINFO = {}             # basename -> unique _KernelInfo object
    BASENAMES_BY_KTYPE = {}     # ktype -> set of associated, known basenames
    for ktype in _KTYPES:
        BASENAMES_BY_KTYPE[ktype] = set()

    # Configuration attributes for how to use information from rules;
    # mainly for debugging but also used by summarizer.py.
    _USE_RULES           = True
    _USE_DEFAULT_RULES   = True
    _USE_INTERNAL_DATES  = True
    _USE_TIMESTAMP_DATES = True

    def __init__(self, basename):
        """Constructor for a _KernelInfo object.

        Parameters:
            basename (str): The basename of a kernel file.
        """

        if basename in _KernelInfo.KERNELINFO:
            raise ValueError('_KernelInfo already defined for ' + basename)

        self._basename = basename
        self._ext = '.' + basename.rpartition('.')[-1]
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
        self._naif_ids_wo_aliases = None
        self._naif_ids_as_found = None
        self._time = None
        self._release_date = None
        self._version = None
        self._family = None
        self._source = None
        self._dest = None

        # Special support for metakernels
        self._meta_basenames = None

        # Info derived via basename rules
        self.__rule_values = None
        self.__default_values = None
        self._rule_properties = None
        self._properties = None

        # Track manual definitions for cases where an abspath changes
        self._manual_defs = []

        _KernelInfo.KERNELINFO[basename] = self
        _KernelInfo.BASENAMES_BY_KTYPE[self._ktype].add(self._basename)

    @staticmethod
    def lookup(basename):
        """The unique _KernelInfo object for this basename.

        Parameters:
            basename (str): The basename of a kernel file.

        Return:
            _KernelInfo:
                The unique _KernelInfo object associated with this basename, constructed
                anew if it does not already exist.
        """

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
        """The rule values for with this _KernelInfo object.

        Return:
            dict:
                The dictionary keyed by property name, returning each rule-defined
                property value associated with this object.
        """

        if self.__rule_values is None:
            self.__rule_values = Rule.apply_all(self._basename)

        return self.__rule_values

    @property
    def _default_values(self):
        """The default rule values for with this _KernelInfo object.

        Return:
            dict:
                The dictionary keyed by property name, returning each default property
                value associated with this object.
        """

        if self.__default_values is None:
            if _KernelInfo._USE_DEFAULT_RULES:
                self.__default_values = _DefaultRule.apply(self._basename)
            else:
                self.__default_values = {}

        return self.__default_values

    @property
    def abspath(self):
        """Absolute path to this kernel file.

        If the file does not exist on the local filesystem, an empty string is returned.

        Return:
            str:
                The absolute path on the local filesystem to this kernel file, or an empty
                string if there is no local copy of this kernel file.
        """
        return _KernelInfo.ABSPATHS.get(self._basename, '')

    @property
    def exists(self):
        """True if this kernel file exists on the local filesystem.

        Return:
            bool: True if this kernel file exists on the local filesystem.
        """
        return self._basename in _KernelInfo.ABSPATHS

    @property
    def is_known(self):
        """True if information about this kernel file basename has been defined.

        A basename is defined if any information about it has been registered, even if
        there is no local copy on the filesystem.

        Return:
            bool: True if information about this kernel file basename has been defined.
        """
        return self._basename in _KernelInfo.KERNELINFO

    @property
    def ext(self):
        """The file extension from the basename of the file described by this _KernelInfo
        object.

        The period is included as the first character.

        Return:
            str:
                The file extension from the basename of the file described by this object,
                starting with the period.
        """
        return self._ext

    @property
    def ktype(self):
        """The kernel type of the file described by this _KernelInfo object: "SPK", "CK",
        "LSK", etc.

        Return:
            str: The kernel type of this object: "SPK", "CK", "LSK", etc.
        """
        return self._ktype

    @property
    def is_text(self):
        """True if this _KernelInfo object describes a text kernel file; False if it
        describes a binary kernel file.

        Return:
            bool:
                True if this describes a text kernel file; False if it describes a binary
                kernel file.
        """
        return self._ext[1] == 't'

    @property
    def is_binary(self):
        """True if this _KernelInfo object describes a binary kernel file; False if it
        describes a text kernel file.

        Return:
            bool:
                True if this describes a binary kernel file; False if it describes a text
                kernel file.
        """
        return self._ext[1] == 'b'

    @property
    def label_abspath(self):
        """The absolute path to the PDS label of the kernel file described by this
        _KernelInfo object.

        If the file does not have a PDS label, an empty string is returned.

        Return:
            str:
                The absolute path to the PDS label of the kernel file described by this
                object, if any; an empty string otherwise.
        """

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
        """The content of the PDS label associated with this _KernelInfo object's kernel
        file, if any, expressed as a list of strings.

        The value is an empty list if there is no label file.

        Return:
            list[str, ...]:
                Content of the PDS label associated with this object's kernel file. If the
                file has no label, the list is empty.
        """

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
        """Any available comments from the kernel file associated with this _KernelInfo
        object, expressed as a list of strings.

        Return:
            list[str, ...]:
                Any comments about the kernel file associated with this object.
        """

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
        """Content of the text kernel file associated with this _KernelInfo object,
        expressed as a list of strings.

        If this object describes a binary kernel file, the returned list is empty.

        Return:
            list[str, ...]:
                The full content of the text kernel file described by this object if it is
                a texxt kernel; an empty list if the kernel file is binary.
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
        """The data lines from the text kernel file described by this _KernelInfo object,
        expressed as a list of strings.

        If this object describes a binary kernel file, the returned list is empty.

        Return:
            list[str, ...]:
                All data lines from the text kernel file described by this object; an
                empty list if the kernel file is binary.
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
        """All comment lines from the text kernel file described by this object, expressed as
        a list of strings.

        If this object describes a binary kernel file, the returned list is empty.

        Return:
            list[str, ...]:
                All comment lines from the text kernel file described by this object; an
                empty list if the kernel file is binary.
        """

        if self._text_comments is None:
            _ = self.text_content       # this fills in both

        return self._text_comments

    @property
    def dict_content(self):
        """The content of the text kernel described by this _KernelInfo object as parsed
        into a dictionary by text_kernel.from_file().

        If this object describes a binary kernel, the dictionary is empty.

        Return:
            dict:
                The content of the text kernel described by this object as parsed into a
                dictionary. If this object describes a binary kernel, the dictionary is
                empty.
        """

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
        """The NAIF IDs covered by the associated kernel file, including aliases.

        If the kernel file is associated with all NAIF IDs, such as if it is a leapseconds
        kernel, the set is empty.

        Return:
            set[int]:
                The NAIF IDs covered by the associated kernel file, including aliases.
        """

        if self._naif_ids is not None:
            return self._naif_ids

        # LSKs are applicable to all NAIF IDs
        if self.ktype == 'LSK':
            self._naif_ids = set()
            self._naif_as_found = set()
            self._naif_wo_aliases = set()
            return self._naif_ids

        # Check the rule results
        if 'naif_ids' in self._rule_values:
            self._naif_as_found = self._rule_values['naif_ids']
            self._naif_ids = naif_ids_with_aliases(self._naif_as_found)
            self._naif_ids_wo_aliases = naif_ids_wo_aliases(self._naif_ids)
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
                naif_ids |= _KernelInfo.KERNELINFO[basename].naif_ids_as_found

        elif self.is_text:              # any text kernel
            naif_ids = self._naif_ids_from_text_kernel()
            if not naif_ids:
                naif_ids = {}

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

        self._naif_ids_as_found = naif_ids
        self._naif_ids = naif_ids_with_aliases(naif_ids)
        self._naif_ids_wo_aliases = naif_ids_wo_aliases(self._naif_ids)
        return self._naif_ids

    @naif_ids.setter
    def naif_ids(self, ids):
        """Define the set of NAIF IDs for this _KernelInfo object.

        Args:
            ids (int or collection[int]):
                The set of NAIF IDs for this object.
        """

        if isinstance(ids, numbers.Integral):
            self._naif_ids = {ids}
        elif not ids:
            self._naif_ids = set()
        else:
            self._naif_ids = set(ids)

        self._naif_ids_as_found |= ids
        self._naif_ids = naif_ids_with_aliases(ids)
        self._naif_ids_wo_aliases = naif_ids_wo_aliases(self._naif_ids)
        self._manual_defs.append(('_naif_ids', self._naif_ids))

    def add_naif_ids(self, *ids):
        """Add one or more NAIF IDs to this _KernelInfo object.

        Args:
            *ids (ints):
                One or more NAIF IDs to add to this object.
        """

        ids = set(ids)
        self._naif_ids_as_found |= ids
        self._naif_ids |= naif_ids_with_aliases(ids)
        self._naif_ids_wo_aliases = naif_ids_wo_aliases(self._naif_ids)
        self._manual_defs.append(('add_naif_ids',) + ids)

    def remove_naif_ids(self, *ids):
        """Remove one or more NAIF IDs to this _KernelInfo object.

        Args:
            *ids (ints):
                One or more NAIF IDs to remove from this object.
        """

        ids = set(ids)
        self._naif_ids_as_found -= ids
        self._naif_ids = naif_ids_with_aliases(self._naif_ids_as_found)
        self._naif_ids_wo_aliases = naif_ids_wo_aliases(self._naif_ids)
        self._manual_defs.append(('remove_naif_ids',) + ids)

    @property
    def naif_ids_wo_aliases(self):
        """The NAIF IDs covered by the associated kernel file, excluding aliases.

        If the kernel file is associated with all NAIF IDs, such as if it is a leapseconds
        kernel, the set is empty.

        Return:
            set[int]:
                The NAIF IDs covered by the associated kernel file, excluding aliases.
        """

        if self._naif_ids_wo_aliases is None:
            _ = self.naif_ids

        return self._naif_ids_wo_aliases

    @property
    def naif_ids_as_found(self):
        """The exact set of NAIF IDs covered by the associated kernel file, before
        processing to handle aliases.

        If the kernel file refers to the alias of a NAIF ID, that alias is in the returned
        set rather than the updated ID.

        Return:
            set[int]:
                The NAIF IDs covered by the associated kernel file.
        """

        if self._naif_ids_as_found is None:
            _ = self.naif_ids

        return self._naif_ids_as_found

    _BODY_FRAME_INS = re.compile(r' *(?:FRAME|BODY|INS)_?(-?\d+)_', re.I)
    _SCLK_DATA_TYPE = re.compile(r' *SCLK_DATA_TYPE_(\d+)', re.I)

    def _naif_ids_from_text_kernel(self):
        """Internal method to extract the set of NAIF IDs from this _KernelInfo object's
        associated text kernel file.

        Return:
            set[int]:
                The NAIF IDs covered by the associated kernel file.
        """

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

    ######################################################################################
    # Time range
    ######################################################################################

    @property
    def time(self):
        """Time limits of this _KernelInfo object.

        For binary kernels, this is a tuple of two floats in seconds TDB, where the first
        time is the earliest time limit within the file and the second is the latest time
        limit within the file. Note that a kernel might have gaps in time coverage, or it
        might cover different NAIF IDs using different limits. Nevertheless, a kernel file
        will never have any applicability before the first time or after the second time.

        For kernels with no time dependence, such as a text kernel, the interval (None,
        None) is returned.

        Return:
            (float, float) or (None, None):
                A tuple of two floats in seconds TDB, where the first time is the earliest
                time limit within the object's associated kernel file and the second is
                the latest time within the file. If a file has no time dependence, (None,
                None) is returned.
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
            for naif_id in self.naif_ids_as_found:
                for (t0, t1) in cspyce.spkcov(self.abspath, naif_id).as_intervals():
                    tmin = min(tmin, t0)
                    tmax = max(tmax, t1)

            self._time = (tmin, tmax)

        # Handle CK
        elif self.ktype == 'CK':

            # Note that this only works if a SCLK has been furnished!
            for naif_id in self.naif_ids_as_found:
                try:
                    times = cspyce.ckcov(self.abspath, naif_id, needav=False,
                                         level='INTERVAL', tol=0., timsys='TDB',
                                         cover=50000)   # 20000 isn't enough for Voyager!
                except KeyError:
                    raise RuntimeError('Unable to determine time limits for '
                                       + self._basename
                                       + '; clock kernel must be furnished for ID '
                                       + str(naif_id))
                else:
                    for (t0, t1) in times.as_intervals():
                        tmin = min(tmin, t0)
                        tmax = max(tmax, t1)

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
    def time(self, times):
        """Define the time range of this _KernelInfo object using a tuple of two input
        values.

        Each of the times can be specified by an ISO-format date string or by a number of
        seconds TDB.

        Args:
            times ((float, int, or str, float, int, or str)):
                The start and stop times of this object.
        """

        (tmin, tmax) = times

        if isinstance(tmin, str):
            tmin = julian.tdb_from_iso(tmin)

        if isinstance(tmax, str):
            tmax = julian.tdb_from_iso(tmax)

        self._time = (tmin, tmax)
        self._manual_defs.append(('_time', self._time))

    ######################################################################################
    # Release date
    ######################################################################################

    # Match for lines that contain some other kind of date, not a release date
    _IGNORE1 = re.compile(r'.*((BEGIN|END|START|STOP)[_ ]TIME|Timespan)', re.I)

    # Ignore textkernel dates, which always begin with "@"
    _IGNORE2 = re.compile(r'@\d\d\d\d-.*', re.I)

    @property
    def release_date(self):
        """The release date of this _KernelInfo object as an ISO date string of the form
        "yyyy-mm-dd".

        If the release date is unknown, an empty string is returned.

        Return:
            str:
                This object's release date as an ISO date string of the form "yyyy-mm-dd";
                if the release date is unknown, an empty string is returned.
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
        for match_pattern in ('Release to: ', 'DELIVERY DATE:', '; Created ',
                              'SATEPHMERGE', 'SATMERGE', 'SATGEN',
                              'Run Date:', 'PRODUCT_CREATION_TIME'):
            daylist = []
            for rec in self.label + self.comments:
                if match_pattern in rec:
                    daylist += julian.days_in_strings(rec)

            if daylist:
                self._release_date = julian.format_day(max(daylist))
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

    @release_date.setter
    def release_date(self, date):
        """Set the release date for this _KernelInfo object.

        Use None if the release date is unknown.

        Args:
            date (str or None):
                The release date in a nearly arbitrary date-time format; use None or an
                empty string if the release date is unknown.
        """

        self._release_date = validate_release_date(date)
        self._manual_defs.append(('_release_date', self._release_date))

    ######################################################################################
    # Family and version
    ######################################################################################

    @property
    def version(self):
        """The version identifier of this _KernelInfo object, or an empty string if the
        file has no associated version.

        Returns:
            (int, str, tuple[int, ...]):
                The version of this object or an empty string if the version is undefined.
                A version using decimal points (e.g., 1.2.3) is represented by a tuple of
                ints.
        """

        if self._version is not None:
            return self._version

        if 'version' in self._rule_values:
            self._version = validate_version(self._rule_values['version'])
        elif 'version' in self._default_values:
            self._version = validate_version(self._default_values['version'])
        else:
            self._version = self.release_date

        return self._version

    @property
    def version_as_set(self):
        if isinstance(self.version, set):
            return self.version
        if self.version == '':
            return set()
        return {self.version}

    @version.setter
    def version(self, value):
        self._version = validate_version(value)
        self._manual_defs.append(('_version', self._version))

    @property
    def family(self):
        """Family name applicable to this kernel file; "" if unavailable.

        Returns:
            xxx: xxx
        """

        if self._family is not None:
            return self._family

        if 'family' in self._rule_values:
            self._family = self._rule_values['family']
        elif 'family' in self._default_values:
            self._family = self._default_values['family']
        else:
            self._family = self._basename

        return self._family

    @family.setter
    def family(self, value):
        if value is None:
            value = ''

        self._family = str(value)
        self._manual_defs.append(('_family', self._family))

    ######################################################################################
    # Download support
    ######################################################################################

    @property
    def source(self):
        if self._source is None:
            self._source = self._rules_values.get('source', [])

        return self._source

    @source.setter
    def source(self, value):
        if isinstance(value, str):
            value = [value]

        self._source = value

    @property
    def dest(self):
        if self._dest is None:
            self._dest = self._rules_values.get('dest', '')

        return self._dest

    @dest.setter
    def dest(self, value):
        self._dest = value

    ######################################################################################
    # Custom properties
    ######################################################################################

    # We define a dict subclass so that we can track when a property is added or deleted
    # manually.
    class _local_dict(dict):
        def __setitem__(self, key, value):
            self.add_property(key, value)
        def __delitem__(self, key):
            self.remove_property(key)

    @property
    def properties(self):
        """The dictionary of special properties for this kernel file.

        Returns:
            xxx: xxx
        """

        if self._rule_properties is None:
            self._rule_properties = {}
            for key, value in self._rule_values.items():
                if key in ('release_date', 'time', 'version', 'family', 'naif_ids'):
                    continue
                self._rule_properties[key] = value

        if self._properties is None:
            self._properties = _KernelInfo._local_dict()
            self._properties.update(self._rule_properties)

        return self._properties

    def add_property(self, name, value):
        """Add or modify a property, same as "self.properties[name] = value".

        Args:
            name (xxx): Xxx
            value (xxx): Xxx
        """

        super(_KernelInfo._local_dict, self.properties).__setitem__(name, value)
        self._manual_defs.append(('add_property', name, value))

    def remove_property(self, name):
        """Remove a property, same as "del self.properties[name]".

        Args:
            name (xxx): Xxx
        """

        super(_KernelInfo._local_dict, self.properties).__delitem__(name)
        self._manual_defs.append(('remove_property', name))

    ######################################################################################
    # Metakernel support
    ######################################################################################

    @property
    def meta_basenames(self):
        """The list of enclosed basenames if this is a metakernel; an empty list
        otherwise.

        Returns:
            xxx: xxx
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

    @staticmethod
    def match(pattern, flags=re.I):
        """The set of existing basenames that match the given regular expression.

        Args:
            pattern (xxx): Regular expression as a string or re.Pattern object.
            flags (RegexFlag, optional): Compile flags to use if the pattern is a string.
        """

        if isinstance(pattern, str):
            pattern = re.compile(pattern, flags=flags)

        basenames = {b for b in _KernelInfo.ABSPATHS if pattern.match(b)}

    @staticmethod
    def replace(basename, abspath):
        """Replace an existing KernelFile with the same basename.

        Args:
            basename (xxx): Xxx
            abspath (xxx): Xxx
        """

        manual_defs = _KernelInfo.KERNELINFO[basename]._manual_defs
        del _KernelInfo.KERNELINFO[basename]

        new_object = _KernelInfo(basename)
        for item in manual_defs:
            name = item[0]
            if name in new_object.__dict__:
                new_object.__dict__[name] = item[1]
            else:
                _KernelInfo.__dict__[name](new_object, *item[1:])

        _KernelInfo.ABSPATHS[basename] = abspath

##########################################################################################
