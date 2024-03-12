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
from spyceman._utils      import is_basename, basename_ktype

# Dictionary ktype -> ordered list of basenames currently furnished in cspyce
_FURNISHED_BASENAMES = {key:{} for key in _KTYPES}


class Kernel(object):
    """Kernel is an abstract class that defines one or more SPICE kernel files and the
    rules for how to to furnish them.

    Every kernel instance has these properties:
        name            A name string for this kernel.
        ktype           The type of this kernel: "CK", "SPK", "LSK", etc.
        naif_ids        The set of NAIF IDs covered by this kernel, including aliases;
                        {} if the kernel applies to all NAIF IDs.
        naif_ids_wo_aliases
                        The set of NAIF IDs covered by this kernel, excluding aliases;
                        {} if the kernel applies to all NAIF IDs.
        time            Time limits as a tuple of two times in seconds TDB, or (None,
                        None) if this kernel applies to all times.
        release_date    Release date as an ISO date string "yyyy-mm-dd", or an empty
                        string if no release date is known.
        version         Version of this kernel file as a string, integer, or tuple of
                        integers; an empty string if the version is undefined.
        family          The family name for this kernel; in general, version IDs refer to
                        different kernels within the same family.
        properties      A dictionary of additional name/value pairs that are relevant to
                        this Kernel. For example, perhaps properties['mission']='Cassini'.

        basenames       The list of kernel basenames managed by this kernel.
        is_ordered      True if this is an ordered list, meaning that later kernels take
                        precedence over earlier ones.
        exclusions      The set of excluded Kernel objects or basenames. When this kernel
                        is furnished, it is guaranteed that any exclusions will be
                        unloaded.
        prerequisites   A set of Kernel objects or basenames that will always be furnished
                        at a lower precedence when this kernel is furnished.
        postrequisites  A set of Kernel objects or basenames that will always be furnished
                        at a higher precedence when this kernel is furnished.
        corequisites    A set of Kernel objects of a different ktype that will always be
                        furnished when this kernel is furnished. Because their ktype
                        differs from that of this ktype, their precedence level does not
                        matter.

    Every kernel instance supports these methods:
        exclude()       Add these kernels to the set of exclusions.
        require()       Add these kernels to the set of pre-, post-, or co-requisites.
        furnish()       Furnish this kernel within a specified range of times and/or for a
                        specified set of NAIF IDs.
        unload()        Unload this kernel within a specified range of times and/or for a
                        specified set of NAIF IDs.
        used()          An ordered list of kernel basenames that are furnished for a
                        specified range of times and/or for a specified set of NAIF IDs.
    """

    # These class definitions are initialized when the associated subclass is imported;
    # this is needed in order to avoid circular imports
    KernelFile = None
    Metakernel = None

    DT = 1.5 * 86400.           # seconds of buffer around the time limits of any kernel

    def __str__(self):
        return type(self).__name__ + '("' + self.name + '")'

    def __repr__(self):
        return self.__str__()

    def __copy__(self):
        new = type(self).__new__()
        new.__dict__ = self.__dict__.copy()
        return new

    def __eq__(self, arg):

        if self is arg:         # this is the quickest test
            return True

        if not isinstance(arg, Kernel):
            return False

        return (type(self) is type(arg) and self.__dict__ == arg.__dict__)

    @staticmethod
    def as_kernel(kernel):
        """Return this input as a subclass of Kernel. Strings are interpreted as basenames
        and returned as KernelFiles.
        """

        if isinstance(kernel, Kernel):
            return kernel
        if not isinstance(kernel, str):
            raise TypeError('not a Kernel object: ' + repr(kernel))

        return Kernel.KernelFile(kernel, download=True)

    ######################################################################################
    # Global operating modes
    ######################################################################################

    _DOWNLOADS = True
    _DEBUG = False
    _VERBOSE = False

    @staticmethod
    def download(status=None):
        """Set and/or return the download status."""

        if status is None:
            status = Kernel._DOWNLOADS

        status = bool(status)
        Kernel._DOWNLOADS = status
        return status

    @staticmethod
    def debug(status=None):
        """Set and/or return the debug status."""

        if status is None:
            status = Kernel._DEBUG

        status = bool(status)
        Kernel._DEBUG = status
        return status

    @staticmethod
    def verbose(status=None):
        """Set and/or return the verbose status."""

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

        The list excudes pre-, post-, and co-requisites.
        """
        return self._basenames

    @property
    def is_ordered(self):
        """True if this Kernel's basename list is ordered by precedence."""
        return self._is_ordered

    @property
    def name(self):
        """The name for this kernel."""

        if not hasattr(self, '_name') or not self._name:
            kernels = [Kernel.KernelFile(b) for b in self._basenames]
            families = [k.family or k.basename for k in kernels]
            self._name = Kernel._common_name(families) or 'UNNAMED'

        return self._name

    @name.setter
    def name(self, value):
        self._name = str(value)

    @property
    def ktype(self):
        """Kernel type of this file: "SPK", "CK", "LSK", etc."""

        if not hasattr(self, '_ktype') or self._ktype is None:
            self._ktype = Kernel.as_kernel(self.basenames[0]).ktype

        return self._ktype

    @property
    def naif_ids(self):
        """The set of NAIF IDs covered by this file, including aliases; an empty set if
        the kernel applies to all NAIF IDs.
        """

        if not hasattr(self, '_naif_ids') or self._naif_ids is None:
            self._naif_ids = Kernel._naif_ids_for_kernels(self.basenames,
                                                          wo_aliases=False)

        return self._naif_ids

    @property
    def naif_ids_wo_aliases(self):
        """The set of NAIF IDs covered by this file, without aliases; an empty set if the
        kernel applies to all NAIF IDs.
        """

        if not hasattr(self, '_naif_ids_wo_aliases') or self._naif_ids_wo_aliases is None:
            self._naif_ids_wo_aliases = Kernel._naif_ids_for_kernels(self.basenames,
                                                                     wo_aliases=True)

        return self._naif_ids_wo_aliases

    @property
    def time(self):
        """Time limits as a tuple of two times in seconds TDB."""

        if not hasattr(self, '_time') or self._time is None:
            self._time = Kernel._time_for_kernels(self.basenames)

        return self._time

    @property
    def release_date(self):
        """Release date as an ISO date string "yyyy-mm-dd", or "" if no release date is
        known.
        """

        if not hasattr(self, '_release_date') or self._release_date is None:
            self._release_date = Kernel._release_date_for_kernels(self.basenames)

        return self._release_date

    @property
    def version(self):
        """Version of this kernel file as a string, integer, or tuple of integers."""

        if not hasattr(self, '_version') or self._version is None:
            self._version = Kernel._version_for_kernels(self.basenames)

        return self._version

    @version.setter
    def version(self, value):
        self._version = _KernelInfo._validate_version(value)

    @property
    def family(self):
        """The family name of this kernel object. Typically, kernels with a different
        version or time range often are members of the same family.
        """

        if not hasattr(self, '_family') or self._family is None:
            self._family = self._family = self._name

        return self._family

    @family.setter
    def family(self, value):
        self._family = str(value)

    @property
    def properties(self):
        """The dictionary of special properties for this Kernel."""

        if not hasattr(self, '_properties') or self._properties is None:
            self._properties = Kernel._properties_for_kernels(self.basenames)

        return self._properties

    ######################################################################################
    # Exclusions and pre-, post-, co-requisites
    ######################################################################################

    @property
    def exclusions(self):
        """The set of excluded kernel file basenames for this kernel."""

        if not hasattr(self, '_exclusions'):
            self._exclusions = set()

        return self._exclusions

    def exclude(self, *kernels):
        """Exclude one or more kernels from being furnished at the same time as this
        kernel.

        Each input value can be a Kernel object, a kernel file basename, or a regular
        expression that matches kernel file basenames.
        """

        self._add_to_set(self.exclusions, self.exclusions, kernels)

    @property
    def prerequisites(self):
        """The set of prerequisite kernels for this kernel.

        A prerequisite kernels will always be furnished, but at lower precedence, when
        this kernel is furnished. Prerequisites are always of the same ktype as the given
        kernel.
        """

        if not hasattr(self, '_prerequisites'):
            self._prerequisites = set()

        return self._prerequisites

    @property
    def postrequisites(self):
        """The set of post-requisite kernels for this kernel.

        A post-requisite kernels will always be furnished, and at higher precedence, when
        this kernel is furnished. Post-requisites are always of the same ktype as the
        given kernel.
        """

        if not hasattr(self, '_postrequisites'):
            self._postrequisites = set()

        return self._postrequisites

    @property
    def corequisites(self):
        """The set of co-requisite kernels for this kernel.

        A co-requisite kernels will always be furnished when this kernel is furnished.
        Co-requisites are always of a different ktype than the given kernel.
        """

        if not hasattr(self, '_corequisites'):
            self._corequisites = set()

        return self._corequisites

    def require(self, *kernels, above=False):
        """Define one or more kernels as being pre-, post-, or co-requisites for this
        kernel.

        If an input kernel is specified as a string, it is converted to a KernelFile.

        Kernels of a different ktype from this kernel are defined as co-requisites. Those
        of the same ktype are pre-requisites if above is False, post-requisites if above
        is True.
        """

        if above:
            self._add_to_set(self.postrequisites, self.corequisites, kernels)
        else:
            self._add_to_set(self.prerequisites, self.corequisites, kernels)

    def _add_to_set(self, same_ktype_set, diff_ktype_set, kernels):
        """Add each kernel to either the set of same-type or different-type kernels.

        A kernel can be represented by a Kernel object, a basename, or a regular
        expression that matches zero or more basenames.

        exclusions is True if we are adding to this Kernel's exclusion set; otherwise,
        we are adding to one or more of its requisite sets.
        """

        meta_msg = 'a metakernel cannot be part of an exclusion set or requirement set'

        for kernel in kernels:

            # Handle a basename or regular expression
            if isinstance(kernel, str):

                # kernel is a basename
                if is_basename(kernel):
                    basenames = {kernel}
                    kfile = Kernel.KernelFile(kernel, exists=True)
                    kernel_ktype = kfile.ktype

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
            elif kernel.basenames & self.basenames:
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
        """When furnishing this kernel, ensure that a file matching the first basename
        pattern will be furnished at a higher level of precedence than any basenames
        matching subsequent patterns.

        Multiple "front" patterns can be specified inside a tuple, list, or set. If this
        input contains capturing sequences, these can be referenced in the "below"
        patterns.
        """

        if not hasattr(self, '_shadows'):
            self._shadows = []

        front  = Kernel.KernelFile._compile(front,  flags=flags)
        behind = Kernel.KernelFile._compile(behind, flags=flags)
            # Each is a list of patterns

        for pattern in front:
            self._shadows.append([pattern] + behind)

    def add_shadows(self, tuples, flags=re.IGNORECASE):
        """Add a list of shadow tuples/lists to this kernel. Each tuple contains a "front"
        pattern followed by one or "behind" patterns.""""

        for front_behind in tuples:
            self.add_shadow(*front_behind, flags=flags)

    def get_shadows(self, basename):
        """The list of compiled regular expressions that this basename shadows."""

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

        This method returns the index of the highest-precedence kernel.

        Overlapping, excluded kernels are unloaded. Pre-, post-, and co-requisites are
        furnished as needed.

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            ids         NAIF ID or set of NAIF IDs.
            minloc      optional specification of an index such that every basename to be
                        furnished will be at or above this index in the list of furnished
                        kernels.
            refloc      optional specification of a particular location in the list of
                        furnished files. If not None, the function will return the updated
                        location as a second element of a tuple. The refloc might change
                        if files lower in precedence than this value are unloaded during
                        the operation.
            reason      reason for the furnish: "prerequisite", "post-requisite",
                        "corequisite", or blank for default.

        Return:         loc or (loc, refloc)
            loc         the index of the basename of the highest furnished basename.
            refloc      the new index of the given refloc in the list of furnished
                        basenames.
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
        maxloc = kernel._furnish_for(tmin=tmin, tmax=tmax, ids=ids, minloc=minloc,
                                     reason=reason)

        # Furnish any post-requisites above this kernel
        for kernel in self.postrequisites:
            kernel = Kernel.as_kernel(kernel)
            _, maxloc = kernel.furnish(tmin=tmin, tmax=tmax, ids=ids,
                                       minloc=maxloc, refloc=maxloc,
                                       reason='post-requisite')

        # Furnish any co-requisites
        for kernel in self.corequisites:
            kernel = Kernel.as_kernel(kernel)
            kernel.furnish(tmin=tmin, tmax=tmax, ids=ids,
                           reason='corequisite')

        return maxloc

    def _furnish_for(self, tmin=None, tmax=None, ids=None, minloc=0, refloc=None,
                     reason=''):
        """Internal method to furnish this kernel, ensuring that every furnished basename
        is at or above a specified location in the list.
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
                if refloc and loc <= refloc:
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
                        print('Spyceman:', kfile.basename, 'reloaded ({reason})')

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
        """Unload any basename of this kernel that overlaps the time range or kernel list.

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            ids         NAIF ID or set of NAIF IDs.
            refloc      optional reference index into the list of furnished kernels.
            reason      reason for unload; blank for default. Used in verbose mode.

        Return          new location of the given refloc value. The value will change for
                        each basename below this location that is unloaded.
        """

        furnished = _FURNISHED_BASENAMES[self.ktype]

        for basename in self.basenames:
            kfile = Kernel.KernelFile(basename)
            if not kfile.exists:
                continue

            if kfile.has_overlap(tmin=tmin, tmax=tmax, ids=ids):
                try:
                    loc = furnished.index(basename)
                except KeyError:
                    continue

                if not Kernel._DEBUG:
                    CSPYCE.unload(kfile.abspath)
                if Kernel.VERBOSE:
                    reason = reason or 'request'
                    print('Spyceman:', kfile.basename, f'unloaded ({reason})')

                furnished.pop(loc)
                if loc <= refloc:
                    refloc -= 1

        return refloc

    def used(self, tmin=None, tmax=None, ids=None):
        """The ordered list of kernel basenames that are or would be used for a given
        range of times and/or a set of NAIF IDs, including pre-, post-, and co-requisites.

        Inputs:
            tmin        earliest time in TDB seconds. Default is to ignore time.
            tmax        latest time in TDB seconds. Default is to use the value of tmin.
            ids         set of NAIF IDs that are required. Default is to ignore NAIF IDs.
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
        """

        return [b for b in self.basenames
                if Kernel.KernelFile(b).has_overlap(tmin=tmin, tmax=tmax, ids=ids)]

    ######################################################################################
    # Overlap tester
    ######################################################################################

    def has_overlap(self, tmin=None, tmax=None, ids=None, *, dt=None):
        """True if this kernel has content that overlaps a kernel or a specified time
        range and/or set of NAIF IDs.

        Inputs:
            tmin        earliest time in TDB seconds. Default is to ignore time. As an
                        alternative, the first input can be a Kernel object, in which case
                        tmin, tmax, and ids are inferred from it. This option makes it
                        possible to compare kernels via "kernel1.has_overlap(kernel2)".
            tmax        latest time in TDB seconds. Default is to use the value of tmin.
            ids         one or more NAIF IDs. Default is to ignore NAIF IDs.
            dt          number of seconds that two time intervals can be separated by for
                        them to be regarded as non-overlapping. This allows time ranges
                        that are "close" to be treated as overlapping even if the limits
                        do not quite intersect. Default is to use the defined value of
                        Kernel.DT.
        """

        if is_basename(tmin):
            tmin = Kernel.as_kernel(tmin)

        if isinstance(tmin, Kernel):
            kernel = tmin
            tmin = kernel.time[0]
            tmax = kernel.time[1]
            ids = kernel.naif_ids

        if not self._time_overlap(tmin=tmin, tmax=tmax, dt=dt):
            return False

        return bool(self.id_overlap(ids=ids))

    def time_overlap(self, tmin=None, tmax=None, dt=True):
        """The range of this kernel's time that overlaps a specified time range. If there
        is no overlap, return None.

        If tmin is None or tmax is None, that time limit is unconstrained.

        Inputs:
            tmin        optional earliest time in TDB seconds, or None for all times. As
                        an alternative, the input can be a Kernel object, in which case
                        tmin and tmax are inferred from it. This option makes it possible
                        to compare kernels via "kernel1.time_overlap(kernel2)".
            tmax        latest time in TDB seconds, or None to use tmin.
            dt          number of seconds that two time intervals must be separated by for
                        them to be regarded as non-overlapping. This allows time ranges
                        that are "close" to be treated as overlapping even if the limits
                        do not quite intersect. Use True to set dt to Kernel.DT.
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
            tmin = julian.tdb_from_iso(tmin)

        if isinstance(tmax, str):
            tmax = julian.tdb_from_iso(tmax)

        # Compare
        t0 = self.time[0]
        t0 = tmin if t0 is None else t0 if tmin is None else max(t0, tmin)

        t1 = self.time[1]
        t1 = tmax if t1 is None else t1 if tmax is None else min(t1, tmax)

        # Check for overlap or near-overlap
        if isinstance(dt, (bool, np.bool_)):
            dt = Kernel.DT if dt else 0.

        if t1 < t0 - dt:
            return None

        return (t0, t1)

    def id_overlap(self, ids=None):
        """The subset of NAIF IDs in this kernel that overlaps a given set of NAIF IDs.

        Note that ids={} indicates that a kernel is applicable to all NAIF IDs, so the
        overlap of {} and a {399} is {399}. However, if both sets are non-empty, this
        returns the intersection of the two sets.

        Inputs:
            ids         NAIF ID or set of NAIF IDs to check against this kernel; if None,
                        the set of IDs of the kernel is returned. As an alternative, the
                        input can be a Kernel object, in which case the set of IDs is
                        inferred from it. This option makes it possible to compare kernels
                        via "kernel1.id_overlap(kernel2)".
        """

        if isinstance(ids, Kernel):
            kernel = ids
            ids = kernel.ids
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
        """The union of all NAIF IDs covered by these kernels."""

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

        If ids is None or an empty set, return the overall time limits; otherwise, return
        the time limits for the specified NAIF ID or set of NAIF IDs.

        Kernels with no time dependence are ignored. If none of the kernels have time
        dependence, (None, None) is returned.

        If the kernel list is empty or there are no kernels covering the given NAIF IDs,
        None is returned.
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
        """The lastest release date among these kernels."""

        return max(Kernel.as_kernel(k).release_date for k in kernels)

    @staticmethod
    def _family_for_kernels(kernels):
        """A reasonable family name for a set of kernels."""

        families = {Kernel.as_kernel(k).family for k in kernels}
        return Kernel._common_name(families)

    @staticmethod
    def _name_for_kernels(kernels):
        """A reasonable name for a set of kernels."""

        names = {Kernel.as_kernel(k).name for k in kernels}
        return Kernel._common_name(names)

    @staticmethod
    def _version_for_kernels(kernels):
        """The overall version ID or set of version IDs among these kernels.

        This is the maximum among the versions of the kernels provided. If the versions
        are a mixture of strings and integers/tuples, the set of both maxima is returned.
        """

        versions = set()
        for k in kernels:
            versions |= k.version_as_set

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
        """Merged properties among these kernels."""

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

        for name, valset in merged.items():
            if not valset:
                del merged[name]
            elif len(valset) == 1:
                merged[name] = valset.pop()

        return merged

    @staticmethod
    def _common_name(names, maxlen=0):
        """A reasonable summary name for a list of names.

        If maxlen is nonzero, it is the approximate maximum length of the name returned.
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
