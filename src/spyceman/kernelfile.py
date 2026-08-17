##########################################################################################
# spyceman/kernelfile.py
##########################################################################################
"""KernelFile is a subclass of Kernel that represents a single SPICE kernel file."""

import collections
import numbers
import re

import julian
import portion

from spyceman.kernel      import Kernel
from spyceman._downloads  import get_fancy_index_dates, retrieve_online_file
from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS
from spyceman._localfiles import _file_checksum, use_path, use_paths, walk
from spyceman._utils      import (_input_set, _input_list,  _test_version, is_basename,
                                  validate_naif_ids, validate_release_date, validate_time)

KTuple = collections.namedtuple('KTuple', ['basename', 'start_time', 'end_time',
                                           'naif_ids', 'release_date'])


class KernelFile(Kernel):
    """Kernel subclass representing a single SPICE kernel file.

    Properties:
        ktype (str): Type of kernel, e.g., "SPK", inferred from the file extension.
        naif_ids (set): The NAIF IDs referenced by this file, including any of their
            defined aliases. If the kernel is relevant to all NAIF IDs, this set is empty.
        naif_ids_wo_aliases (set): The primary NAIF IDs referenced by this file. If it
            references a body or frame by its alias, this is the primary ID rather than
            the one that appears in the file. If the kernel is relevant to all NAIF IDs,
            this set is empty.
        time (tuple[float or None, float or None]): Time coverage of this file as
            (start_time, stop_time). If this kernel is relevant to all times, this tuple
            is (None, None).
        release_date (str or None): The release date of this kernel in "yyyy-mm-dd"
            format; None if unknown.
        version (int, str, tuple[int, ...], or set): The kernel version as indicated by
            the name or content of the kernel file. If this kernel does not have a version
            number, the value is "". A file may be associated with multiple versions, in
            which case this attribute is a set.
        version_as_set (set): The version(s) as a set. If the kernel has only one version,
            this set will have a single element. If the version is an empty string, the
            set is empty.
        source (list[str]): A list of one or more URLs pointing to online directories that
            can be searched to download this file.
        dest (str): A sub-path defining where to place this file within the user's SPICE
            downloads directory.
        family (str): The family of kernels with which this file associated.
        properties (dict[str, Any]): A dictionary of any special properties for this
            kernel. Special properties are mission-specific. For example, one might define
            the property "voyager" for Voyager kernels, where the value is 1 for kernels
            specific to Voyager 1 and 2 for kernels specific to Voyager 2.
        exists (bool): True if this file exists in the local file system.
        abspath (str): The absolute path to this file if it exists. Otherwise, an empty
            string.
        is_known (bool): True if this file is known to exist, although perhaps only
            online.
        ext (str): The file extension, including the period.
        is_text (bool): True if this is a text kernel.
        is_binary (bool): True if this is a binary kernel.
        checksum (int): The Adler 32 checksum of this file.
        label_abspath (str): The path to the PDS label of this file, if it has a label;
            otherwise, "".
        label (list[str]): The text content of the label as a list of strings.
        comments (list[str]): The embedded comments of this file as a list of strings.
        text (list[str]): The entire content of this file if it is a text kernel.
        text_content (list[str]): The data content of a text kernel.
        text_comments (list[str]): All the non-data content of a text kernel.
        dict_content (dict): The content of this text kernel as returned by `textkernel`.
        meta_basenames (list): The files referenced by this metakernel.

    Notes:
        Most of these properties are evaluated lazily, which means that they are only
        derived when needed. However, all of these attributes of a KernelFile are global,
        so if two different KernelFile objects refer to the same basename, they will have
        access to the same information.

        In many cases, some of this information is derived directly from a file or its
        name using "Rules". Users can override these properties by setting their values
        explicitly.

        All SPICE kernel basenames must be unique. Initial calls to `KernelFile.walk()`,
        `KernelFile.use_path()`, and/or `KernelFile.use_paths()` will associate basenames
        with their paths in the user's local file system.

        Note that a KernelFile can be constructed for a file basename that does not
        currently exist. If the file is needed, it will be downloaded from one of its
        defined `source` URLs and saved to the directory defined by its `dest` attribute.
    """

    _is_ordered = False     # fixed value for every instance of this subclass

    def __init__(self, basename, *, exists=False, **properties):
        """Construct a KernelFile object.

        All the attributes of a KernelFile are global to the basename, so two KernelFile
        objects referring to the same basename share the same information. A KernelFile
        can be constructed for a file that does not exist locally; it cannot be furnished
        until a local copy exists.

        Parameters:
            basename (str, KernelFile): Basename of a SPICE kernel file, or an existing
                KernelFile object to copy.
            exists (bool, optional): True to require that a local copy of this file
                already exist, raising if it does not. This asserts a precondition; it
                does not fetch anything. Call must_exist() to download a missing file.
            **properties: Names and values of additional attributes or properties to
                assign to this KernelFile.
        """

        if isinstance(basename, KernelFile):
            basename = basename._basename

        self._basename = basename

        if properties:
            KernelFile.set_info([self], **properties)

        if exists and basename not in _KernelInfo.ABSPATHS:
            raise FileNotFoundError('kernel file not found: ' + repr(basename))

    def must_exist(self, *, source='', dest='', verbose=True):
        """Ensure that this file exists locally, downloading it if necessary.

        Each source URL is tried in turn until one yields the file. If downloads are
        disabled, a missing file is an error.

        Parameters:
            source (str, list[str], optional): Override for this file's default source URL
                or URLs.
            dest (str, optional): Override for this file's default local destination
                directory.
            verbose (bool, optional): True to print information about downloads as they
                occur.

        Raises:
            FileNotFoundError: If the file is missing and downloads are disabled, or if
                no source directory contains it.
            ConnectionError: If every source that lists the file failed to deliver it.
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
                raise FileNotFoundError(f'no identified source for "{self.basename}"')

            # Use this new file
            use_path(destpath)

        else:
            raise FileNotFoundError(f'missing kernel file: "{self.basename}"')

    @staticmethod
    def set_info(info, **properties):
        """Set attributes or properties of one or more KernelFiles.

        Given a KTuple, the time limits, NAIF IDs, and release date it carries are
        assigned to the corresponding KernelFile before any additional properties are
        applied.

        Parameters:
            info (KernelFile, KTuple, str, list): One KernelFile, KTuple, or basename, or
                a list of them, for which attributes are to be defined.
            **properties: Names and values of the attributes or properties to assign.
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
                    kernel.add_property(name, value)

    ######################################################################################
    # Required properties
    ######################################################################################

    @property
    def _info(self):
        """The _KernelInfo object associated with this KernelFile object's basename.

        This is a property and is constructed anew if necessary.

        Returns:
            _KernelInfo: The unique object holding this basename's attributes.
        """
        return _KernelInfo.lookup(self._basename)

    def _hash_key(self):
        """Identifying data for hashing, consistent with __eq__.

        Every other attribute of a KernelFile lives in the global _KernelInfo keyed by
        this basename, so the basename alone identifies it, and it is fixed at
        construction.

        Returns:
            tuple: The class name and this file's basename.
        """

        return (type(self).__name__, self._basename)

    @property
    def basename(self):
        """The basename of the kernel file described by this KernelFile object.

        Returns:
            str: The basename of this kernel file.
        """
        return self._basename

    @property
    def basenames(self):
        """All the kernel file basenames associated with this Kernel object.

        Returns:
            list[str]: A single-element list containing this file's basename.
        """
        return [self.basename]

    @property
    def name(self):
        """The name of this Kernel object.

        For KernelFile objects, this is always equivalent to its basename.

        Returns:
            str: The basename of this file.
        """
        return self.basename

    @property
    def ktype(self):
        """The kernel type of this file: "SPK", "CK", "LSK", etc.

        Returns:
            str: The kernel type, inferred from the file extension.
        """
        return self._info.ktype

    @property
    def naif_ids(self):
        """The set of NAIF IDs covered by this file, including aliases.

        Returns:
            set[int]: The NAIF IDs this file covers, including every alias. The set is
                empty if the kernel applies to all NAIF IDs.
        """
        return self._info.naif_ids

    @naif_ids.setter
    def naif_ids(self, ids):
        """Define the set of NAIF IDs covered by this file.

        Parameters:
            ids (int, set[int]): The NAIF ID or IDs to assign.
        """

        self._info.naif_ids = ids

    def add_naif_ids(self, *ids):
        """Add one or more NAIF IDs to this KernelFile.

        Parameters:
            *ids (int): One or more NAIF IDs to add.
        """
        self._info.add_naif_ids(*ids)

    def remove_naif_ids(self, *ids):
        """Remove one or more NAIF IDs from this KernelFile.

        Parameters:
            *ids (int): One or more NAIF IDs to remove.
        """
        self._info.remove_naif_ids(*ids)

    @property
    def naif_ids_wo_aliases(self):
        """The set of all NAIF IDs described by the file, excluding aliases.

        Returns:
            set[int]: The primary NAIF IDs this file covers. The set is empty if the
                kernel applies to all NAIF IDs.
        """
        return self._info.naif_ids_wo_aliases

    @property
    def naif_ids_as_found(self):
        """The exact set of NAIF IDs described by the file, before aliases are handled.

        Returns:
            set[int]: The NAIF IDs exactly as they appear in the file, before any alias
                was resolved to its primary ID.
        """
        return self._info.naif_ids_as_found

    @property
    def time(self):
        """Time limits of this kernel file as a tuple of two times in seconds TDB.

        Returns:
            (float, float), (None, None): The earliest and latest times covered by this
                file, in seconds TDB; (None, None) if it applies to all times.
        """
        return self._info.time

    @time.setter
    def time(self, value):
        """Define the time limits of this kernel file.

        Parameters:
            value ((float, float), (str, str)): The start and stop times, each given in
                seconds TDB or as a date-time string.
        """

        self._info.time = value

    @property
    def tmin(self):
        """The lower time limit of this file in seconds TDB.

        Returns:
            float, None: The earliest time covered by this file, in seconds TDB; None if
                the kernel applies to all times.
        """
        return self._info.time[0]

    @property
    def tmax(self):
        """The upper time limit of this file in seconds TDB.

        Returns:
            float, None: The latest time covered by this file, in seconds TDB; None if
                the kernel applies to all times.
        """
        return self._info.time[1]

    @property
    def release_date(self):
        """Release date of this kernel file as an ISO date string.

        Returns:
            str: The release date as "yyyy-mm-dd"; an empty string if it is unknown.
        """
        return self._info.release_date

    @release_date.setter
    def release_date(self, value):
        """Define the release date of this kernel file.

        Parameters:
            value (str): The release date in nearly any recognizable format; an empty
                string or None if the release date is unknown.
        """

        if not value:
            self._info._release_date = ''
            return

        self._info.release_date = julian.format_day(julian.day_from_string(value))

    @property
    def version(self):
        """Version of this kernel file.

        Returns:
            int, str, tuple[int, ...], set: The version of this file, expressed as an
                integer, a string, or a tuple of integers for a version using decimal
                points. A file associated with several versions returns a set of them,
                and one with no version returns an empty string.
        """
        return self._info.version

    @property
    def version_as_set(self):
        """Version or versions of this kernel file, expressed as a set.

        Returns:
            set: The version or versions of this file. The set holds one element if the
                file has a single version, and is empty if it has none.
        """
        return self._info.version_as_set

    @version.setter
    def version(self, value):
        """Define the version of this kernel file.

        Parameters:
            value (int, str, tuple, set): The version to assign.
        """

        self._info.version = value

    @property
    def family(self):
        """The family name of this kernel.

        Kernels with a different version or time range are often members of the same
        family.

        Returns:
            str: The family name of this kernel file.
        """
        return self._info.family

    @family.setter
    def family(self, value):
        """Define the family name of this kernel.

        Parameters:
            value (str): The family name to assign.
        """

        self._info.family = str(value)

    @property
    def source(self):
        """One or more URLs to search for this file online.

        Returns:
            list[str]: The URLs of online directories that might contain this file.
        """
        return self._info.source

    @source.setter
    def source(self, value):
        """Define the URLs to search for this file online.

        Parameters:
            value (str, list[str]): One URL, or a list of them.
        """

        self._info.source = value

    @property
    def dest(self):
        """The sub-path within the SPICE downloads directory for this file.

        Returns:
            str: The subdirectory in which this file is placed when downloaded.
        """
        return self._info.dest

    @dest.setter
    def dest(self, value):
        """Define the sub-path within the SPICE downloads directory for this file.

        Parameters:
            value (str): The subdirectory to use.
        """

        self._info.dest = value

    @property
    def properties(self):
        """The dictionary of special properties for this Kernel.

        Returns:
            dict: The name and value of each special property of this kernel file.
        """
        return self._info.properties

    def add_property(self, name, value):
        """Add or modify a property, same as "self.properties[name] = value".

        Parameters:
            name (str): Name of the property.
            value (object): Value of the property.
        """
        self._info.add_property(name, value)

    def remove_property(self, name):
        """Remove a property, same as "del self.properties[name]".

        Parameters:
            name (str): Name of the property to remove.
        """
        self._info.remove_property(name)

    ######################################################################################
    # Public properties specific to KernelFile objects
    ######################################################################################

    @property
    def abspath(self):
        """Absolute path to this KernelFile.

        Returns:
            str: The absolute path to this file on the local filesystem; an empty string
                if no local copy exists.
        """
        return self._info.abspath

    @property
    def exists(self):
        """True if this kernel file exists.

        Returns:
            bool: True if a local copy of this file exists.
        """
        return self._info.exists

    @property
    def is_known(self):
        """True if this kernel file basename has been defined.

        Returns:
            bool: True if information about this basename has been registered, even if
                no local copy of the file exists.
        """
        return self._info.is_known

    @property
    def ext(self):
        """File extension of this file.

        Returns:
            str: The file extension, including the leading period.
        """
        return '.' + self.basename.rpartition('.')[-1]

    @property
    def is_text(self):
        """True if this is a text kernel file.

        Returns:
            bool: True if this file is a text kernel; False if it is binary.
        """
        return self._info.is_text

    @property
    def is_binary(self):
        """True if this is a binary kernel file.

        Returns:
            bool: True if this file is a binary kernel; False if it is text.
        """
        return self._info.is_binary

    @property
    def checksum(self):
        """Adler 32 checksum of the file.

        Returns:
            int: The Adler 32 checksum of this file's content.

        Raises:
            FileNotFoundError: If no local copy of this file exists.
        """
        if not self.exists:
            raise FileNotFoundError(f'kernel file not found: "{self.basename}"')

        return _file_checksum(self.abspath)

    @property
    def label_abspath(self):
        """Absolute path to the PDS label of this file, if any.

        Returns:
            str: The absolute path to this file's PDS label; an empty string if it has no
                label.
        """
        return self._info.label_abspath

    @property
    def label(self):
        """Content of the PDS label, if any, as a list of strings.

        Returns:
            list[str]: The lines of this file's PDS label; an empty list if it has no
                label.
        """
        return self._info.label

    @property
    def comments(self):
        """Any available comments as a list of strings.

        Returns:
            list[str]: The comment records embedded in this file or in an accompanying
                comment file; an empty list if none are available.
        """
        return self._info.comments

    @property
    def text(self):
        """Content of a text kernel as a list of strings.

        Returns:
            list[str]: Every line of this file if it is a text kernel; an empty list if it
                is binary.
        """
        return self._info.text

    @property
    def text_content(self):
        """Data content of a text kernel as a list of strings.

        Returns:
            list[str]: The data lines of this file, meaning those inside a \\begindata
                section; an empty list if the file is binary.
        """
        return self._info.text_content

    @property
    def text_comments(self):
        """All comments embedded within a text kernel as a list of strings.

        Returns:
            list[str]: The non-data lines of this file; an empty list if the file is
                binary.
        """
        return self._info.text_comments

    @property
    def dict_content(self):
        """Content of this text kernel as parsed into a textkernel dictionary.

        Returns:
            dict: The parsed content of this text kernel; an empty dictionary if the file
                is binary.
        """
        return self._info.dict_content

    @property
    def meta_basenames(self):
        """The list of enclosed basenames if this is a metakernel.

        Returns:
            list[str]: The basenames this metakernel refers to; an empty list if this
                file is not a metakernel.
        """
        return self._info.meta_basenames

    ######################################################################################
    # Public API for selecting and sorting kernel files
    ######################################################################################

    @staticmethod
    def reduce(basenames, *, tmin=None, tmax=None, ids=None):
        """Reduce a list of basenames or KernelFiles to the minimal list that provides
        complete coverage.

        A file whose entire time coverage for every relevant NAIF ID is superseded by
        files later in the list is dropped, because those later files take precedence
        wherever they overlap.

        Parameters:
            basenames (list[str], list[KernelFile]): An ordered list of basenames or
                KernelFiles, in increasing order of precedence.
            tmin (float, optional): Earliest time to be covered, in seconds TDB; None to
                use the earliest time covered by the given files.
            tmax (float, optional): Latest time to be covered, in seconds TDB; None to
                use the latest time covered by the given files.
            ids (set[int], optional): The NAIF IDs that must be covered; None to use
                every ID covered by the given files.

        Returns:
            list[str], list[KernelFile]: The reduced list, in the same order and of the
                same element type as the input.
        """

        if not basenames:
            return []

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
                tmax = BIGTIME

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
                    t1 = BIGTIME

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
        version, release date, and/or property values.

        A file that does not define a property named in the filter is retained rather
        than rejected, on the grounds that an unknown value cannot be ruled out. The same
        applies to a file with no known release date.

        Parameters:
            basenames (list[str], list[KernelFile]): The basenames or KernelFiles to
                filter, in increasing order of precedence.
            tmin (float, str, optional): Only include files whose coverage extends to or
                beyond this time, in seconds TDB or as a date-time string.
            tmax (float, str, optional): Only include files whose coverage begins at or
                before this time, in seconds TDB or as a date-time string.
            ids (int, set[int], optional): Only include files that refer to one or more
                of these NAIF IDs.
            name (str, list, set, tuple, optional): Only include files matching this
                basename or regular expression, or one of these. A string containing only
                letters, numbers, underscore, dash, and dot is treated as a literal
                basename rather than as a pattern.
            version (int, str, tuple, set, list, optional): Only include files matching
                this version. Use a set for several acceptable versions, or a list of two
                values for an inclusive range in which either limit may be None.
            release_date (str, list, tuple, optional): Only include files consistent with
                this release date. Use a list or tuple of two dates for a range, in which
                either may be None or empty; a single date is the upper limit.
            expand (bool, optional): True to widen the returned list where necessary so
                that the entire time range is covered for every specified NAIF ID, even
                if that violates the constraints on name, version, and release date.
            reduce (bool, optional): True to drop any file whose coverage is eclipsed by
                files later in the list.
            flags (RegexFlag, optional): Compile flags for any regular expression;
                default is re.IGNORECASE.
            **properties: Additional constraints on property values. Place multiple
                acceptable values in a list, set, or tuple.

        Returns:
            list[str], list[KernelFile]: The filtered list, in the same order and of the
                same element type as the input.
        """

        def filter_by_name(name, kfiles):
            """Select the kernel files matching one of the given names or patterns.

            Parameters:
                name (str, list, set, tuple, optional): One basename or regular
                    expression, or a collection of them; an empty input selects
                    everything.
                kfiles (list[KernelFile]): The candidate kernel files.

            Returns:
                list[KernelFile]: The matching files, in their original order.
            """

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
            """Select the kernel files whose version satisfies the given constraint.

            Parameters:
                version (int, str, tuple, set, list, optional): The version constraint; an
                    empty input selects everything.
                kfiles (list[KernelFile]): The candidate kernel files.

            Returns:
                list[KernelFile]: The matching files, in their original order.
            """

            if not version:
                return kfiles

            return [k for k in kfiles if _test_version(version, k)]

        def filter_by_release_date(release_date, kfiles):
            """Select the kernel files whose release date falls within the given range.

            A file with no known release date is retained.

            Parameters:
                release_date (list, tuple, optional): The earliest and latest acceptable
                    release dates, either of which may be None or empty; an empty input
                    selects everything.
                kfiles (list[KernelFile]): The candidate kernel files.

            Returns:
                list[KernelFile]: The matching files, in their original order.
            """

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
            """Select the kernel files whose property values are among those requested.

            A file that does not define one of the named properties is retained.

            Parameters:
                properties (dict): The acceptable values for each named property; an empty
                    input selects everything.
                kfiles (list[KernelFile]): The candidate kernel files.

            Returns:
                list[KernelFile]: The matching files, in their original order.
            """

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
        if not basenames:
            return []

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

            # Find the highest location of a filtered file in the unfiltered list.
            # The filters may have removed everything, which is exactly the case expand
            # exists to recover from, so start from the end of the unfiltered list.
            maxloc = unfiltered.index(kfiles[-1]) if kfiles else len(unfiltered)

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

        Parameters:
            pattern (str, re.Pattern, list, tuple, set, optional): Only return basenames
                matching this name or pattern, or one of these; None to return every
                known basename.
            ktype (str, optional): Only return basenames of this kernel type. It is not
                necessary to give this if the ktype can be inferred from the pattern.
            exists (bool, optional): True to return only basenames present in the local
                file system.
            sort (str, function, optional): How to sort the result: "alpha" to sort
                alphabetically, "version" to sort by version, "date" to sort by release
                date, or a function mapping a basename to its sort key.
            flags (RegexFlag, optional): Compile flags for the regular expression;
                default is re.IGNORECASE.

        Returns:
            list[str]: The matching basenames, sorted as requested.
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
                    sources = _KernelInfo.BASENAMES_BY_KTYPE[ktype]
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

        Parameters:
            option (str, function): "alpha" to sort basenames alphabetically and without
                regard to case, "version" to sort by version and then alphabetically,
                "date" to sort by release date and then alphabetically, or a function to
                use as the sort key directly.

        Returns:
            function: A function mapping a basename to its sort key.

        Raises:
            ValueError: If the option is neither a recognized name nor a callable.
        """

        def version_sort_key(basename):
            """Key for sorting versions.

            Integers and tuples of integers sort together. Strings sort above them.
            Missing versions sort lowest.

            Parameters:
                basename (str): Basename of the kernel file to be sorted.

            Returns:
                tuple: The sort key for this basename's version.
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

    # "\1" or "\g<name>": a reference to a group captured by the triggering pattern.
    _GROUP_REFERENCE = re.compile(r'\\(?:\d|g<)')

    @staticmethod
    def mutual_veto(*patterns, flags=re.IGNORECASE):
        """Ensure that at most one file matching these patterns is furnished at a time.

        When a kernel whose basename matches one of the given patterns is furnished, any
        overlapping kernel matching one of the patterns is unloaded.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.

        Parameters:
            *patterns (str, re.Pattern): The basenames or regular expressions that veto
                one another.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
        """

        patterns = KernelFile._compile(patterns, flags=flags, subs=False)
            # this is a list of patterns

        for pattern in patterns:
            KernelFile._VETOS.append([pattern] + patterns)

    @staticmethod
    def group_vetos(*patterns, flags=re.IGNORECASE):
        """Ensure that kernels matching one group veto those matching the others.

        When a kernel whose basename matches any of the given patterns is furnished, any
        overlapping kernel matching one of the *other* patterns is unloaded. Patterns
        within one group do not veto each other.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.

        Parameters:
            *patterns (str, re.Pattern, list, set, tuple): One group per argument; a group
                may be a single pattern or a collection of them.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
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
        """Ensure that kernels matching the first pattern veto those matching the rest.

        When a kernel whose basename matches the first pattern is furnished, any
        overlapping kernel matching one of the veto patterns is unloaded.

        A veto is similar to an exclusion, but exclusions are specific to Kernel objects.
        Vetos apply globally, taking effect any time a basename is furnished.

        Parameters:
            patterns (str, re.Pattern, list, set, tuple): The basename or regular
                expression that triggers the veto, or a collection of them. Capturing
                groups here can be referenced from the veto patterns.
            *vetos (str, re.Pattern): The basenames or regular expressions to be unloaded,
                which may contain backreferences to the triggering pattern.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
        """

        patterns = KernelFile._compile(patterns, flags=flags, subs=False)
        vetos = KernelFile._compile(vetos, flags=flags, subs=True)
        # Each is a list of patterns

        for pattern in patterns:
            KernelFile._VETOS.append([pattern] + vetos)

    @staticmethod
    def shadow(front, *behind, flags=re.IGNORECASE):
        """Ensure that kernels matching the first pattern outrank those matching the rest.

        When a kernel whose basename matches the first pattern is furnished, it is given
        a higher precedence than any overlapping kernel matching the later patterns.

        Parameters:
            front (str, re.Pattern, list, set, tuple): The basename or regular expression
                to be furnished at higher precedence, or a collection of them. Capturing
                groups here can be referenced from the "behind" patterns.
            *behind (str, re.Pattern): The basenames or regular expressions to be
                furnished at lower precedence.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
        """

        front  = KernelFile._compile(front,  flags=flags)
        behind = KernelFile._compile(behind, flags=flags)
            # Each is a list of patterns

        for pattern in front:
            KernelFile._SHADOWS.append([pattern] + behind)

    @staticmethod
    def _compile(patterns, *, flags=re.IGNORECASE, subs=False):
        """Convert one pattern or list of patterns to a list of compiled patterns.

        Parameters:
            patterns (str, re.Pattern, list, set, tuple): One pattern or a collection of
                them. A literal basename is escaped before compiling.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
            subs (bool, optional): True to return a pattern that cannot be compiled as
                the tuple (string, flags), so that it can later be expanded against a
                match; False to let the compilation error propagate.

        Returns:
            list: The compiled patterns, with any replacement pattern represented by a
                tuple (string, flags) instead of an re.Pattern.

        Raises:
            re.error: If a pattern cannot be compiled and subs is False.
        """

        if not isinstance(patterns, (list, set, tuple)):
            patterns = (patterns,)

        result = []
        for pattern in patterns:
            if not isinstance(pattern, re.Pattern):
                if is_basename(pattern):    # convert a basename to a regular expression
                    pattern = pattern.replace('.', r'\.')

                # A replacement template such as r'\1_.*\.bc' is a perfectly valid
                # regular expression -- "\1" is a backreference -- so it cannot be
                # recognized by trying to compile it. Keep it as (string, flags) whenever
                # substitution was asked for and the pattern carries a group reference.
                if subs and KernelFile._GROUP_REFERENCE.search(pattern):
                    pattern = (pattern, flags)
                else:
                    pattern = re.compile(pattern, flags=flags)

            result.append(pattern)

        return result

    @staticmethod
    def _get_vetos_or_shadows(basename, source):
        """The list of compiled regular expressions that match this basename.

        Parameters:
            basename (str): A kernel file basename.
            source (list[list]): The veto or shadow table, each entry being a list whose
                first element is the triggering pattern and whose remaining elements are
                the patterns it applies to.

        Returns:
            list[re.Pattern]: Every pattern triggered by this basename, with any
                replacement pattern expanded against the triggering match.
        """

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
        """The list of compiled regular expressions that this basename vetos.

        Parameters:
            basename (str): A kernel file basename.

        Returns:
            list[re.Pattern]: All the compiled regular expressions that match basenames
                which the given basename vetos.
        """

        return KernelFile._get_vetos_or_shadows(basename, source=KernelFile._VETOS)

    @staticmethod
    def _get_shadows(basename):
        """The regular expressions that this basename shadows.

        Parameters:
            basename (str): A kernel file basename.

        Returns:
            list[re.Pattern]: All the compiled regular expressions that match basenames
                which the given basename shadows.
        """

        return KernelFile._get_vetos_or_shadows(basename, source=KernelFile._SHADOWS)

##########################################################################################
# Include the initialize functions as class methods
##########################################################################################

KernelFile.walk      = walk
KernelFile.use_path  = use_path
KernelFile.use_paths = use_paths

##########################################################################################
# Enable the Kernel class to access this subclass
##########################################################################################

Kernel.KernelFile = KernelFile

##########################################################################################
