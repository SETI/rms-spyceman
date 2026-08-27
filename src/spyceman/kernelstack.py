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

        Parameters:
            kernels (list[Kernel], list[str]): The Kernel objects, in increasing order of
                precedence. A string is interpreted as a basename and wrapped in a
                KernelFile.
            name (str, optional): A name for this KernelStack. By default, the name of the
                highest-precedence kernel is used.

        Raises:
            ValueError: If a kernel is a metakernel or another KernelStack, or if the
                kernels do not all share a single ktype.
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

        Where a basename appears in more than one of the stacked kernels, only its last
        occurrence is retained, so it takes the precedence of its highest position.

        Returns:
            list[str]: The basenames of every stacked kernel, in increasing order of
                precedence. Pre-, post-, and co-requisites are excluded.
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
        """The set of excluded kernel file basenames for this kernel.

        Returns:
            set[str, Kernel]: The union of the exclusions of every stacked kernel.
        """

        if self._exclusions is None:
            self._exclusions = set()    # before exclude() reads this property back
            for kernel in self._kernels:
                self.exclude(*kernel.exclusions)

        return self._exclusions

    @property
    def prerequisites(self):
        """The set of prerequisite kernels for this kernel.

        A prerequisite kernels will always be furnished, but at lower precedence, when
        this kernel is furnished. Prerequisites are always of the same ktype as the given
        kernel.

        Every kernel in the stack below the highest is also a prerequisite of the stack
        as a whole, which is what preserves the load order.

        Returns:
            set[str, Kernel]: The prerequisites of the stack.
        """

        if self._prerequisites is None:
            self._prerequisites = set()     # before require() reads this property back
            for kernel in self._kernels:
                self.require(*kernel.prerequisites, above=False)

            # Every kernel below the highest is a prerequisite of the stack as a whole;
            # that is what preserves the load order.
            for kernel in self._kernels[:-1]:
                self.require(kernel, above=False)

        return self._prerequisites

    @property
    def postrequisites(self):
        """The set of post-requisite kernels for this kernel.

        A post-requisite kernels will always be furnished, and at higher precedence, when
        this kernel is furnished. Post-requisites are always of the same ktype as the
        given kernel.

        Returns:
            set[str, Kernel]: The union of the post-requisites of every stacked kernel.
        """

        if self._postrequisites is None:
            self._postrequisites = set()    # before require() reads this property back
            for kernel in self._kernels:
                self.require(*kernel.postrequisites, above=True)

        return self._postrequisites

    @property
    def corequisites(self):
        """The set of co-requisite kernels for this kernel.

        A co-requisite kernels will always be furnished when this kernel is furnished.
        Co-requisites are always of a different ktype than the given kernel.

        Returns:
            set[str, Kernel]: The union of the co-requisites of every stacked kernel.
        """

        if self._corequisites is None:
            self._corequisites = set()      # before require() reads this property back
            for kernel in self._kernels:
                self.require(*kernel.corequisites)

        return self._corequisites

    ######################################################################################
    # Furnished kernel management
    ######################################################################################

    def furnish(self, tmin=None, tmax=None, ids=None):
        """Furnish this Kernel object at highest precedence for the specified range of
        times and the specified set of NAIF IDs.

        Each stacked kernel is furnished above the one before it, which is what preserves
        the stack's order of precedence. Overlapping, excluded kernels are unloaded, and
        pre-, post-, and co-requisites are furnished as needed.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
        """

        self._furnish(tmin=tmin, tmax=tmax, ids=ids)

    def _furnish(self, tmin=None, tmax=None, ids=None, *, minloc=0, refloc=None,
                 reason=''):
        """Furnish this Kernel object at highest precedence for the specified range of
        times and the specified set of NAIF IDs.

        Each stacked kernel is furnished above the one before it, which is what preserves
        the stack's order of precedence. Overlapping, excluded kernels are unloaded, and
        pre-, post-, and co-requisites are furnished as needed.

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
            reason (str, optional): Why this kernel is being furnished: "prerequisite",
                "post-requisite", "corequisite", or blank for a direct request. Used in
                verbose mode.

        Returns:
            int, (int, int): The index of the highest-precedence basename furnished; or
                that index paired with the updated refloc, if a refloc was given.
        """

        for kernel in self._kernels:
            if refloc is None:
                minloc = kernel._furnish(tmin=tmin, tmax=tmax, ids=ids, minloc=minloc,
                                         reason=reason)
            else:
                minloc, refloc = kernel._furnish(tmin=tmin, tmax=tmax, ids=ids,
                                                 minloc=minloc, refloc=refloc,
                                                 reason=reason)

        if refloc is None:
            return minloc

        return (minloc, refloc)

    def unload(self, tmin=None, tmax=None, ids=None):
        """Unload any basename of this kernel that overlaps the time range or kernel list.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
        """

        self._unload(tmin=tmin, tmax=tmax, ids=ids)

    def _unload(self, tmin=None, tmax=None, ids=None, refloc=0, reason=''):
        """Unload any basename of this kernel that overlaps the time range or kernel list.

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

        for kernel in self._kernels:
            refloc = kernel._unload(tmin=tmin, tmax=tmax, ids=ids, refloc=refloc,
                                    reason=reason)

        return refloc

    def used(self, tmin=None, tmax=None, ids=None):
        """The ordered list of kernel basenames that are or would be used for a given
        range of times and/or a set of NAIF IDs, including pre-, post-, and co-requisites.

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.

        Returns:
            list[str]: The basenames that would be furnished, in increasing order of
                precedence, with each duplicate reduced to its last occurrence.
        """

        basenames = []
        for kernel in self._kernels:
            kernel_basenames = Kernel.used(kernel, tmin=tmin, tmax=tmax, ids=ids)
            for basename in kernel_basenames:
                # If a basename is duplicated, keep the later occurrence
                if basename in basenames:
                    basenames.remove(basename)
                basenames.append(basename)

        return basenames

##########################################################################################
