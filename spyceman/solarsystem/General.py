##########################################################################################
# spyceman/solarsystem/General.py
##########################################################################################
"""\
Support for general Solar System kernels. Last updated 2024-02-01.

The following attributes are defined:

lsk()       function returning a Kernel object for one of the NAIF LSKs.
pck()       function returning a Kernel object for one of the NAIF PCKs.
spk()       function returning a Kernel object derived from one or more of the "dynamical
            ephemeris" SPK files.
"""

from spyceman.kernelfile  import KernelFile
from spyceman.rule        import Rule
from spyceman.solarsystem import _SOURCE
from spyceman.spicefunc   import spicefunc
from spyceman._cspyce     import CSPYCE

##########################################################################################
# LSKs
##########################################################################################

from ._NAIF_LSKS import _NAIF_LSKS

lsk_source = (_SOURCE + 'lsk', _SOURCE + 'lsk/a_old_versions')

rule = Rule(r'naif(NNNN).*\.tls', source=lsk_source, dest='General/LSK',
            family='NAIF-LSK')
KernelFile.mutual_veto(rule.pattern)    # never more than one furnished at a time

lsk = spicefunc('lsk', title='NAIF LSKs',
                known=_NAIF_LSKS,
                unknown=rule.pattern, source=lsk_source,
                exclude=True)

del lsk_source, rule

##########################################################################################
# PCKs
##########################################################################################

from ._NAIF_PCKS import _NAIF_PCKS

pck_source = (_SOURCE + 'pck', _SOURCE + 'pck/a_old_versions')

rule = Rule(r'pck(NNNNN).*\.tpc', source=pck_source, dest='General/PCK',
            family='NAIF-PCK')
KernelFile.mutual_veto(rule.pattern)    # never more than one furnished at a time

# pck00011.tpc is a special case. There's one version for SPICE Toolkit versions 66 and
# before; another for versions 67 and after.
if CSPYCE.tkvrsn('toolkit') <= 'CSPICE_N0066':
    _NAIF_PCKS = [i for i in _NAIF_PCKS if i.basename != 'pck00011.tpc']
else:
    _NAIF_PCKS = [i for i in _NAIF_PCKS if i.basename != 'pck00011_n0066.tpc']

pck = spicefunc('pck', title='general NAIF PCKs',
                known=_NAIF_PCKS,
                unknown=rule.pattern, source=pck_source,
                exclude=True)

del pck_source, rule

##########################################################################################
# Dynamical Ephemeris ("DE") SPKs
##########################################################################################

from ._DE_SPKS import _DE_SPKS

spk_source = (_SOURCE + 'spk/planets', _SOURCE + 'spk/planets/a_old_versions')

spk_body_ids = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399}
    # These SPKs no longer include 499, Mars center

rule = Rule(r'de(NNN)\.bsp', source=spk_source, dest='General/SPK',
            naif_ids=spk_body_ids, family='DE-SPK',
            planet={'MERCURY', 'VENUS', 'EARTH', 'MOON', 'MARS', 'JUPITER', 'SATURN',
                    'URANUS', 'NEPTUNE', 'PLUTO'})

def spk_sort_key(basename):

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

spk = spicefunc('spk', title='"DE" Solar System SPKs',
                known=_DE_SPKS,
                unknown=rule.pattern, source=spk_source,
                exclude=False, reduce=True,
                sort=spk_sort_key,
                default_ids=spk_body_ids)

del rule, spk_source, spk_body_ids
del spicefunc, _SOURCE

##########################################################################################
