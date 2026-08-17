##########################################################################################
# spyceman/hosts/_utils.py
##########################################################################################

import re

from spyceman.kernelfile import KernelFile

_BASENAME_PATTERN = re.compile(r'[\w.-]+$')


def _intersect_basenames(basenames, choices, flags=re.I):
    """The intersection of two sets of basenames. Either set can contain one or more
    regular expressions.

    Parameters:
        basenames (str, set, list, tuple): One basename or regular expression, or a
            collection of them.
        choices (str, set, list, tuple): One basename or regular expression, or a
            collection of them.
        flags (RegexFlag, optional): Compile flags to apply to any regular expression;
            default is re.IGNORECASE.

    Returns:
        set[str]: The basenames present in both inputs, after expanding every regular
            expression into the known basenames it matches.
    """

    # Check for empty input
    if not basenames:
        return set()

    # Convert each input to a set
    basenames = {basenames} if isinstance(basenames, str) else set(basenames)
    choices   = {choices}   if isinstance(choices,   str) else set(choices)

    # Augment the set of basenames with known files matching a regular expression
    patterns = {b for b in basenames if _BASENAME_PATTERN.match(b) is None}
    basenames -= patterns
    for pattern in patterns:
        more = KernelFile.find_all(pattern, exists=False, flags=flags)
        basenames |= set(more)

    # Augment the set of choices with known files matching a regular expression
    patterns = {b for b in choices if _BASENAME_PATTERN.match(b) is None}
    choices -= patterns
    for pattern in patterns:
        more = KernelFile.find_all(pattern, exists=False, flags=flags)
        choices |= set(more)

    # Return the intersection
    return basenames & choices

##########################################################################################
