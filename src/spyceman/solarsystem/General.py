##########################################################################################
# spyceman/solarsystem/General.py
##########################################################################################
"""Support for general Solar System kernels. Last updated 2024-02-01.

Methods:
    lsk(): Function returning a Kernel object for one of the NAIF LSKs.
    pck(): Function returning a Kernel object for one of the NAIF PCKs.
    spk(): Function returning a Kernel object derived from one or more of the "dynamical
        ephemeris" SPK files.
"""

import re

from spyceman._cspyce     import _CSPYCE
from spyceman._spicefunc  import _spicefunc
from spyceman.kernelfile  import KernelFile as _KernelFile
from spyceman.rule        import Rule as _Rule
from spyceman.solarsystem import _SOURCE_URL

##########################################################################################
# LSKs
##########################################################################################

from ._NAIF_LSKS import _NAIF_LSKS

_lsk_source = (_SOURCE_URL + 'lsk', _SOURCE_URL + 'lsk/a_old_versions')

_rule = _Rule(r'naif(NNNN).*\.tls', source=_lsk_source, dest='General/LSK',
              family='NAIF-LSK')
_KernelFile.mutual_veto(_rule.pattern)   # never more than one furnished at a time

lsk = _spicefunc('lsk',
                 title = 'NAIF LSKs',
                 known = _NAIF_LSKS,
                 unknown = _rule.pattern,
                 source = _lsk_source,
                 exclude = True)

##########################################################################################
# PCKs
##########################################################################################

from ._NAIF_PCKS import _NAIF_PCKS

_pck_source = (_SOURCE_URL + 'pck', _SOURCE_URL + 'pck/a_old_versions')

_rule = _Rule(r'pck(NNNNN).*\.tpc', source=_pck_source, dest='General/PCK',
              family='NAIF-PCK')
_KernelFile.mutual_veto(_rule.pattern)   # never more than one furnished at a time

# pck00011.tpc is a special case. There's one version for SPICE Toolkit versions 66 and
# before; another for versions 67 and after. Compare the release number itself: string
# comparison happens to order "CSPICE_N0066" correctly today, but would place
# "CSPICE_N0100" before it.
_tkvrsn = re.search(r'N(\d+)', _CSPYCE.tkvrsn('toolkit'))
_toolkit_release = int(_tkvrsn.group(1)) if _tkvrsn else 0

if _toolkit_release <= 66:
    _NAIF_PCKS = [i for i in _NAIF_PCKS if i.basename != 'pck00011.tpc']
else:
    _NAIF_PCKS = [i for i in _NAIF_PCKS if i.basename != 'pck00011_n0066.tpc']

pck = _spicefunc('pck',
                 title = 'general NAIF PCKs',
                 known = _NAIF_PCKS,
                 unknown = _rule.pattern,
                 source = _pck_source,
                 exclude = True)

##########################################################################################
# Dynamical Ephemeris ("DE") SPKs
##########################################################################################

from ._DE_SPKS import _DE_SPKS

_spk_source = (_SOURCE_URL + 'spk/planets', _SOURCE_URL + 'spk/planets/a_old_versions')

_spk_body_ids = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399}
# These SPKs no longer include 499, Mars center

_rule = _Rule(r'de(NNN).*\.bsp', source=_spk_source, dest='General/SPK',
              naif_ids=_spk_body_ids, family='DE-SPK',
              planet={'MERCURY', 'VENUS', 'EARTH', 'MOON', 'MARS', 'JUPITER', 'SATURN',
              'URANUS', 'NEPTUNE', 'PLUTO'})

def _spk_sort_key(basename):
    """Sort key for the "DE" Solar System SPKs, in increasing order of precedence.

    Three adjustments are applied. An un-suffixed name sorts after the same version with
    a suffix. DE410 and DE413 sort lowest, because they were special-purpose kernels that
    should never be selected by default, although they remain available by name or
    version. DE440 and DE441 are swapped, so that DE440 takes precedence over DE441,
    which is the same kernel with extended time coverage.

    Parameters:
        basename (str): Basename of a "DE" SPK, of the form "deNNN.bsp".

    Returns:
        str: The sort key for this basename.
    """

    # A kernel file without suffix takes precedence over the same version with suffix.
    if len(basename) == 9:
        basename = basename.replace('.', '~')

    # DE410 and DE413 were mission-specific, special purpose kernels. They should never be
    # prioritized, although they can be used if specifically requested by name or version.
    version = int(basename[2:5])
    if version in (410, 413):
        return 'de000' + basename[2:]

    # Let DE440 take precedence over DE441, because DE441 is just the same kernel with
    # extended time coverage.
    if version == 440:
        return 'de441' + basename[5:]

    if version == 441:
        return 'de440' + basename[5:]

    return basename

spk = _spicefunc('spk',
                 title = '"DE" Solar System SPKs',
                 known = _DE_SPKS,
                 unknown = _rule.pattern,
                 source = _spk_source,
                 exclude = False,
                 reduce = True,
                 sort = _spk_sort_key,
                 default_ids = _spk_body_ids)

__all__ = ['lsk', 'pck', 'spk']

##########################################################################################
