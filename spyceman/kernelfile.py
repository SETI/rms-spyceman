##########################################################################################
# spyceman/kernelfile.py
##########################################################################################
"""KernelFile is a subclass of Kernel that represents a single SPICE kernel file."""

import collections
import numbers
import portion
import re

import julian
import spyceman._localfiles as _localfiles

from spyceman.kernel      import Kernel
from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS
from spyceman._downloads  import get_fancy_index_dates, retrieve_online_file
from spyceman._utils      import is_basename, validate_time, validate_naif_ids, \
                                 validate_release_date, _input_set, _input_list, \
                                 _test_version

KTuple = collections.namedtuple('KTuple', ['basename', 'start_time', 'end_time',
                                           'naif_ids', 'release_date'])

class KernelFile(Kernel):
    """Kernel subclass representing a single SPICE kernel file.

    After you use the constructor:
        k = KernelFile(basename)
    you can freely access properties of the file:
        k.ktype         type of kernel, e.g., "SPK", inferred from the file extension.
        k.naif_ids      the set of NAIF IDs referenced by this file, including any of
                        their defined aliases. If the kernel is relevant to all NAIF IDs,
                        this set is empty.
        k.naif_ids_wo_aliases
                        the set of primary NAIF IDs referenced by this file. If it
                        references a body or frame by its alias, this is the primary ID
                        rather than the one that appears in the file. If the kernel is
                        relevant to all NAIF IDs, this set is empty.
        k.time          time coverage of this file as a tuple (start_time, stop_time). If
                        this kernel is relevant to all times, this tuple is (None, None).
        k.release_date  the release date of this kernel in "yyyy-mm-dd" format.
        k.version       the version number, string, or tuple of integers. If this kernel
                        does not have a version number, the value is "". A file may be
                        associated with multiple versions, in which case this attribute is
                        a set.
        k.version_as_set the version(s) as a set. If the kernel has only one version, this
                        set will have a single element. If the version is an empty string,
                        the set is empty.
        k.source        a list of one or more URLs pointing to online directories that can
                        be searched to download this file.
        k.dest          a sub-path defining where to place this file within the user's
                        SPICE downloads directory.
        k.family        the family of kernels with which this file associated.
        k.properties    a dictionary of any special properties for this kernel. Special
                        properties are mission-specific. For example, one might define the
                        property "voyager" for Voyager kernels, where the value is 1 for
                        kernels specific to Voyager 1 and 2 for kernels specific to
                        Voyager 2.

        k.exists        True if this file exists in the local file system.
        k.abspath       the absolute path to this file if it exists. Otherwise, an empty
                        string.
        k.is_known      True if this file is known to exist, although perhaps only online.

        k.ext           the file extension (including the period).
        k.is_text       True if this is a text kernel.
        k.is_binary     True if this is a binary kernel.
        k.checksum      the Adler 32 checksum of this file.
        k.label_abspath the path to the PDS label of this file, if it has a label.
        k.label         the text content of the label as a list of strings.
        k.comments      the embedded comments of this file as a list of strings.
        k.text          the entire content of this file if it is a text kernel.
        k.text_content  the data content of a text kernel.
        k.text_comments all the non-data content of a text kernel.
        k.dict_content  the dictionary content of this text kernel.
        k.meta_basenames the list of files referenced by this metakernel.

    Most of these properties are evaluated "lazily", which means that they are only
    derived when needed. However, all of these attributes of a KernelFile are global, so
    if two different KernelFile objects refer to the same basename, they will have access
    to the same information.

    In many cases, some of this information is derived directly from a file or its name
    using "Rules". Users can override these properties by setting their values explicitly.

    All SPICE kernel basenames must be unique. Initial calls to KernelFile.walk(),
    KernelFile.use_path(), and/or KernelFile.use_paths() will associate basenames with
    their paths in the user's local file system.

    Note that a KernelFile can be constructed for a file basename that does not currently
    exist. If the file is needed, it will be downloaded from one of its defined source
    URLs and saved to the directory defined by its dest attribute.
    """

    _is_ordered = False     # fixed value for every instance of this subclass

    def __init__(self, basename, exists=False, **properties):
        """Construct a KernelFile object.

        Input:
            basename    basename of a SPICE kernel file, or else a KernelFile object.
            exists      if True, this file is required to exist locally.
            name=value  optionally, set the attribute(s) or property identified by name to
                        the specified value.
        """

        if isinstance(basename, KernelFile):
            basename = basename._basename

        self._basename = basename

        if properties:
            KernelFile.set_info([self], properties)

        if exists:
            if basename not in _KernelInfo.ABSPATHS:
                self.must_exist()
            else:
                raise FileNotFoundError('kernel file not found: ' + repr(basename))

    def must_exist(self, source='', dest='', verbose=True):
        """Ensure that this file exists locally.

        Input:
            source      optional override to the default source URL(s).
            dest        optional override to the default local destination.
            verbose     True to print information about downloads.
        """

        if self.exists:
            return

        if Kernel._DOWNLOADS:

            dest = dest or self.dest

            sources = source or self.source
            if isinstance(sources, str):
                sources = [sources]

            # Try each of the possible sources
            error = None
            found = False
            for source in sources:
                table = get_fancy_index_dates(source)
                if table and self.basename not in table:
                    continue
                if verbose:
                    if table:
                        print(f'downloading "{self.basename}" from {source}')
                    else:
                        print(f'attempting to download "{self.basename}" from {source}')

                try:
                    destpath = retrieve_online_file(source, dest, self.basename,
                                                    dates=table, label=True)
                    found = True
                    break

                except ConnectionError as e:
                    error = error or e

            if not found:
                if error:
                    raise error
                raise FileNotFoundError('no identified source for "{self.basename}"')

            # Use this new file
            _localfiles.use_path(destpath)

        else:
            raise FileNotFoundError(f'missing kernel file: "{self.basename}"')

    @staticmethod
    def set_info(info, **properties):
        """Initialize info about one or more KernelFiles.

        Input:
            info        a KernelFile, KTuple or basename, or a list thereof. If it is a
                        KTuple, the time limits, set of NAIF IDs, and release date are
                        also defined.
            name=value  zero or more additional attributes or properties and their values.
                        These values will be assigned to each kernel listed.
        """

        if not isinstance(info, list):
            info = [info]

        for item in info:

            # Create the KernelFile
            if isinstance(item, KernelFile):
                kernel = item
            elif isinstance(item, str):
                kernel = KernelFile(item)
            else:
                kernel = KernelFile(item.basename)

                # Define the KTuple attributes
                kernel.time = (item.start_time, item.end_time)
                kernel.naif_ids = item.naif_ids
                kernel.release_date = item.release_date

            # Set any additional properties
            for name, value in properties.items():
                if name in KernelFile.__dict__:
                    KernelFile.__dict__[name].fset(kernel, value)
                else:
                    info.add_property(name, value)

    ######################################################################################
    # Required properties
    ######################################################################################

    @property
    def _info(self):
        """The _KernelInfo object for this basename, constructed anew if necessary."""
        return _KernelInfo.lookup(self._basename)

    @property
    def basenames(self):
        """Ordered list of all the kernel basenames associated with this Kernel."""
        return [self.basenames]

    @property
    def name(self):
        """The name for this kernel, always equivalent to its basename."""
        return self.basename

    @property
    def ktype(self):
        """Kernel type of this file: "SPK", "CK", "LSK", etc."""
        return self._info.ktype

    @property
    def naif_ids(self):
        """The set of NAIF IDs covered by this file, including aliases; an empty set if
        the kernel applies to all NAIF IDs.
        """
        return self._info.naif_ids

    @naif_ids.setter
    def naif_ids(self, ids):
        self._info.naif_ids = ids

    def add_naif_ids(self, *ids):
        """Add one or more NAIF IDs to this KernelFile."""
        self._info.add_naif_ids(*ids)

    def remove_naif_ids(self, *ids):
        """Remove one or more NAIF IDs from this KernelFile."""
        self._info.remove_naif_ids(*ids)

    @property
    def naif_ids_wo_aliases(self):
        """The set of all NAIF IDs described by the file, excluding aliases."""
        return self._info.naif_ids_wo_aliases

    @property
    def naif_ids_as_found(self):
        """The exact set of all NAIF IDs described by the file before handling aliases."""
        return self._info.naif_ids_as_found

    @property
    def time(self):
        """Time limits as a tuple of two times in seconds TDB; (None,None) if this kernel
        is applicable to all times.
        """
        return self._info.time

    @time.setter
    def time(self, value):
        self._info.time = value

    @property
    def tmin(self):
        """The lower time limit of this file in seconds TDB; None if this kernel is
        applicable to all times.
        """
        return self._info.time[0]

    @property
    def tmax(self):
        """The upper time limit of this file in seconds TDB; None if this kernel is
        applicable to all times.
        """
        return self._info.time[1]

    @property
    def release_date(self):
        """Release date as an ISO date string "yyyy-mm-dd", or "" if no release date is
        known.
        """
        return self._info.release_date

    @release_date.setter
    def release_date(self, value):
        if not value:
            self._info._release_date = ''

        self._info.release_date = julian.format_day(julian.day_from_string(value))

    @property
    def version(self):
        """Version of this kernel file as a string, integer, or tuple of integers, or
        a set containing multiple versions. If the file has no version, the value is "".
        """
        return self._info.version

    @property
    def version_as_set(self):
        """Version(s) of this kernel file as a set containing strings, integers, or tuples
        of integers."""
        return self._info.version_as_set

    @version.setter
    def version(self, value):
        self._info.version = value

    @property
    def family(self):
        """The family name of this kernel. Typically, kernels with a different version
        or time range often are members of the same family.
        """
        return self._info.family

    @family.setter
    def family(self, value):
        self._info.family = str(value)

    @property
    def source(self):
        """One or more URLs to search for this file online."""
        return self._info.source

    @source.setter
    def source(self, value):
        self._info.source = value

    @property
    def dest(self):
        """The sub-path within a SPICE kernel download directory where this file will be
        located upon download.
        """
        return self._info.dest

    @dest.setter
    def dest(self, value):
        self._info.dest = value

    @property
    def properties(self):
        """The dictionary of special properties for this Kernel."""
        return self._info.properties

    def add_property(self, name, value):
        """Add or modify a property, same as "self.properties[name] = value"."""
        self._info.add_property(name, value)

    def remove_property(self, name):
        """Remove a property, same as "del self.properties[name]"."""
        self._info.remove_property(name)

    ######################################################################################
    # Public properties specific to KernelFile objects
    ######################################################################################

    @property
    def abspath(self):
        """Absolute path to this KernelFile; an empty string if this file doesn't exist.
        """
        return self._info.abspath

    @property
    def exists(self):
        """True if this kernel file exists."""
        return self._info.exists

    @property
    def is_known(self):
        """True if this kernel file basename has been defined; it might not exist as a
        local file.
        """
        return self._info.is_known

    @property
    def ext(self):
        """File extension of this file."""
        return '.' + self.basename.rpartition('.')[-1]

    @property
    def is_text(self):
        """True if this is a text kernel file."""
        return self._info.is_text

    @property
    def is_binary(self):
        """True if this is a binary kernel file."""
        return self._info.is_binary

    @property
    def checksum(self):
        """Adler 32 checksum of the file."""
        return self._info.checksum

    @property
    def label_abspath(self):
        """Absolute path to a label file, if any; blank otherwise."""
        return self._info.label_abspath

    @property
    def label(self):
        """Content of the PDS label, if any, as a list of strings."""
        return self._info.label

    @property
    def comments(self):
        """Any available comments as a list of strings."""
        return self._info.comments

    @property
    def text(self):
        """Content of a text kernel as a list of strings; an empty list for a binary
        kernel.
        """
        return self._info.text

    @property
    def text_content(self):
        """Data content of a text kernel as a list of strings; an empty list for a binary
        kernel.
        """
        return self._info.text_content

    @property
    def text_comments(self):
        """All comments embedded within a text kernel as a list of strings; an empty list
        for a binary kernel.
        """
        return self._info.text_comments

    @property
    def dict_content(self):
        """Content of this text kernel as parsed into a textkernel dictionary."""
        return self._info.dict_content

    @property
    def meta_basenames(self):
        """The list of enclosed basenames if this is a metakernel; an empty list
        otherwise.
        """
        return self._info.meta_basenames

    ######################################################################################
    # Public API for selecting and sorting kernel files
    ######################################################################################

    @staticmethod
    def reduce(basenames, *, tmin=None, tmax=None, ids=None):
        """Reduce a list of basenames or KernelFiles to the minimal list that provides
        complete coverage.

        Input:
            basenames   an ordered list of basenames or KernelFiles.
            tmin, tmax  time range coverage desired.
            ids         set of NAIF IDs required.

        Return:         the reduced list of basenames or KernelFiles.
        """

        return_basenames = isinstance(basenames[0], str)
        kfiles = [KernelFile(b) if isinstance(b, str) else b for b in basenames]

        BIGTIME = 1.e99

        if tmin is None:
            tmins = [k.time[0] for k in kfiles if k.time[0] is not None]
            if tmins:
                tmin = min(tmins)
            else:
                tmin = -BIGTIME

        if tmax is None:
            tmaxes = [k.time[1] for k in kfiles if k.time[1] is not None]
            if tmaxes:
                tmax = max(tmaxes)
            else:
                tmin = BIGTIME

        if not ids:
            ids = set()
            for k in kfiles:
                ids |= k.naif_ids_wo_aliases

        if not ids:
            if tmin == -BIGTIME and tmax == BIGTIME:
                return kfiles[-1:]
            ids = {0}

        interval_dicts = {i:portion.IntervalDict() for i in ids}
        for kfile in kfiles:
            naif_ids = {0} if ids == {0} else kfile.naif_ids & ids
            for naif_id in naif_ids:
                # Each KernelFile interval overwrites the intervals of names earlier in
                # in the list
                (t0, t1) = kfile.time
                if t0 is None:
                    t0 = -BIGTIME
                if t1 is None:
                    t1 = -BIGTIME

                interval = portion.closed(t0, t1)
                interval_dicts[naif_id][interval] = kfile

        # Identify the full set of kernels needed to cover each NAIF ID
        times_required = portion.closed(tmin, tmax)

        reduced_set = set()
        for interval_dict in interval_dicts.values():
            coverage = interval_dict[times_required]
            reduced_set |= set(coverage.values())

        # Return the required kernels in their original order
        kfiles = [k for k in kfiles if k in reduced_set]

        if return_basenames:
            return [k.basename for k in kfiles]

        return kfiles

    @staticmethod
    def filter_basenames(basenames, tmin=None, tmax=None, ids=None, *, name=None,
                         version=None, release_date=None, expand=False, reduce=False,
                         flags=re.IGNORECASE, **properties):
        """Filter a list of basenames or KernelFiles based on time coverage, NAIF IDs,
        version, release date, and/or property values

        If the input is a list, the filtered list returned will be in the same order.

        Inputs:
            basenames   a list of basenames or KernelFiles for which the filter is to be
                        applied.
            tmin, tmax  only include kernel files with times that overlap this time
                        interval, specified as a date/time string or in TDB seconds.
            ids         only include kernel files that refer to one or more of these NAIF
                        IDs.
            name        only include kernel files that match this basename or regular
                        expression. Specify multiple values in a list, set, or tuple.
                        Note: in this context, a string containing only only letters,
                        numbers, underscore, dash ("-") and dot(".") is treated as a
                        literal basename rather than as a match pattern.
            version     only include kernel files that match this version. Use a set to
                        specify multiple acceptable versions. Use a list of two values to
                        specify the minimum and a maximum (inclusive) of acceptable range;
                        in this case, either value can be None to enforce a minimum or a
                        maximum version but not both.
            release_date only include kernel files consistent with this release date. Use
                        a list or tuple of two date strings defining the earliest and
                        latest dates to include. Replace either date value with None or an
                        empty string to ignore that constraint. A single date is treated
                        as the upper limit on the release date.
            expand      if True, the returned list of kernel files is expanded if
                        necessary to ensure that the entire time range is covered for all
                        of the specified NAIF IDs. In this case, some constraints on name,
                        version, and release date might be violated.
            reduce      If True, any kernel files whose coverage is eclipsed by other
                        kernel files later in the list will be eliminated.
            flags       compile flags to use on any regular expressions. Default is
                        re.IGNORECASE.
            name=value  any additional constraints on property values; kernel files with
                        other values will be removed from the returned list. Place
                        multiple values in a list, set, or tuple.
        """

        def filter_by_name(name, kfiles):
            if not name:
                return kfiles

            name = _input_set(name)
            names = {n.lower() for n in name if is_basename(n)}
            patterns = [re.compile(n, flags=flags) for n in name if not is_basename(n)]
            sublist = []
            for kfile in kfiles:
                if kfile.basename.lower() in names:
                    sublist.append(kfile)
                else:
                    for pattern in patterns:
                        if pattern.fullmatch(kfile.basename):
                            sublist.append(kfile)
                            break

            return sublist

        def filter_by_version(version, kfiles):
            if not version:
                return kfiles

            return [k for k in kfiles if _test_version(version, k)]

        def filter_by_release_date(release_date, kfiles):
            if not release_date:
                return kfiles

            sublist = []
            for kfile in kfiles:
                date = kfile.release_date
                if date:
                    if release_date[0] and date < release_date[0]:
                        continue
                    if release_date[1] and date > release_date[1]:
                        continue
                    sublist.append(kfile)
                else:
                    sublist.append(kfile)

            return sublist

        def filter_by_properties(properties, kfiles):
            if not properties:
                return kfiles

            for name, value in properties.items():
                if not value and value != 0:    # ignore None or empties but not zero
                    continue

                sublist = []
                valset = _input_set(value)
                for kfile in kfiles:
                    if name in kfile.properties:
                        test = _input_set(kfile.properties[name])
                        if test & valset:
                            sublist.append(kfile)
                    else:
                        sublist.append(kfile)

                kfiles = sublist

            return kfiles

        #### Begin active code here

        # Clean up inputs
        name = _input_list(name)

        if release_date:
            if isinstance(release_date, (list, tuple)):
                release_date = [validate_release_date(release_date[0]),
                                validate_release_date(release_date[1])]
            else:
                release_date = [None, validate_release_date(release_date)]

        if tmin is not None:
            tmin = validate_time(tmin)

        if tmax is not None:
            tmax = validate_time(tmax)

        if ids:
            ids = validate_naif_ids(ids)

        # Check return type
        return_basenames = isinstance(basenames[0], str)

        # Switch from basenames to KernelFiles
        kfiles = [KernelFile(b) if isinstance(b, str) else b for b in basenames]

        # Sub-select kernels by time and/or NAIF IDs
        if tmin is not None or tmax is not None or ids:
            kfiles = [k for k in kfiles if k.has_overlap(tmin, tmax, ids)]

        # Always filter based on properties
        kfiles = filter_by_properties(properties, kfiles)

        unfiltered = kfiles

        # Filter based on other inputs
        kfiles = filter_by_name(name, kfiles)
        kfiles = filter_by_version(version, kfiles)
        kfiles = filter_by_release_date(release_date, kfiles)

        # Expand if necessary
        if expand:
            # To expand, we first try earlier files and then later files, relative to what
            # is in the filtered list.

            # Find the highest location of a filtered file in the unfiltered list
            maxloc = unfiltered.index(kfiles[-1])

            # Create the ordered list of unused files
            kset = set(kfiles)
            before = [k for k in unfiltered[:maxloc] if k not in kset]
            after  = [k for k in unfiltered[maxloc:] if k not in kset]
            expanded = after[::-1] + before + kfiles

            reduced = set(KernelFile.reduce(expanded, tmin=tmin, tmax=tmax, ids=ids))
            kfiles = [k for k in expanded if k in (reduced | kset)]

        # Reduce if necessary
        if reduce:
            kfiles = KernelFile.reduce(kfiles, tmin=tmin, tmax=tmax, ids=ids)

        if return_basenames:
            return [k.basename for k in kfiles]

        return kfiles

    @staticmethod
    def find_all(pattern=None, *, ktype=None, exists=False, sort='alpha', flags=re.I):
        """The list of basenames matching a particular pattern and/or of a particular
        type.

        Inputs:
            pattern     if specified, only return basenames matching this name or pattern.
                        Specify multiple names or regular expressions in a list, tuple, or
                        set.
            ktype       if specified, only basenames associated with this ktype will be
                        returned. If the ktype can be inferred from the pattern, it is
                        not necessary to specify it here.
            exists      if True, only file basenames in the local file system are
                        returned.
            sort        definition of how to sort the returned basenames:
                            "alpha"         sort alphabetically (default);
                            "version"       sort by version;
                            "date"          sort by release date;
                            any function    sort using the return value of this function.
            flags       the compile flags for the regular expression; default is
                        re.IGNORECASE.
        """

        sort_key = KernelFile.basename_sort_key(sort)

        # Get the set of candidate basenames
        if pattern:
            basenames = set()
            if isinstance(pattern, (list, tuple, set)):
                patterns = pattern
            else:
                patterns = [pattern]

            for pattern in patterns:
                if isinstance(pattern, str):
                    if is_basename(pattern):
                        pattern = pattern.replace('.', r'\.')
                    pattern = re.compile(pattern, flags=flags)

                ext = '.' + pattern.pattern.rpartition('.')[-1].lower()
                if ext in _EXTENSIONS:
                    sources = _KernelInfo.BASENAMES_BY_KTYPE[_EXTENSIONS[ext]]
                elif ktype:
                    sources = _KernelInfo.BASENAMES_BY_KTYPE[_EXTENSIONS[ext]]
                else:
                    sources = _KernelInfo.KERNELINFO.keys()
                basenames |= {b for b in sources if pattern.fullmatch(b)}

        else:
            if ktype:
                basenames = _KernelInfo.BASENAMES_BY_KTYPE[ktype]
            else:
                basenames = set(_KernelInfo.KERNELINFO.keys())

        # Filter by existence
        if exists:
            basenames = [b for b in basenames if b in _KernelInfo.ABSPATHS]

        # Sort
        basenames = list(basenames)
        basenames.sort(key=sort_key)
        return basenames

    @staticmethod
    def basename_sort_key(option):
        """A function that returns a key function for sorting basenames or KernelFiles.

        Options are:
            "alpha"         sort basenames alphabetically (caseless);
            "version"       sort by version, then alphabetically;
            "date"          sort by release date, then alphabetically;
            any function    use this function as the sort key.
        """

        def version_sort_key(basename):
            """Key for sorting versions. Integers and tuples of integers are sorted
            together. Strings sort as greater than integers or tuples. Missing versions
            sort lowest.
            """

            version = KernelFile(basename).version
            if isinstance(version, numbers.Integral):
                return (1, version)
            if isinstance(version, tuple):
                return (1,) + version
            if not version:         # put basenames with unknown version lowest
                return (0,)
            return (2, version)

        if option == 'alpha':
            return lambda basename: KernelFile(basename).basename.lower()

        if option == 'date':
            return lambda basename: (KernelFile(basename).release_date,
                                     KernelFile(basename).basename.lower())

        if option == 'version':
            return lambda basename: (version_sort_key(basename),
                                     KernelFile(basename).basename.lower())

        if hasattr(option, '__call__'):
            return lambda basename: option(KernelFile(basename).basename)

        raise ValueError('invalid sort option: ' + repr(option))

    ######################################################################################
    # Veto and shadow management
    ######################################################################################

    # These are lists of lists of compiled regular expressions. If the first item in each
    # sub-list matches a file basename, then the remaining regular expressions are used.
    # If the first item contains capturing sub-patterns, these can be referenced in the
    # subsequent items, which are stored as tuples (string, flags) instead of compiled
    # expressions.
    _VETOS = []
    _SHADOWS = []

    @staticmethod
    def mutual_veto(*patterns, flags=re.IGNORECASE):
        """Ensure that if a kernel is furnished whose basename matches one of the given
        patterns, any overlapping kernel matching one of the patterns will be unloaded.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.
        """

        patterns = KernelFile._compile(patterns, flags=flags, subs=False)
            # this is a list of patterns

        for pattern in patterns:
            KernelFile._VETOS.append([pattern] + patterns)

    @staticmethod
    def group_vetos(*patterns, flags=re.IGNORECASE):
        """Ensure that if a kernel is furnished whose basename matches any of the given
        patterns, any overlapping kernels whose basename matches one of the other patterns
        will be unloaded.

        Multiple patterns can be specified inside a tuple, list, or set.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.
        """

        patterns = [KernelFile._compile(p, flags=flags, subs=False) for p in patterns]
            # this is a list of lists of patterns

        for k in range(len(patterns)):
            selection = patterns[k]         # list of one or more patterns
            remainders = list(patterns)     # copy the list of lists
            remainders.pop(k)               # remove the selection
            other_patterns = []             # convert remainders to a list of patterns
            for remainder in remainders:
                other_patterns += remainder

            for pattern in selection:
                KernelFile._VETOS.append([pattern] + other_patterns)

    @staticmethod
    def veto(patterns, *vetos, flags=re.IGNORECASE):
        """Ensure that if a kernel is furnished whose basename matches the first pattern,
        any overlapping kernel whose name matches one of the veto patterns will be
        unloaded.

        Multiple patterns can be specified inside a tuple, list, or set. If the first
        input contains capturing sequences, these can be referenced in the remaining
        patterns.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.
        """

        patterns = KernelFile._compile(patterns, flags=flags, subs=False)
        vetos = KernelFile._compile(vetos, flags=flags, subs=True)
            # Each is a list of patterns

        for pattern in patterns:
            KernelFile._VETOS.append([pattern] + vetos)

    @staticmethod
    def shadow(front, *behind, flags=re.IGNORECASE):
        """Ensure that if a kernel is furnished whose basename matches the first pattern,
        it will be furnished at a higher precedence than any overlapping kernel whose
        basename matches the second or subsequent patterns.

        Multiple "front" patterns can be specified inside a tuple, list, or set. If this
        input contains capturing sequences, these can be referenced in the "behind"
        patterns.
        """

        front  = KernelFile._compile(front,  flags=flags)
        behind = KernelFile._compile(behind, flags=flags)
            # Each is a list of patterns

        for pattern in front:
            KernelFile._SHADOWS.append([pattern] + behind)

    @staticmethod
    def _compile(patterns, flags=re.IGNORECASE, subs=False):
        """Convert one pattern or list of patterns to a list of compiled patterns.

        Patterns containing replacement patterns cannot be compiled; they are instead
        returned as tuples (string, flags).
        """

        if not isinstance(patterns, (list, set, tuple)):
            patterns = (patterns,)

        result = []
        for pattern in patterns:
            if not isinstance(pattern, re.Pattern):
                if is_basename(pattern):    # convert a basename to a regular expression
                    pattern = pattern.replace('.', r'\.')
                try:
                    pattern = re.compile(pattern, flags=flags)
                except re.error:
                    if subs:
                        pattern = (pattern, flags)
                    else:
                        raise

            result.append(pattern)

        return result

    @staticmethod
    def _get_vetos_or_shadows(basename, source):
        """The list of compiled regular expressions that match this basename."""

        matches = []
        for item_list in source:
            match = item_list[0].fullmatch(basename)
            if match:
                for item in item_list[1:]:
                    if isinstance(item, tuple):
                        (template, flags) = item
                        matches.append(re.compile(match.expand(template), flags=flags))
                    else:
                        matches.append(item)

        return matches

    @staticmethod
    def _get_vetos(basename):
        """The list of compiled regular expressions that this basename vetos."""

        return KernelFile._get_vetos_or_shadows(basename, source=KernelFile._VETOS)

    @staticmethod
    def _get_shadows(basename):
        """The list of compiled regular expressions that this basename shadows."""

        return KernelFile._get_vetos_or_shadows(basename, source=KernelFile._SHADOWS)

##########################################################################################
# Include the _localfiles functions as class methods
##########################################################################################

KernelFile.initialize = _localfiles.initialize
KernelFile.walk       = _localfiles.walk
KernelFile.use_path   = _localfiles.use_path
KernelFile.use_paths  = _localfiles.use_paths

##########################################################################################
# Enable the Kernel class to access this subclass
##########################################################################################

Kernel.KernelFile = KernelFile

##########################################################################################
