##########################################################################################
# spyceman/kernelset.py
##########################################################################################
"""KernelSet is a subclass of Kernel that represents a set of SPICE kernel files that can
be furnished together.
"""

from spyceman.kernel     import Kernel
from spyceman.kernelfile import KernelFile

class KernelSet(Kernel):
    """Kernel subclass representing a set of SPICE kernel files that can be furnished
    together.
    """

    def __init__(self, basenames, *, ordered=False, name=None):
        """Constructor.

        Inputs:
            basenames   list of kernel file basenames or KernelFiles to be included.
            ordered     True to ensure that the load order among the basenames is
                        preserved; False to allow the basenames within this KernelSet to
                        be loaded in any order.
            name        optional name string for this Kernel. If not provided, a name
                        will be derived from the basenames and their family names. This
                        string is entirely for user convenience and need not be unique.
        """

        self._ktype = KernelFile(basenames[0])._ktype
        if self._ktype == 'META':
            raise ValueError('KernelSets cannot contain metakernels')

        # Select unique basenames, prioritizing last occurrence
        self._basenames = []
        for basename in basenames:
            if isinstance(basename, KernelFile):
                basename = KernelFile._basename

            if KernelFile(basename).ktype != self._ktype:
                raise ValueError('KernelSets can only contain a single ktype')

            try:
                loc = self._basenames.index(basename)
            except ValueError:
                pass
            else:
                self._basenames.pop(loc)

            self._basenames.append(basename)

        self._is_ordered = bool(ordered)
        self._name = str(name)

        # Filled in lazily if needed
        self._naif_ids = None
        self._time = None
        self._release_date = None
        self._version = None

##########################################################################################
