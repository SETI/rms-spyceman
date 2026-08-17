##########################################################################################
# spyceman/kernel.py
##########################################################################################
"""Definition of the abstract Kernel class."""

import julian
import numbers
import numpy as np
import re

from spyceman._cspyce     import CSPYCE
from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _KTYPES
from spyceman._utils      import (is_basename, basename_ktype, validate_iso_time,
                                  validate_version)

# Dictionary ktype -> ordered list of basenames currently furnished in cspyce
_FURNISHED_BASENAMES = {key:[] for key in _KTYPES}


class Kernel(object):
    """Kernel is an abstract class that defines one or more SPICE kernel files and the
    rules for how to to furnish them.

    Attributes:
        name (str):
            A name string for this kernel.
        ktype (str):
            The type of this kernel: "CK", "SPK", "LSK", etc.
        naif_ids (set[int]):
            The NAIF IDs covered by this kernel, including aliases; an empty set if the
            kernel applies to all NAIF IDs.
        naif_ids_wo_aliases (set[int]):
            The NAIF IDs covered by this kernel, excluding aliases; an empty set if the
            kernel applies to all NAIF IDs.
        time ((float, float) or (None, None)):
            Time limits as a tuple of two times in seconds TDB; (None, None) if this
            kernel applies to all times.
        release_date (str):
            Release date as an ISO date string "yyyy-mm-dd"; an empty string if no release
            date is known.
        version (int, str, or tuple[int, ...]):
            Version of this kernel file; an empty string if the version is undefined. A
            version using decimal points (e.g., 1.2.3) is represented by a tuple of ints.
        family (str):
            The family name for this kernel; in general, version IDs refer to different
            kernels within the same family.
        properties (dict):
            Additional name/value pairs that are relevant to this Kernel. For example,
            properties['mission'] = 'Cassini'.
        basenames (list[str]):
            All the kernel file basenames managed by this Kernel.
        is_ordered (bool):
            True if this uses an ordered list of kernel files, meaning that later kernels
            take precedence over earlier ones.
        exclusions (set[str or Kernel]):
            Excluded Kernel objects or basenames. When this kernel is furnished, it is
            guaranteed that any exclusions will be unloaded.
        prerequisites (set[str or Kernel]):
            Kernel objects or basenames that will always be furnished at a lower
            precedence when this kernel is furnished.
        postrequisites (set[str or Kernel]):
            Kernel objects or basenames that will always be furnished at a higher
            precedence when this kernel is furnished.
        corequisites (set[str or Kernel]):
            Kernel objects of a different ktype that will always be furnished when this
            kernel is furnished. Because their ktype differs from that of this ktype,
            their precedence level does not matter.

    Methods:
        exclude(): Add one or more kernels to the set of exclusions.
        require(): Add one or more kernels to the set of pre-, post-, or co-requisites.
        furnish(): Furnish this kernel within a specified range of times and/or for a
            specified set of NAIF IDs.
        unload(): Unload this kernel within a specified range of times and/or for a
            specified set of NAIF IDs.
        used(): An ordered list of kernel basenames that are furnished for a specified
            range of times and/or for a specified set of NAIF IDs.
    """

    # These class definitions are initialized when the associated subclass is imported;
    # this is needed in order to avoid circular imports
    KernelFile = None
    Metakernel = None

    DT = 1.5 * 86400.   # seconds of buffer around the time limits of any kernel

    def __str__(self):
        """A brief string representation of this Kernel.

        Returns:
            str: The class name followed by this kernel's name in quotes.
        """

        return type(self).__name__ + '("' + self.name + '")'

    def __repr__(self):
        """A brief string representation of this Kernel.

        Returns:
            str: The class name followed by this kernel's name in quotes.
        """

        return self.__str__()

    def __copy__(self):
        """A shallow copy of this Kernel.

        Returns:
            Kernel: A new object of the same class, sharing this one's attributes.
        """

        new = type(self).__new__(type(self))
        new.__dict__ = self.__dict__.copy()
        return new

    def __eq__(self, arg):
        """True if this Kernel is equivalent to another.

        Two Kernels are equal if they are the same object, or if they are of the same
        class and all their attributes match.

        Parameters:
            arg (object): The object to compare against.

        Returns:
            bool: True if the two Kernels are equivalent.
        """

        if self is arg:         # this is the quickest test
            return True

        if not isinstance(arg, Kernel):
            return False

        return (type(self) is type(arg) and self.__dict__ == arg.__dict__)

    def _hash_key(self):
        """Identifying data for hashing, consistent with __eq__.

        __eq__ compares the whole instance dictionary, which is mutable and holds lazily
        cached values, so it cannot be hashed directly. A subclass overrides this with
        whatever immutable data identifies it; the requirement is only that two objects
        which compare equal produce equal keys. The default is the class alone, which is
        always safe and simply puts every instance of that class in one bucket.

        Returns:
            tuple: A hashable key for this Kernel.
        """

        return (type(self).__name__,)

    def __hash__(self):
        """A hash consistent with __eq__.

        Kernel objects are held in sets throughout -- exclusions, pre-, post- and
        co-requisites -- so they must be hashable. Note that a Kernel mutated after it
        enters a set may not be found there again, which is the usual caveat for a
        mutable object used as a set member.

        Returns:
            int: The hash of this Kernel's identifying data.
        """

        return hash(self._hash_key())

    @staticmethod
    def as_kernel(kernel):
        """Return this input as a subclass of Kernel.

        Parameters:
            kernel (Kernel, str): A Kernel object, or a basename to be interpreted as a
                KernelFile.

        Returns:
            Kernel: The input itself if it is already a Kernel; otherwise a new KernelFile
                for the given basename.

        Raises:
            TypeError: If the input is neither a Kernel nor a string.
        """

        if isinstance(kernel, Kernel):
            return kernel
        if not isinstance(kernel, str):
            raise TypeError('not a Kernel object: ' + repr(kernel))

        return Kernel.KernelFile(kernel)

    ######################################################################################
    # Global operating modes
    ######################################################################################

    _DOWNLOADS = True
    _DEBUG = False
    _VERBOSE = False

    @staticmethod
    def download(status=None):
        """Set and/or return the download status.

        Parameters:
            status (bool, optional): True to permit missing files to be downloaded, False
                to forbid it; None to query the setting without changing it.

        Returns:
            bool: The download status now in effect.
        """

        if status is None:
            status = Kernel._DOWNLOADS

        status = bool(status)
        Kernel._DOWNLOADS = status
        return status

    @staticmethod
    def debug(status=None):
        """Set and/or return the debug status.

        In debug mode, kernels are tracked but never actually furnished or unloaded in the
        SPICE toolkit.

        Parameters:
            status (bool, optional): True to enable debug mode, False to disable it; None
                to query the setting without changing it.

        Returns:
            bool: The debug status now in effect.
        """

        if status is None:
            status = Kernel._DEBUG

        status = bool(status)
        Kernel._DEBUG = status
        return status

    @staticmethod
    def verbose(status=None):
        """Set and/or return the verbose status.

        In verbose mode, each furnish and unload is reported to standard output.

        Parameters:
            status (bool, optional): True to enable verbose mode, False to disable it;
                None to query the setting without changing it.

        Returns:
            bool: The verbose status now in effect.
        """

        if status is None:
            status = Kernel._VERBOSE

        status = bool(status)
        Kernel._VERBOSE = status
        return status

    ######################################################################################
    # Standard properties, overridden where necessary
    ######################################################################################

    @property
    def basenames(self):
        """The ordered list of basenames associated with this Kernel object.

        Returns:
            list[str]: The basenames of this kernel, in increasing order of precedence.
                Pre-, post-, and co-requisites are excluded.
        """

        return self._basenames

    @property
    def is_ordered(self):
        """True if this Kernel's basename list is ordered by precedence.

        Returns:
            bool: True if later basenames must take precedence over earlier ones.
        """

        return self._is_ordered

    @property
    def name(self):
        """The name for this kernel.

        If no name was assigned, one is derived from the family names of the kernel files
        this object manages.

        Returns:
            str: The name of this kernel.
        """

        if not hasattr(self, '_name') or not self._name:
            kernels = [Kernel.KernelFile(b) for b in self._basenames]
            families = [k.family or k.basename for k in kernels]
            self._name = Kernel._common_name(families) or 'UNNAMED'

        return self._name

    @name.setter
    def name(self, value):
        """Assign a name to this kernel.

        Parameters:
            value (str): The name to assign. It is for user convenience and need not be
                unique.
        """

        self._name = str(value)

    @property
    def ktype(self):
        """Kernel type of this file: "SPK", "CK", "LSK", etc.

        Returns:
            str: The kernel type, taken from the first of this kernel's basenames.
        """

        if not hasattr(self, '_ktype') or self._ktype is None:
            self._ktype = Kernel.as_kernel(self.basenames[0]).ktype

        return self._ktype

    @property
    def naif_ids(self):
        """The set of NAIF IDs covered by this kernel, including aliases.

        Returns:
            set[int]: The union of the NAIF IDs covered by this kernel's files, including
                every alias. The set is empty if the kernel applies to all NAIF IDs.
        """

        if not hasattr(self, '_naif_ids') or self._naif_ids is None:
            self._naif_ids = Kernel._naif_ids_for_kernels(self.basenames,
                                                          wo_aliases=False)

        return self._naif_ids

    @property
    def naif_ids_wo_aliases(self):
        """The set of NAIF IDs covered by this kernel, excluding aliases.

        Returns:
            set[int]: The union of the primary NAIF IDs covered by this kernel's files.
                The set is empty if the kernel applies to all NAIF IDs.
        """

        if not hasattr(self, '_naif_ids_wo_aliases') or self._naif_ids_wo_aliases is None:
            self._naif_ids_wo_aliases = Kernel._naif_ids_for_kernels(self.basenames,
                                                                     wo_aliases=True)

        return self._naif_ids_wo_aliases

    @property
    def time(self):
        """Time limits of this kernel as a tuple of two times in seconds TDB.

        Returns:
            (float, float), (None, None), None: The earliest and latest times covered by
                this kernel's files, in seconds TDB; (None, None) if none of them has a
                time dependence; None if this kernel has no files.
        """

        if not hasattr(self, '_time') or self._time is None:
            self._time = Kernel._time_for_kernels(self.basenames)

        return self._time

    @property
    def release_date(self):
        """Release date of this kernel as an ISO date string.

        Returns:
            str: The latest release date among this kernel's files, as "yyyy-mm-dd"; an
                empty string if no release date is known.
        """

        if not hasattr(self, '_release_date') or self._release_date is None:
            self._release_date = Kernel._release_date_for_kernels(self.basenames)

        return self._release_date

    @property
    def version(self):
        """Version of this kernel.

        Returns:
            int, str, tuple[int, ...], set: The highest version among this kernel's files.
                A mixture of strings and integers or tuples returns the set of both
                maxima, and no version at all returns an empty string.
        """

        if not hasattr(self, '_version') or self._version is None:
            self._version = Kernel._version_for_kernels(self.basenames)

        return self._version

    @version.setter
    def version(self, value):
        """Define the version of this kernel.

        Parameters:
            value (int, str, tuple, set): The version to assign.
        """

        self._version = validate_version(value)

    @property
    def family(self):
        """The family name of this kernel object.

        Kernels with a different version or time range are often members of the same
        family.

        Returns:
            str: The family name of this kernel.
        """

        if not hasattr(self, '_family') or self._family is None:
            self._family = self.name

        return self._family

    @family.setter
    def family(self, value):
        """Define the family name of this kernel object.

        Parameters:
            value (str): The family name to assign.
        """

        self._family = str(value)

    @property
    def properties(self):
        """The dictionary of special properties for this Kernel.

        Returns:
            dict: The merged properties of this kernel's files. A property with one value
                across all of them maps to that value; a property with several maps to
                the set of them.
        """

        if not hasattr(self, '_properties') or self._properties is None:
            self._properties = Kernel._properties_for_kernels(self.basenames)

        return self._properties

    ######################################################################################
    # Exclusions and pre-, post-, co-requisites
    ######################################################################################

    @property
    def exclusions(self):
        """The set of excluded kernel file basenames for this kernel.

        Returns:
            set[str, Kernel]: The basenames and Kernel objects guaranteed to be unloaded
                whenever this kernel is furnished.
        """

        if not hasattr(self, '_exclusions'):
            self._exclusions = set()

        return self._exclusions

    def exclude(self, *kernels):
        """Exclude one or more kernels from being furnished alongside this one.

        Parameters:
            *kernels (Kernel, str): The Kernel objects, kernel file basenames, or regular
                expressions matching basenames to exclude.

        Raises:
            ValueError: If one of the kernels is a metakernel.
        """

        self._add_to_set(self.exclusions, self.exclusions, kernels)

    @property
    def prerequisites(self):
        """The set of prerequisite kernels for this kernel.

        A prerequisite is always furnished, at lower precedence, when this kernel is
        furnished. Prerequisites always share this kernel's ktype.

        Returns:
            set[str, Kernel]: The prerequisites of this kernel.
        """

        if not hasattr(self, '_prerequisites'):
            self._prerequisites = set()

        return self._prerequisites

    @property
    def postrequisites(self):
        """The set of post-requisite kernels for this kernel.

        A post-requisite is always furnished, at higher precedence, when this kernel is
        furnished. Post-requisites always share this kernel's ktype.

        Returns:
            set[str, Kernel]: The post-requisites of this kernel.
        """

        if not hasattr(self, '_postrequisites'):
            self._postrequisites = set()

        return self._postrequisites

    @property
    def corequisites(self):
        """The set of co-requisite kernels for this kernel.

        A co-requisite is always furnished when this kernel is furnished. Because its
        ktype differs from this kernel's, its precedence does not matter.

        Returns:
            set[str, Kernel]: The co-requisites of this kernel.
        """

        if not hasattr(self, '_corequisites'):
            self._corequisites = set()

        return self._corequisites

    def require(self, *kernels, above=False):
        """Define one or more kernels as pre-, post-, or co-requisites for this kernel.

        A kernel of a different ktype becomes a co-requisite. One of the same ktype
        becomes a prerequisite or a post-requisite according to `above`.

        Parameters:
            *kernels (Kernel, str): The Kernel objects or basenames to require. A string
                is interpreted as a basename or a regular expression matching basenames.
            above (bool, optional): True to make same-ktype kernels post-requisites,
                furnished at higher precedence; False to make them prerequisites.

        Raises:
            ValueError: If one of the kernels is a metakernel.
        """

        if above:
            self._add_to_set(self.postrequisites, self.corequisites, kernels)
        else:
            self._add_to_set(self.prerequisites, self.corequisites, kernels)

    def _add_to_set(self, same_ktype_set, diff_ktype_set, kernels):
        """Add each kernel to either the set of same-type or different-type kernels.

        A Kernel object whose basenames overlap this kernel's own is broken up and its
        basenames are added individually.

        Parameters:
            same_ktype_set (set): The set to receive kernels sharing this kernel's ktype.
            diff_ktype_set (set): The set to receive kernels of a different ktype.
            kernels (tuple): The Kernel objects, basenames, or regular expressions to
                add.

        Raises:
            ValueError: If one of the kernels is a metakernel.
        """

        meta_msg = 'a metakernel cannot be part of an exclusion set or requirement set'

        for kernel in kernels:

            # Handle a basename or regular expression
            if isinstance(kernel, str):

                # kernel is a basename
                if is_basename(kernel):
                    basenames = {kernel}
                    kernel_ktype = basename_ktype(kernel)
                    # An exclusion or requirement names a file that must not, or must, be
                    # furnished; it needs only the ktype, which the extension supplies.
                    # The file itself need not exist locally, and often will not.

                # kernel is a regular expression
                else:
                    basenames = set(_KernelInfo.match(kernel))
                    kernel_ktype = basename_ktype(kernel)
                    # blank if the ktype cannot be inferred from the pattern

                basenames -= set(self.basenames)
                for basename in basenames:
                    ktype = kernel_ktype or Kernel.KernelFile(basename).ktype
                    if ktype == 'META':
                        raise ValueError(meta_msg)
                    if ktype == self.ktype:
                        same_ktype_set.add(basename)
                    else:
                        diff_ktype_set.add(basename)

            elif kernel.ktype == 'META':
                raise ValueError(meta_msg)

            # If it's a Kernel object, check for overlap among the basenames
            elif set(kernel.basenames) & set(self.basenames):
                # If there is overlap, handle the basenames individually
                self._add_to_set(same_ktype_set, diff_ktype_set, kernel.basenames)

            # Otherwise, save the Kernel rather than the individual basenames
            else:
                if kernel.ktype == self.ktype:
                    same_ktype_set.add(kernel)
                else:
                    diff_ktype_set.add(kernel)

    ######################################################################################
    # Shadows
    ######################################################################################

    def add_shadow(self, front, *behind, flags=re.IGNORECASE):
        """Ensure that a matching file outranks files matching the later patterns.

        When this kernel is furnished, a file matching the first pattern is given a higher
        precedence than any file matching the subsequent patterns.

        Parameters:
            front (str, re.Pattern, list, set, tuple): The basename or regular expression
                to be furnished at higher precedence, or a collection of these. Capturing
                groups here can be referenced from the "behind" patterns.
            *behind (str, re.Pattern): The basenames or regular expressions to be
                furnished at lower precedence.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
        """

        if not hasattr(self, '_shadows'):
            self._shadows = []

        # These are lists of patterns
        front  = Kernel.KernelFile._compile(front,  flags=flags)
        behind = Kernel.KernelFile._compile(behind, flags=flags)

        for pattern in front:
            self._shadows.append([pattern] + behind)

    def add_shadows(self, tuples, flags=re.IGNORECASE):
        """Add a list of shadow tuples to this kernel.

        Parameters:
            tuples (list, tuple): Each entry is a "front" pattern followed by one or more
                "behind" patterns.
            flags (RegexFlag, optional): Compile flags for the regular expressions;
                default is re.IGNORECASE.
        """

        for front_behind in tuples:
            self.add_shadow(*front_behind, flags=flags)

    def get_shadows(self, basename):
        """The list of compiled regular expressions that this basename shadows.

        Both this kernel's own shadows and the globally defined shadows are consulted.

        Parameters:
            basename (str): A kernel file basename.

        Returns:
            list[re.Pattern]: Every pattern matching basenames that the given basename
                takes precedence over.
        """

        if hasattr(self, '_shadows'):
            sources = self._shadows + Kernel.KernelFile._SHADOWS
        else:
            sources = Kernel.KernelFile._SHADOWS

        return Kernel.KernelFile._get_vetos_or_shadows(basename, sources)

    ######################################################################################
    # Furnished kernel management
    ######################################################################################

    def furnish(self, tmin=None, tmax=None, ids=None, *, minloc=0, refloc=None,
                reason=''):
        """Furnish this Kernel object at highest precedence for the specified range of
        times and the specified set of NAIF IDs.

        Overlapping, excluded kernels are unloaded. Pre-, post-, and co-requisites are
        furnished as needed, prerequisites below this kernel and post-requisites above.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
            minloc (int, optional): An index such that every basename furnished will be
                at or above this position in the list of furnished kernels.
            refloc (int, optional): A reference index into the list of furnished kernels,
                which is tracked as entries below it are removed.
            reason (str, optional): Why this kernel is being furnished: "prerequisite",
                "post-requisite", "corequisite", or blank for a direct request. Used in
                verbose mode.

        Returns:
            int: The index of the highest-precedence basename furnished.
        """

        # Unload any excluded kernels; track minloc
        for kernel in self.exclusions:
            kernel = Kernel.as_kernel(kernel)
            minloc = kernel.unload(tmin=tmin, tmax=tmax, ids=ids, refloc=minloc,
                                   reason='exclusion')

        # Furnish any prerequisites; identify highest loc among the furnished basenames
        for kernel in self.prerequisites:
            kernel = Kernel.as_kernel(kernel)
            loc, minloc = kernel.furnish(tmin=tmin, tmax=tmax, ids=ids,
                                         minloc=0, refloc=minloc, reason='prerequisite')
            minloc = max(minloc, loc)

        # Furnish this kernel above any prerequisites
        maxloc = self._furnish_for(tmin=tmin, tmax=tmax, ids=ids, minloc=minloc,
                                   reason=reason)

        # Furnish any post-requisites above this kernel
        for kernel in self.postrequisites:
            kernel = Kernel.as_kernel(kernel)
            _, maxloc = kernel.furnish(tmin=tmin, tmax=tmax, ids=ids,  minloc=maxloc,
                                       refloc=maxloc, reason='post-requisite')

        # Furnish any co-requisites
        for kernel in self.corequisites:
            kernel = Kernel.as_kernel(kernel)
            kernel.furnish(tmin=tmin, tmax=tmax, ids=ids, reason='corequisite')

        # Mirror _furnish_for(): a caller that supplied a refloc gets it back, updated.
        if refloc is None:
            return maxloc

        return (maxloc, refloc)

    def _furnish_for(self, tmin=None, tmax=None, ids=None, minloc=0, refloc=None,
                     reason=''):
        """Internal method to furnish this kernel, ensuring that every furnished basename
        is at or above a specified location in the list.

        Any furnished file vetoed by one of this kernel's basenames is unloaded first.
        A file already furnished below its required precedence is unloaded and furnished
        again at the top.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
            minloc (int, optional): An index such that every basename furnished will be
                at or above this position in the list of furnished kernels.
            refloc (int, optional): A reference index into the list of furnished kernels,
                which is tracked as entries below it are removed. None to omit it from
                the result.
            reason (str, optional): Why this kernel is being furnished, used in verbose
                mode.

        Returns:
            int, (int, int): The index of the highest-precedence basename furnished; or
                that index paired with the updated refloc, if a refloc was given.
        """

        furnished = _FURNISHED_BASENAMES[self.ktype]

        maxloc = minloc
        for basename in self.basenames:
            kfile = Kernel.KernelFile(basename)

            # Ignore files that do not overlap
            if not kfile.has_overlap(tmin=tmin, tmax=tmax, ids=ids):
                continue

            # Require an overlapping file to exist
            kfile.must_exist()

            # Identify locations of vetoed files
            patterns = Kernel.KernelFile._get_vetos(basename)
            locs = []
            for pattern in patterns:
                locs += [loc for loc, name in enumerate(furnished)
                         if pattern.fullmatch(name)]

            # Unload vetoed files; update minloc and maxloc
            locs = list(set(locs))      # select unique locs
            locs.sort(reverse=True)     # reverse order!
            for loc in locs:
                unload = Kernel.KernelFile(furnished[loc])
                if not unload.has_overlap(tmin=tmin, tmax=tmax, ids=ids):
                    continue

                furnished.pop(loc)
                if not Kernel._DEBUG:
                    CSPYCE.unload(unload.abspath)
                if Kernel._VERBOSE:
                    print('Spyceman:', unload.basename, 'unloaded (veto)')

                if loc <= minloc:
                    minloc -= 1
                if loc <= maxloc:
                    maxloc -= 1
                if refloc is not None and loc <= refloc:
                    refloc -= 1

            # See if the kernel file is already furnished
            try:
                loc = furnished.index(basename)

            # If not, furnish it
            except ValueError:
                furnished.append(basename)
                loc = len(furnished) - 1

                if not Kernel._DEBUG:
                    CSPYCE.furnsh(kfile.abspath)
                if Kernel._VERBOSE:
                    reason = reason or 'request'
                    print('Spyceman:', kfile.basename, f'furnished ({reason})')

            # Otherwise...
            else:
                # Locate any shadowed files
                patterns = self.get_shadows(basename)
                locs = [minloc]
                for pattern in patterns:
                    locs += [k for k,f in enumerate(furnished) if pattern.fullmatch(f)]

                # If this file's precedence is too low, unload and furnish again
                if loc < max(locs):
                    if not Kernel._DEBUG:
                        CSPYCE.unload(kfile.abspath)
                        CSPYCE.furnsh(kfile.abspath)
                    if Kernel._VERBOSE:
                        reason = reason or 'request'
                        print('Spyceman:', kfile.basename, f'reloaded ({reason})')

                    furnished.pop(loc)
                    furnished.append(basename)
                    loc = len(furnished) - 1

            # During an ordered load, make sure each basename is always furnished above
            # the previous.
            if self.is_ordered:
                minloc = loc

            # Track the maximum index among the kernel files being furnished
            maxloc = max(maxloc, loc)

        if refloc is None:
            return maxloc

        return (maxloc, refloc)

    def unload(self, tmin=None, tmax=None, ids=None, refloc=0, reason=''):
        """Unload any basename of this kernel that overlaps the time range or NAIF IDs.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
            refloc (int, optional): A reference index into the list of furnished kernels,
                which is tracked as entries below it are removed.
            reason (str, optional): Why this kernel is being unloaded, used in verbose
                mode.

        Returns:
            int: The new index of the given refloc, decremented once for each basename
                below it that was unloaded.
        """

        furnished = _FURNISHED_BASENAMES[self.ktype]

        for basename in self.basenames:
            kfile = Kernel.KernelFile(basename)
            if not kfile.exists:
                continue

            if kfile.has_overlap(tmin=tmin, tmax=tmax, ids=ids):
                try:
                    loc = furnished.index(basename)
                except ValueError:      # list.index raises ValueError, not KeyError
                    continue

                if not Kernel._DEBUG:
                    CSPYCE.unload(kfile.abspath)
                if Kernel._VERBOSE:
                    reason = reason or 'request'
                    print('Spyceman:', kfile.basename, f'unloaded ({reason})')

                furnished.pop(loc)
                if loc <= refloc:
                    refloc -= 1

        return refloc

    def used(self, tmin=None, tmax=None, ids=None):
        """The ordered list of kernel basenames that are or would be used for a given
        range of times and/or a set of NAIF IDs.

        Co-requisites come first, then prerequisites, then this kernel's own basenames,
        then post-requisites.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.

        Returns:
            list[str]: The basenames that would be furnished, in increasing order of
                precedence, including pre-, post-, and co-requisites.
        """

        basenames = []
        for kernel in self.corequisites:
            kernel = Kernel.as_kernel(kernel)
            basenames += kernel._used_for(tmin=tmin, tmax=tmax, ids=ids)

        for kernel in self.prerequisites:
            kernel = Kernel.as_kernel(kernel)
            basenames += kernel._used_for(tmin=tmin, tmax=tmax, ids=ids)

        basenames += self._used_for(tmin=tmin, tmax=tmax, ids=ids)

        for kernel in self.postrequisites:
            kernel = Kernel.as_kernel(kernel)
            basenames += kernel._used_for(tmin=tmin, tmax=tmax, ids=ids)

        return basenames

    def _used_for(self, tmin=None, tmax=None, ids=None):
        """Internal method to return the list of basenames to be used in this range of
        times and/or this set of NAIF IDs.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.

        Returns:
            list[str]: This kernel's own basenames that overlap the given constraints, in
                increasing order of precedence.
        """

        return [b for b in self.basenames
                if Kernel.KernelFile(b).has_overlap(tmin=tmin, tmax=tmax, ids=ids)]

    ######################################################################################
    # Overlap tester
    ######################################################################################

    def has_overlap(self, tmin=None, tmax=None, ids=None, *, dt=None):
        """True if this kernel overlaps a specified time range and/or set of NAIF IDs.

        Parameters:
            tmin (float, str, Kernel, optional): Earliest time in seconds TDB or as a
                date-time string; None to ignore time. As an alternative, a Kernel
                object, in which case tmin, tmax, and ids are all inferred from it, which
                makes "kernel1.has_overlap(kernel2)" possible.
            tmax (float, str, optional): Latest time in seconds TDB or as a date-time
                string; None to use the value of tmin.
            ids (int, set[int], optional): One or more NAIF IDs; None to ignore NAIF IDs.
            dt (float, bool, optional): The number of seconds by which two time intervals
                may be separated and still count as overlapping, which lets nearby ranges
                be treated as overlapping even when they do not quite intersect. Default
                is to use Kernel.DT.

        Returns:
            bool: True if this kernel overlaps the given time range and NAIF IDs.
        """

        if is_basename(tmin):
            tmin = Kernel.as_kernel(tmin)

        if isinstance(tmin, Kernel):
            kernel = tmin
            tmin = kernel.time[0]
            tmax = kernel.time[1]
            ids = kernel.naif_ids

        if not self.time_overlap(tmin=tmin, tmax=tmax, dt=dt):
            return False

        # An empty set of NAIF IDs means "applicable to every NAIF ID", on either side.
        # id_overlap() returns an empty set both when the two sets name IDs and share
        # none, and when neither side constrains the IDs at all; only the first of those
        # is a failure to overlap. Without this test, a kernel that applies to all IDs --
        # every LSK, for one -- never overlaps an unconstrained query, and so is never
        # furnished.
        if not ids and not self.naif_ids:
            return True

        return bool(self.id_overlap(ids=ids))

    def time_overlap(self, tmin=None, tmax=None, dt=True):
        """The range of this kernel's time that overlaps a specified time range.

        Parameters:
            tmin (float, str, Kernel, tuple, list, optional): Earliest time in seconds
                TDB or as a date-time string, or None for all times. As an alternative, a
                Kernel object or a (tmin, tmax) pair, which makes
                "kernel1.time_overlap(kernel2)" possible.
            tmax (float, str, optional): Latest time in seconds TDB or as a date-time
                string, or None to use tmin.
            dt (float, bool, optional): The number of seconds by which two time intervals
                may be separated and still count as overlapping. Use True for Kernel.DT
                and False for zero.

        Returns:
            (float, float), None: The overlapping time range in seconds TDB; None if the
                two ranges do not overlap.
        """

        # Interpret the inputs
        if isinstance(tmin, Kernel):
            kernel = tmin
            tmin = kernel.time[0]
            tmax = kernel.time[1]
        elif isinstance(tmin, (tuple,list)):
            time = tmin
            tmin = time[0]
            tmax = time[1]

        if isinstance(tmin, str):
            tmin = validate_iso_time(tmin)

        if isinstance(tmax, str):
            tmax = validate_iso_time(tmax)

        # Compare
        t0 = self.time[0]
        t0 = tmin if t0 is None else t0 if tmin is None else max(t0, tmin)

        t1 = self.time[1]
        t1 = tmax if t1 is None else t1 if tmax is None else min(t1, tmax)

        # Check for overlap or near-overlap. has_overlap() defaults dt to None and
        # documents that as "use Kernel.DT", so None is accepted here alongside True.
        if dt is None:
            dt = Kernel.DT
        elif isinstance(dt, (bool, np.bool_)):
            dt = Kernel.DT if dt else 0.

        # Either limit can still be None, meaning that neither this kernel nor the query
        # constrains that end of the range. An unconstrained end cannot rule out an
        # overlap, so the limits are only compared when both are known.
        if t0 is not None and t1 is not None and t1 < t0 - dt:
            return None

        return (t0, t1)

    def id_overlap(self, ids=None):
        """The subset of NAIF IDs in this kernel that overlaps a given set of NAIF IDs.

        An empty set means that a kernel applies to all NAIF IDs, so the overlap of an
        empty set with {399} is {399}. Where both sets are non-empty, this returns their
        intersection.

        Parameters:
            ids (int, set[int], Kernel, optional): A NAIF ID or set of NAIF IDs to check
                against this kernel; None to return this kernel's own IDs. As an
                alternative, a Kernel object, which makes "kernel1.id_overlap(kernel2)"
                possible.

        Returns:
            set[int]: The NAIF IDs common to this kernel and the given set.
        """

        if isinstance(ids, Kernel):
            kernel = ids
            ids = kernel.naif_ids
        elif isinstance(ids, numbers.Integral):
            ids = {ids}

        if not ids:
            return self.naif_ids

        if not self.naif_ids:
            return set(ids)

        return set(ids) & self.naif_ids

    ######################################################################################
    # Support methods
    ######################################################################################

    @staticmethod
    def _naif_ids_for_kernels(kernels, wo_aliases=False):
        """The union of all NAIF IDs covered by the given kernels.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.
            wo_aliases (bool, optional): True to use each kernel's primary NAIF IDs; False
                to include aliases.

        Returns:
            set[int]: The union of the NAIF IDs covered by these kernels.
        """

        naif_ids = set()
        for kernel in kernels:
            if wo_aliases:
                naif_ids |= Kernel.as_kernel(kernel).naif_ids_wo_aliases
            else:
                naif_ids |= Kernel.as_kernel(kernel).naif_ids

        return naif_ids

    @staticmethod
    def _time_for_kernels(kernels, ids=None):
        """The extreme time limits covered by these kernels.

        Kernels with no time dependence are ignored.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.
            ids (int, set[int], optional): Restrict the result to kernels covering this
                NAIF ID or set of NAIF IDs; None for the overall limits.

        Returns:
            (float, float), (None, None), None: The earliest and latest times covered, in
            seconds TDB; (None, None) if none of the kernels has a time dependence; None
            if the list is empty or no kernel covers the given NAIF IDs.
        """

        if not kernels:
            return None

        if isinstance(ids, numbers.Integral):
            ids = {ids}

        # Initialize to an impossible range of times
        tmin =  1.e99
        tmax = -1.e99

        for kernel in kernels:
            kernel = Kernel.as_kernel(kernel)
            if ids and not (kernel.naif_ids & ids):
                continue

            (t0, t1) = kernel.time
            if t0 is not None:
                tmin = min(tmin, t0)
                tmax = max(tmax, t1)

        if tmin > tmax:
            if ids:             # no kernels covered the given IDs
                return None

            return (None, None)

        return (tmin, tmax)

    @staticmethod
    def _release_date_for_kernels(kernels):
        """The latest release date among these kernels.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.

        Returns:
            str: The latest release date, as "yyyy-mm-dd".
        """

        return max(Kernel.as_kernel(k).release_date for k in kernels)

    @staticmethod
    def _family_for_kernels(kernels):
        """A reasonable family name for a set of kernels.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to
                combine.

        Returns:
            str: A name summarizing the family names of these kernels.
        """

        families = {Kernel.as_kernel(k).family for k in kernels}
        return Kernel._common_name(families)

    @staticmethod
    def _name_for_kernels(kernels):
        """A reasonable name for a set of kernels.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.

        Returns:
            str: A name summarizing the names of these kernels.
        """

        names = {Kernel.as_kernel(k).name for k in kernels}
        return Kernel._common_name(names)

    @staticmethod
    def _version_for_kernels(kernels):
        """The overall version ID or set of version IDs among these kernels.

        This is the maximum among the versions of the kernels provided. Where the versions
        are a mixture of strings and integers or tuples, the set of both maxima is
        returned.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.

        Returns:
            int, str, tuple[int, ...], set: The overall version; an empty string if none
                of the kernels has a version.
        """

        versions = set()
        for k in kernels:
            versions |= Kernel.as_kernel(k).version_as_set

        if not versions:
            return ''

        versions = {(v,) if isinstance(v, numbers.Integral) else v for v in versions}
        tuples = {v for v in versions if isinstance(v, tuple)}
        strings = {v for v in versions if isinstance(v, str)}

        versions = []
        if tuples:
            max_tuples = max(tuples)
            if len(max_tuples) == 1:        # convert tuple to int
                max_tuples = max_tuples[0]
            versions.append(max_tuples)

        if strings:
            versions.append(max(strings))

        if len(versions) == 1:
            return versions[0]

        return set(versions)

    @staticmethod
    def _properties_for_kernels(kernels):
        """Merged properties among these kernels.

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects or basenames to combine.

        Returns:
            dict: Each property name mapped to its value where the kernels agree, or to
                the set of values where they do not.
        """

        merged = {}
        for kernel in kernels:
            properties = Kernel.as_kernel(kernel).properties
            for name, value in properties.items():
                if name not in merged:
                    merged[name] = set()
                if not value and value != 0:
                    continue
                if isinstance(value, set):
                    merged[name] |= value
                else:
                    merged[name].add(value)

        for name, valset in list(merged.items()):
            if not valset:
                del merged[name]
            elif len(valset) == 1:
                merged[name] = valset.pop()

        return merged

    @staticmethod
    def _common_name(names, maxlen=0):
        """A reasonable summary name for a list of names.

        Characters shared by every name are kept; a position where the names differ only
        in a digit becomes "N"; and the remaining differences are collapsed into a
        bracketed alternation, split on underscores where that is shorter.

        Parameters:
            names (list[str], set[str]): The names to summarize.
            maxlen (int, optional): The approximate maximum length of the name returned;
                zero for no limit.

        Returns:
            str: A single name summarizing all of the given names.
        """

        names = set(names)
        if len(names) == 1:
            return names.pop()

        # Find common characters from beginning
        head = []
        while True:
            chars = {n[0] if n else '' for n in names}
            if len(chars) == 1:
                char = chars.pop()
                if not char:
                    break
                head.append(char)
            elif chars.issubset(set('0123456789')):     # try replacing digits with "N"
                head.append('N')
            else:
                break

            names = {n[1:] if n else '' for n in names}

        head = ''.join(head)

        # Find common characters from end
        tail = []
        while True:
            chars = {n[-1] if n else '' for n in names}
            if len(chars) == 1:
                char = chars.pop()
                if not char:
                    break
                tail.append(char)
            elif chars.issubset(set('0123456789')):     # try replacing digits with "N"
                tail.append('N')
            else:
                break

            names = {n[:-1] if n else '' for n in names}

        tail = ''.join(tail[::-1])

        # Find the shortest way to express the "innards" upon splitting by underscores
        names = list(names)
        names.sort()
        innard_options = ['[' + '|'.join(names) + ']']

        before = ''
        while True:
            words = {n.partition('_')[0] for n in names}
            if len(words) == 1:
                innard = words.pop() + '_'
            else:
                words = list(words)
                words.sort()
                if all(len(w) < 2 for w in words):
                    innard = '[' + ''.join(words) + ']_'
                else:
                    innard = '[' + '|'.join(words) + ']_'

            names = {n.partition('_')[-1] for n in names}
            if names == {''}:
                break

            names = list(names)
            names.sort()
            before += innard
            innard_options.append(before + '[' + '|'.join(names) + ']')

        minlen = min(len(i) for i in innard_options)
        innard = [i for i in innard_options if len(i) == minlen][0]

        # Merge results
        return head + innard + tail

##########################################################################################
