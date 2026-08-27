##########################################################################################
# spyceman/metakernel.py
##########################################################################################
"""Definition of the Metakernel subclass of class Kernel."""

from spyceman.kernel      import Kernel
from spyceman.kernelfile  import KernelFile
from spyceman.kernelset   import KernelSet
from spyceman.kernelstack import KernelStack
from spyceman._ktypes     import _KTYPES


class Metakernel(Kernel):
    """Representation of a single SPICE metakernel file."""

    _ktype = 'META'  # fixed value for every instance of this subclass

    def __init__(self, *kernels, name=''):
        """Construct a Metakernel object for one or more Kernel objects or basenames.

        Kernels are grouped by ktype. A ktype contributing a single kernel is stored as
        that kernel; one contributing several file basenames becomes an ordered KernelSet;
        one contributing several Kernel objects becomes a KernelStack. Given a single
        existing metakernel, its contents are unpacked and re-grouped.

        Parameters:
            *kernels (Kernel, str): The Kernel objects or kernel file basenames that this
                metakernel comprises.
            name (str, optional): A name for this Metakernel. Given a single input kernel,
                its name is used by default.

        Raises:
            ValueError: If no kernels are given, or if one of them is itself a metakernel
                and is not the sole input.
        """

        if not kernels:             # pragma: no branch
            raise ValueError('at least one kernel must be specified')

        self._name = name
        self._basenames = None      # filled in if needed

        # Replace a single metakernel by its list of basenames
        if len(kernels) == 1:
            kernel = Kernel.as_kernel(kernels[0])
            self._name = name or kernel.name    # re-use the name of the single input
            if kernel.ktype == 'META':
                kernels = kernel.meta_basenames

        # Create a dictionary ktype -> list of kernels or basenames
        self._kdict = {}
        for kernel in kernels:
            ktype = Kernel.as_kernel(kernel).ktype
            if ktype == 'META':
                raise ValueError('Metakernels cannot contain metakernels')
            self._kdict.setdefault(ktype, []).append(kernel)

        # Convert to a dictionary ktype -> Kernel of some subclass
        for ktype, klist in self._kdict.items():
            if len(klist) == 1:
                self._kdict[ktype] = Kernel.as_kernel(klist[0])
            elif all(isinstance(k, (str, KernelFile)) for k in klist):
                basenames = [Kernel.as_kernel(k).basename for k in klist]
                self._kdict[ktype] = KernelSet(basenames, ordered=True)
            else:
                kernels = [Kernel.as_kernel(k) for k in klist]
                self._kdict[ktype] = KernelStack(kernels)

    def _add_to_set(self, same_ktype_set, diff_ktype_set, kernels):
        """Add each kernel to either the set of same-type or different-type kernels.

        This overrides the default method to prevent a metakernel from having exclusions
        or requirements.

        Parameters:
            same_ktype_set (set): The set that would receive kernels sharing this kernel's
                ktype.
            diff_ktype_set (set): The set that would receive kernels of a different ktype.
            kernels (tuple): The kernels that would be added.

        Raises:
            ValueError: Always, because a metakernel can have neither exclusions nor
                requirements.
        """

        raise ValueError('a metakernel cannot have exclusions or requirements')

    @property
    def basenames(self):
        """The ordered list of basenames associated with this Kernel object.

        Returns:
            list[str]: The basenames of every kernel in this metakernel, ordered by ktype
                so that each appears after the ktypes it might depend upon.
        """

        basenames = []
        for ktype in _KTYPES:
            kernel = self._kdict.get(ktype)
            if kernel is not None:
                basenames += kernel.basenames

        return basenames

    @property
    def subkernels(self):
        """A list of the included kernel objects.

        Returns:
            list[Kernel]: One Kernel object per ktype represented in this metakernel.
        """
        return list(self._kdict.values())

############################################################
# Enable the Kernel class to access subclass KernelFile
############################################################

Kernel.Metakernel = Metakernel

##########################################################################################
