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
                        does not have a version number, the value is "".
        k.family        the family of kernels with which this file associated. For
                        example, if a kernel has multiple versions indicated by a
                        three-digit integer, this would be the basename with its version
                        replaced by "NNN".
        k.properties    a dictionary of any special properties for this kernel. Special
                        properties are mission-specific. For example, one might define the
                        property "voyager" for Voyager kernels, where the value is 1 for
                        kernels specific to Voyager 1 and 2 for kernels specific to
                        Voyager 2.
        k.exists        True if this file exists in the local file system.
        k.abspath       the absolute path to this file if it exists. Otherwise, an empty
                        string.
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

    In most cases, this information is derived directly from a file or its name. Users can
    override many of these properties by setting their values explicitly.

    All SPICE kernel basenames must be unique. Initial calls to KernelFile.walk(),
    KernelFile.use_path(), and/or KernelFile.use_paths() will associate a basename with
    its path in the user's local file system.
    """

    _is_ordered = False     # fixed value for every instance of this subclass

    def __init__(self, basename, exists=False):
        """Construct a KernelFile object for a given basename.

        If exists is True and the file does not exist, raise a FileNotFoundError.
        """

        self._basename = basename
        if exists and basename not in _KernelInfo.ABSPATHS:
            raise FileNotFoundError('kernel file not found: ' + repr(basename))

    @staticmethod
    def set_info(info, **properties):
        """Initialize info about one or more known KernelFiles.

        Input:
            info        a KTuple or basename, or a list thereof. If it is a KTuple, the
                        time limits, set of NAIF IDs, and release date are assigned for
                        this kernel file.
            name=value  zero or more additional attributes or properties and their values
                        to be assigned for every basename listed.
        """

        if not isinstance(info, list):
            info = [info]

        for ktuple in info:

            # Create the KernelFile
            if isinstance(ktuple, str):
                kernel = KernelFile(ktuple)
            else:
                kernel = KernelFile(ktuple.basename)

                # Define the KTuple attributes
                kernel.time = (ktuple.start_time, ktuple.end_time)
                kernel.naif_ids = ktuple.naif_ids
                kernel.release_date = ktuple.release_date

            # Set any additional properties
            for name, value in properties.items():
                if '_' + name in kernel.__dict__:
                    kernel.__dict__[name].fset(kernel, value)
                else:
                    kernel.properties[name] = value

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
        self._info.naif_ids_without_aliases

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
        """Version of this kernel file as a string, integer, or tuple of integers."""
        return self._info.version

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
    def properties(self):
        """The dictionary of special properties for this Kernel."""
        return self._info.properties

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
    # Public API for selecting kernel files
    ######################################################################################

    @staticmethod
    def filter_basenames(basenames, name=None, tmin=None, tmax=None, ids=None,
                         dates=None, versions=None, expand=False, reduce=False,
                         **properties):
        """Filter a list or set of basenames based on time coverage, NAIF IDs, version,
        release date, and/or property values

        If the input is a list, the filtered list returned will be in the same order.

        Inputs:
            basenames   a list or set of basenames for which the filter is to be applied.
            name        a basename or regular expression that every returned file basename
                        must match. Alternatively, a tuple of patterns or basenames, and
                        every returned file must match one or more of these patterns.
                        Note: in this context, a string containing only only letters,
                        numbers, underscore, dash ("-") and dot(".") is treated as a
                        literal basename rather than as a match pattern.
            tmin, tmax  only include basenames with times that overlap this time interval,
                        specified in TDB seconds.
            ids         only include basenames that refer to one or more of these NAIF
                        IDs.
            dates       only include basenames released within this range of dates. Use a
                        tuple of two date strings, defining the earliest and latest dates
                        to include. Replace either date value with None or an empty string
                        to ignore that constraint. A single date is treated as the latest
                        release date.
            versions    only include basenames within this range of versions. Use a tuple
                        of two version IDs, defining the minimum and maximum to be
                        included. Replace either value with None to ignore that
                        constraint. A single string or integer is treated as the upper
                        limit.
            expand      if True, the returned list of basenames is expanded if necessary
                        to ensure that all of the specified NAIF IDs are covered for the
                        entire time range tmin to tmax. In this case, some constraints on
                        the name, release date, and version might be violated.
            reduce      If True, only a reduced subset of the basenames will be returned.
                        The reduced subset excludes any kernel files earlier in the list
                        whose content is completely covered by later kernels. If False,
                        every kernel file containing times and IDs related to the request
                        will be returned.
            name=value  optional additional property constraints. If a single non-None
                        value is given, basenames that have a different value of this
                        property will be excluded, but those for which the named property
                        is undefined will still be included. To match multiple values of
                        a property, specify these values inside a tuple, list, or set.
        """

        original_basenames = basenames

        # Apply the basename filter
        if name is not None:
            if not isinstance(name, (list, tuple)):
                patterns = (name,)
            else:
                patterns = name

            # Create the set of every basename matching one or more patterns
            matches = set()
            for pattern in patterns:

                regex = None
                if isinstance(pattern, re.Pattern):
                    regex = pattern
                else:
                    # With no special chars, it's a literal string; otherwise, a regex
                    if not KernelFile._is_basename(pattern):
                        regex = re.compile(pattern, re.I)

                if regex:
                    for basename in basenames:
                        if regex.fullmatch(basename):
                            matches.add(basename)
                else:
                    matches.add(pattern)

            # Filter the list of basenames, preserving original order
            basenames = [b for b in basenames if b in matches]

        # Filter on properties
        if properties:
            kernels = [KernelFile(b) for b in basenames]
            filtered = set()

            # For each property constrained by the user...
            for prop_name, prop_values in properties.items():
                name_found = False

                # Convert the value(s) to a set; include None
                if isinstance(prop_values, (list,tuple,set)):
                    prop_values = set(prop_values) | {None}
                else:
                    prop_values = {prop_values, None}

                # Filter KernelFiles based on the constraint. Include KernelFiles for
                # which the property is not present or None.
                for kernel in kernels:
                    if prop_name in kernel.properties:
                        name_found = True

                    kernel_value = kernel.properties.get(prop_name, None)
                    if kernel_value in prop_values:
                        filtered.add(kernel.basename)

                # If this property did not appear anywhere, it was probably an error
                if not name_found:
                    raise ValueError('filter_basenames() got an unexpected keyword '
                                     'argument ' + repr(prop_name))

            # Create the filtered basename list, preserving the original order
            basenames = [k.basename for k in kernels if k.basename in filtered]

        basenames_filtered_by_name = basenames  # save this list for the "expand" option

        # Create KernelFile objects
        kernels = [KernelFile(b) for b in basenames]

        # Filter by time interval
        if (tmin, tmax) != (None, None):
            # If either time is None, use the other
            tmin = tmax if tmin is None else tmin
            tmax = tmin if tmax is None else tmax
            time_is_constrained = tmin is not None

            kernels = [k for k in kernels if Kernel.time_overlap(tmin, tmax)]

        # Filter by NAIF ID
        if isinstance(ids, numbers.Integral):
            ids = {ids}

        if ids:
            kernels = [k for k in kernels if Kernel.naif_id_overlap(tmin, tmax, ids)]

        # Filter by date
        if not isinstance(dates, (tuple, list)):
            dates = (None, dates)

        if dates[0] is not None:
            if isinstance(dates[0], numbers.Integral):
                date = julian.ymd_format_from_day(dates[0])
            else:
                date = dates[0]

            kernels = [k for k in kernels if (k.release_date and k.release_date >= date)]

        if dates[1] is not None:
            if isinstance(dates[1], numbers.Integral):
                date = julian.ymd_format_from_day(dates[1])
            else:
                date = dates[1]

            kernels = [k for k in kernels if (k.release_date and k.release_date <= date)]

        # Filter by version
        if not isinstance(versions, (tuple, list)):
            versions = (None, versions)

        if versions[0] is not None:
            kernels = [k for k in kernels if Kernel._version_ge(k.version, versions[0])]

        if versions[1] is not None:
            kernels = [k for k in kernels if Kernel._version_le(k.version, versions[1])]

        # For the expand and/or reduce options, revisit the set of NAIF IDs and time range
        if expand or reduce:

            # If no NAIF ID constraint was provided, use the set of NAIF IDs found
            ids_found = Kernel.naif_ids_for_kernels(*kernels)
            if not ids:
                ids = ids_found

            # Also remove any NAIF IDs that are completely absent
            if ids:
                all_ids = Kernel.naif_ids_for_kernels(*original_basenames)
                if all_ids:
                    ids = ids & all_ids

        # Expand the list of basenames if necessary
        if expand and (name or dates != (None, None) or versions != (None, None)):
            new_basenames = set()

            # We will try four different ways to address any missing NAIF IDs or cases of
            # incomplete coverage:
            #   1. Allow earlier dates and versions but retain the name constraint;
            #   2. Allow any dates or versions but retain the name constraint;
            #   3. Relax the name constraint, and then allow earlier dates and versions;
            #   4. Relax all name, date, and version constraints.

            if basenames_filtered_by_name == original_basenames:
                list_options = [original_basenames]
            else:
                list_options = [basenames_filtered_by_name, original_basenames]

            iters = len(list_options)
            if dates[1] is None and versions[1] is None:
                date_options    = iters * [(None, None)]
                version_options = iters * [(None, None)]
            else:
                date_options    = iters * [(None, dates[1])   , (None, None)]
                version_options = iters * [(None, versions[1]), (None, None)]
                list_options    = [2*[option] for option in list_options]

            # Determine which NAIF IDs require additional kernel files
            time_info = {}      # naif_id -> (best times, current times, expansion needed)
            for naif_id in ids:

                # Figure out the best possible time coverage for this NAIF ID
                best = Kernel.time_for_kernels(*original_basenames, ids={naif_id})

                # Get the current time limits (None if the NAIF ID is missing)
                current = Kernel.time_for_kernels(*kernels, ids={naif_id})

                if time_is_constrained:
                    best = (max(tmin, best[0]), min(tmax, best[1]))
                    if best[0] > best[1]:
                        # Skip this NAIF ID because the time coverage required does not
                        # overlap anything in the original set of available kernels.
                        ids.remove(naif_id)
                        continue

                    expansion = (current[0] is None or current[0] > best[0],
                                 current[1] is None or current[1] < best[1])
                else:
                    expansion = (current[0] is None, current[1] is None)

                time_info = (best, current, expansion)

            # Try the four expansion options
            for (list_option, date_option, version_option) in zip(list_options,
                                                                  date_options,
                                                                  version_options):
                new_basenames = set()

                # Check each NAIF ID
                try_again = False       # becomes True if any NAIF ID is incomplete
                for naif_id in ids:
                    (best, current, expansion) = time_info[naif_id]
                    if expansion == (False, False):
                        continue

                    # Get the list of relevant basenames
                    basenames_for_id = KernelFile.filter_basenames(
                                                        list_option,
                                                        tmin=tmin, tmax=tmax,
                                                        dates=date_option,
                                                        versions=version_option,
                                                        ids={naif_id}, expand=False)

                    # Check the time limits of coverage now
                    (t0, t1) = Kernel.time_for_kernels(*basenames_for_id,
                                                       ids={naif_id})
                    if expansion[0]:
                        t0_satisfied = t0 is not None and (t0 <= best[0])
                    else:
                        t0_satisfied = True     # because expansion is not needed

                    if expansion[1]:
                        t1_satisfied = t1 is not None and (t1 >= best[1])
                    else:
                        t1_satisfied = True     # because expansion is not needed

                    new_basenames |= set(basenames_for_id)

                    # If time limits are unsatisfied, move on to next set of options
                    if not (t0_satisfied and t1_satisfied):
                        try_again = True
                        break                   # exit the loop over NAIF IDs

                if not try_again:
                    break

            # Sort with expanded basenames before un-expanded basenames
            old_basenames = {k.basename for k in kernels}
            new_kernels = [KernelFile(b) for b in original_basenames
                           if b in new_basenames and b not in old_basenames]
            kernels = new_kernels + kernels

        # If necessary, reduce the list by eliminating extraneous kernels
        if reduce:
            interval_dicts = {i:portion.IntervalDict() for i in ids}
            for kernel in kernels:
                for naif_id in (kernel.naif_ids & ids):
                    # Each basename's interval overwrites the intervals of names earlier
                    # in the list
                    interval = portion.closed(*kernel.time)
                    interval_dicts[naif_id][interval] = kernel

            # Identify the full set of kernels needed to cover each NAIF ID
            if not time_is_constrained:
                (tmin, tmax) = Kernel.ALL_TIME
            times_required = portion.closed(tmin, tmax)

            reduced_set = set()
            for interval_dict in interval_dicts.values():
                coverage = interval_dict[times_required]
                reduced_set |= set(coverage.values())

            # Reorder the selected kernels
            kernels = [k for k in kernels if k in reduced_set]

        return [k.basename for k in kernels]

    @staticmethod
    def find_all(regex=None, ktype=None, versions=False, order=[]):
        """The list of existing basenames matching a particular pattern and/or of a
        particular type.

        Inputs:
            regex       if specified, only existing basenames matching this pattern will
                        be returned.
            ktype       if specified, only basenames associated with this ktype will be
                        returned. If the ktype can be inferred from the regex, it is
                        not necessary to specify it here.
            versions    True to sort basenames by version ID; False to alphabetically.
            order       if this is a list of basenames, then the order of names in the
                        list returned will match the order of names in the list given,
                        with any additional names inserted following the last occurrence
                        of a matching or earlier version ID.

        Example. Suppose these files all exist:
            "jup090.bsp", "jup100-a.bsp", "jup100-b.bsp", "jup120.bsp", "jup121.bsp"
        and these are the inputs:
            regex = r"jup(\\d\\d\\d).*\\.bsp"
            order = ["jup120.bsp", "jup100-a.bsp",  "jup100-c.bsp"]
        The returned list will be:
            ["jup090.bsp", "jup120.bsp", "jup100-a.bsp", "jup100-b.bsp", "jup121.bsp"]
        """

        def sort_key(basename):
            """Key for sorting versions. Integers and tuples of integers are sorted
            together. Strings sort as greater than integers or tuples. Missing versions
            sort last.
            """

            # If we're not using version sorting, just use the basename.
            if not versions:
                return basename

            version = KernelFile(basename).version
            if isinstance(version, numbers.Integral):
                return (0, version)
            if isinstance(version, tuple):
                return (0,) + version

            if not version:         # put basenames with unknown version last
                return (2, basename)

            return (1, version)

        if not isinstance(order, (list,tuple)):
            raise ValueError('invalid order type: ' + type(order).__name__)

        # Get the extension from the regex if possible; compile the regex
        if regex is None:
            ext = ''
        elif isinstance(regex, str):
            ext = '.' + regex.rpartition('.')[-1]
            regex = re.compile(regex)
        else:
            ext = '.' + regex.pattern.rpartition('.')[-1]

        # Filter by ktype and ext
        if ktype:
            basenames = _KernelInfo._BASENAMES_BY_KTYPE[ktype]
        elif ext in _EXTENSIONS:
            ktype = _EXTENSIONS[ext]
            basenames = _KernelInfo._BASENAMES_BY_KTYPE[ktype]
        else:
            basenames = _KernelInfo.ABSPATHS.keys()

        # Filter by regex
        if regex:
            basenames = [b for b in basenames if regex.fullmatch(b)]

        # If there's no order input, return the list sorted alphabetically
        if not order and not versions:
            basenames.sort()
            return basenames

        # Sort the found names to match the sorted list
        sorted_locals = [b for b in order if b in basenames]

        # If there are no extras, we're done
        if len(basenames) == len(sorted_locals):
            return sorted_locals

        # Identify the extra basenames, sort
        extras = [b for b in basenames if b not in sorted_locals]
        extras.sort(key=sort_key)

        # If no order was specified, we're done
        if not order:
            return extras

        # Merge the lists
        merged = sorted_locals
        vdict = {b:sort_key(b) for b in merged}

        for extra in extras:
            key = sort_key(extra)
            vdict[extra] = key
            where_le = [k for k,basename in enumerate(merged)
                        if vdict[basename] <= key]
            if where_le:
                merged.insert(max(where_le) + 1, extra)
            else:
                merged.append(extra)

        return merged

    ######################################################################################
    # Public API for identifying local SPICE files
    # Functions walk, use_path, and use_paths are defined in spyceman/_localfiles.py.
    ######################################################################################

    @staticmethod
    def initialize():
        """On first call, check the environment for a variable named "SPICEPATH" and walk
        that list of directories.
        """

        if _localfiles._ROOTS:
            return

        if 'SPICEPATH' in os.environ:
            roots = ':'.split(os.environ['SPICEPATH'])
            for root in roots:
                KernelFile.walk(root)

############################################################
# Include the _localfiles functions as class methods
############################################################

KernelFile.walk      = _localfiles.walk
KernelFile.use_path  = _localfiles.use_path
KernelFile.use_paths = _localfiles.use_paths
KernelFile._INITIALIZED = False

############################################################
# Enable the Kernel class to access this subclass
############################################################

Kernel.KernelFile = KernelFile

##########################################################################################
