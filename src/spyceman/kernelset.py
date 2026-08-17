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

        Where a basename appears more than once, only its last occurrence is retained, so
        that a repeated file takes the precedence of its latest position.

        Parameters:
            basenames (list[str], list[KernelFile]): The kernel file basenames or
                KernelFile objects to include. Every one must have the same ktype.
            ordered (bool, optional): True to preserve the load order among the basenames;
                False to allow them to be furnished in any order.
            name (str, optional): A name for this Kernel. If not provided, a name is
                derived from the basenames and their family names. The name is for user
                convenience and need not be unique.

        Raises:
            ValueError: If no basenames are given, if they are metakernels, or if they do
                not all share a single ktype.
        """

        if not basenames:
            raise ValueError('a KernelSet must contain at least one kernel file')

        self._ktype = KernelFile(basenames[0]).ktype
        if self._ktype == 'META':
            raise ValueError('KernelSets cannot contain metakernels')

        # Select unique basenames, prioritizing last occurrence
        self._basenames = []
        for basename in basenames:
            if isinstance(basename, KernelFile):
                basename = basename._basename

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
        # str(None) is the truthy string 'None', which would defeat the lazy name
        # derivation in Kernel.name.
        self._name = str(name) if name else ''

        # Filled in lazily if needed
        self._naif_ids = None
        self._time = None
        self._release_date = None
        self._version = None

##########################################################################################
