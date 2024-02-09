##########################################################################################
# spyceman/kernelstack.py
##########################################################################################

from spyceman.kernel import Kernel

class KernelStack(Kernel):
    """An ordered list of Kernel objects that must be furnished in the given order of
    precedence. The rules for each kernel's exclusions and pre-, post-, and co-requisites
    are honored.
    """

    _is_ordered = True      # fixed value for every instance of this subclass

    def __init__(self, kernels, *, name=''):
        """Constructor.

        Inputs:
            kernels     list of kernel objects.
            name        optional name string for this KernelStack.
        """

        self._kernels = [Kernel.as_kernel(k) for k in kernels]
        self._ktype = self._kernels[0].ktype
        if self._ktype == 'META':
            raise ValueError('KernelStacks cannot contain metakernels')

        for kernel in self._kernels:
            if isinstance(kernel, KernelStack):
                raise ValueError('KernelStacks cannot contain KernelStacks')
            if kernel.ktype != self._ktype:
                raise ValueError('KernelStacks can only contain a single ktype')

        self._name = str(name) or self._kernels[-1].name

        # Filled in lazily when needed, using methods that override the defaults
        self._basenames = None
        self._exclusions = None
        self._prerequisites = None
        self._postrequisites = None
        self._corequisites = None

    ######################################################################################
    # Required properties
    ######################################################################################

    @property
    def basenames(self):
        """The ordered list of basenames associated with this Kernel object.

        The list excudes pre-, post-, and co-requisites.
        """

        if self._basenames is None:
            self._basenames = []
            for kernel in self._kernels:
                for basename in kernel.basenames:
                    # If a basename is duplicated, keep the later occurrence
                    if basename in self._basenames:
                        self._basenames.remove(basename)

                    self._basenames.append(basename)

        return self._basenames

    ######################################################################################
    # Exclusions and pre-, post-, co-requisites
    ######################################################################################

    @property
    def exclusions(self):
        """The set of excluded kernel file basenames for this kernel."""

        if self._exclusions is None:
            for kernel in self._kernels:
                self.exclude(*kernel.exclusions)

        return self._exclusions

    @property
    def prerequisites(self):
        """The set of prerequisite kernels for this kernel.

        A prerequisite kernels will always be furnished, but at lower precedence, when
        this kernel is furnished. Prerequisites are always of the same ktype as the given
        kernel.
        """

        if self._prerequisites is None:
            for kernel in self._kernels:
                self.require(kernel.prerequisites, above=False)

            for kernel in self._kernels[:-1]:
                self.require(*kernel, above=False)

        return self._prerequisites

    @property
    def postrequisites(self):
        """The set of post-requisite kernels for this kernel.

        A post-requisite kernels will always be furnished, and at higher precedence, when
        this kernel is furnished. Post-requisites are always of the same ktype as the
        given kernel.
        """

        if self._postrequisites is None:
            for kernel in self._kernels:
                self.require(*kernel.postrequisites, above=True)

        return self._postrequisites

    @property
    def corequisites(self):
        """The set of co-requisite kernels for this kernel.

        A co-requisite kernels will always be furnished when this kernel is furnished.
        Co-requisites are always of a different ktype than the given kernel.
        """

        if self._corequisites is None:
            for kernel in self._kernels:
                self.require(*kernel.corequisites)

        return self._corequisites

    ######################################################################################
    # Furnished kernel management
    ######################################################################################

    def furnish(self, tmin=None, tmax=None, ids=None, minloc=0):
        """Furnish this Kernel object at highest precedence for the specified range of
        times and the specified set of NAIF IDs.

        This method returns the index of the highest-precedence kernel

        Overlapping, excluded kernels are unloaded. Pre-, post-, and co-requisites are
        also furnished as needed.

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            ids         NAIF ID or set of NAIF IDs.
            minloc      optional specification of an index such that every basename to be
                        furnished will be at or above this index in the list of furnished
                        kernels.

        Return:         the index of the basename of the highest furnished basename.
        """

        for kernel in self._kernels:
            minloc = Kernel.furnish(kernel, tmin=tmin, tmax=tmax, ids=ids, minloc=minloc)

        return minloc

    def unload(self, tmin=None, tmax=None, ids=None, refloc=0):
        """Unload any basename of this kernel that overlaps the time range or kernel list.

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            ids         NAIF ID or set of NAIF IDs.
            loc         optional reference index into the list of furnished kernels.

        Return          new location of the given index. The value will change for each
                        basename below this location that is unloaded.
        """

        for kernel in self._kernels:
            refloc = Kernel.unload(kernel, tmin=tmin, tmax=tmax, ids=ids, refloc=refloc)

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
        for kernel in self._kernels:
            kernel_basenames = Kernel.used(kernel, tmin=tmin, tmax=tmax, ids=ids)
            for basename in kernel_basenames:
                # If a basename is duplicated, keep the later occurrence
                if basename in kernel_basenames:
                    basenames.remove(basename)
                basenames.append(basename)

        return basenames

##########################################################################################
