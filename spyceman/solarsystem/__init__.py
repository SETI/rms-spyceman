##########################################################################################
# spyceman/solarsystem/general.py
##########################################################################################

__all__ = []

_SOURCE = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/'

from spyceman.rule import Rule

def _spk_sort_key(basename):
    """Files like "satNNN.bsp" sort after those with a suffix following NNN."""
    return basename.replace('.', '~') if len(basename) <= 10 else basename

def _srange(*args):
    """Convenience function for set(range(*args))."""
    return set(range(*args))

##########################################################################################
