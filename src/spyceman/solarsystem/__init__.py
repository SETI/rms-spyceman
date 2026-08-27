##########################################################################################
# spyceman/solarsystem/__init__.py
##########################################################################################

_SOURCE_URL = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/'


def _spk_sort_key(basename):
    """Sort key placing files like "satNNN.bsp" after those with a suffix following NNN.

    A tilde sorts after every character that can appear in a basename, so substituting it
    for the period in a short, un-suffixed name pushes that name to the end of its group.

    Parameters:
        basename (str): Basename of a kernel file.

    Returns:
        str: The sort key for this basename.
    """
    return basename.replace('.', '~') if len(basename) <= 10 else basename


def _srange(*args):
    """Convenience function equivalent to set(range(*args)).

    Parameters:
        *args (int): The arguments accepted by range(): stop, or start and stop, or
            start, stop and step.

    Returns:
        set[int]: The integers produced by range() over the given arguments.
    """
    return set(range(*args))


__all__ = []

##########################################################################################
