##########################################################################################
# spyceman/__init__.py
##########################################################################################

from spyceman.kernel      import Kernel
from spyceman.kernelfile  import KernelFile, KTuple
from spyceman.kernelset   import KernelSet
from spyceman.kernelstack import KernelStack
from spyceman.metakernel  import Metakernel
from spyceman.recipe      import Recipe
from spyceman.rule        import Rule

try:
    from ._version import __version__
except ImportError:                         # pragma nocover
    __version__ = 'Version unspecified'

__all__ = ['Kernel', 'KernelFile', 'KTuple', 'KernelSet', 'KernelStack', 'Metakernel',
           'Recipe', 'Rule']

##########################################################################################
