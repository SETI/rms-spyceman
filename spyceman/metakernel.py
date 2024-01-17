##########################################################################################
# kernel/metakernel.py
##########################################################################################
"""Definition of the Metakernel subclass of class KernelFile."""

from spyceman.kernel      import Kernel
from spyceman.kernelfile  import KernelFile
from spyceman.kernelset   import KernelSet
from spyceman.kernelstack import KernelStack
from spyceman._ktypes     import _KTYPES

class Metakernel(Kernel):
    """Representation of a single SPICE metakernel file."""

    _ktype = 'META'                 # fixed value for every instance of this subclass

    def __init__(self, *kernels, name=''):
        """Construct a Metakernel object for one or more Kernel objects or basenames."""

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
        or reqirements.
        """

        raise ValueError('a metakernel cannot have exclusions or requirements')

    @property
    def basenames(self):
        """The ordered list of basenames associated with this Kernel object."""

        basenames = []
        for ktype in _KTYPES:
            basenames += self._kdict.get(ktype, [])

    @property
    def subkernels(self):
        """A list of the included kernel objects."""
        return list(self._kdict.values())

############################################################
# Enable the Kernel class to access subclass KernelFile
############################################################

Kernel.Metakernel = Metakernel

##########################################################################################
