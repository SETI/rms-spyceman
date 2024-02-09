##########################################################################################
# spyceman/hosts/Cassini/ck.py
##########################################################################################
"""Cassini CK constructor functions:

gapfill_ck()    a low-precedence "gapfill" CK for the Saturn tour.
jupiter_ck()    a CK for the Jupiter flyby.
ck()            function returning a C (pointing) kernel for any part of the mission.
"""

from spyceman.kernelfile import KernelFile
from spyceman.rule       import Rule
from spyceman.spicefunc  import spicefunc
from spyceman._utils     import _input_set

from ._utils import _DEFAULT_TIMES, _DEFAULT_BODY_IDS, _source

from ._RECONSTRUCTED_CKS import _RECONSTRUCTED_CKS

# This pattern will match any Cassini CK except the original Jupiter CKs, which use
# YYMMDD dates.0
Rule(r'(YYDOY)_(YYDOY)(p[a-z]|r[abc]]).*\.bc', naif_ids={-82000}, mission='CASSINI',
     source=_source('CK'))

##########################################################################################
# Gapfill CK
##########################################################################################

from ._GAPFILL_CKS import _GAPFILL_CKS

rule = Rule(r'(YYDOY)_(YYDOY)pa_gapfill_v(NN)\.bc', family='Cassini-gapfill-CK',
            dest='Cassini/CK-gapfill', planet='SATURN', gapfill=True)
KernelFile.veto(rule.pattern, r'\1_\2pa_gapfill.*\.bc')
    # Veto other gapfill CKs for the same dates, different version.

gapfill_ck_pattern = r'\d{5}_\d{5}p[a-z]_gapfill_v\d\d\.tf'

gapfill_ck_notes = """\
        The Cassini "gapfill" CKs should always be furnished at a lower precedence than
        any other selected CKs.

        The final version released by the team is 14 (except during 2003, when the only
        version is 1).
"""

gapfill_ck = spicefunc('gapfill_ck', title='Cassini gapfill CKs',
            known=_GAPFILL_CKS,
            unknown=gapfill_ck_pattern, source=_source('CK'),
            exclude=False, reduce=True,
            default_times=('2003-01-01','2017-09-16'),
            default_ids=None,           # to match any Cassini frame ID
            notes=gapfill_ck_notes)

del gapfill_ck_pattern, gapfill_ck_notes

##########################################################################################
# Jupiter CKs
##########################################################################################

from ._JUPITER_CKS import _JUPITER_CKS

Rule(r'(YYMMDD)_(YYMMDD)(|r[ab])\.bc', family='Cassini-Jupiter-CK',
     naif_ids={-82000}, version={1,2}, source=_source('CK'),
     dest='Cassini/CK-Jupiter', mission='CASSINI', planet='JUPITER')

# These five files in _JUPITER_CKS are overrides of version=1 kernels and are specific
# to version 2.
jupiter_ck_superseders = [('001113_001116ra.bc', '001113_001118ra.bc'),
                          ('001129_001130ra.bc', '001123_001130ra.bc'),
                          ('001213_001213ra.bc', '001213_001215ra.bc'),
                          ('010121_010122ra.bc', '010121_010123ra.bc'),
                          ('010123_010124ra.bc', '010123_010128ra.bc')]
for basename, _ in jupiter_ck_superseders:
    KernelFile(basename, version=2)

# This pattern will match any "reconstructed" CK; version=3
Rule(r'(YYDOY)_(YYDOY)r[ab]\.bc', family='Cassini-reconstructed-CK', version=3)
Rule(r'(00[23]|010)\d\d_\d{5}r[ab]\.bc', planet='JUPITER')  # start time indicates Jupiter

def jupiter_ck_sort_key(basename):
    if basename[5:] == '_':     # reconstructed begin with "YYDOY_"
        return (3, basename)
    if basename in {'001113_001116ra.bc',
                    '001129_001130ra.bc',
                    '001213_001213ra.bc',
                    '010121_010122ra.bc',
                    '010123_010124ra.bc'}:
        return (2, basename)
    return (1, basename)

jupiter_ck_notes = """\
    This kernel contains the reconstructed pointing for the Jupiter flyby of late 2000
    and early 2001.

    Version 1 uses the initial pointing reconstruction from telemetry.
    Version 2, also from during and shortly after the flyby, augments Version 1 with a few
    updates to the pointing reconstruction.
    Version 3 contains the mission's final pointing reconstruction from 2018.
"""

jupiter_ck = spicefunc('jupiter_ck', title='Cassini Jupiter CKs',
            known=_JUPITER_CKS + _RECONSTRUCTED_CKS,
            sort=jupiter_ck_sort_key,
            exclude=False, reduce=False,
            superseders=jupiter_ck_superseders,
            default_times=('2000-10-01', '2001-04-01'),
            default_ids=None,           # to match any Cassini frame ID
            notes=jupiter_ck_notes)

del basename, jupiter_ck_superseders, jupiter_ck_sort_key, jupiter_ck_notes

##########################################################################################
# General CKs
##########################################################################################

from ._LIVE_CKS     import _LIVE_CKS
from ._AS_FLOWN_CKS import _AS_FLOWN_CKS

# This pattern will match any "live" CK but not a gapfill CK; version=1
Rule(r'(YYDOY)_(YYDOY)p[a-x](?!_gapfill).*\.bc', family='Cassini-live-CK', version=1,
     dest='Cassini/CK-live', planet='SATURN')

# This pattern will match any "as flown" CK; version=2
Rule(r'(YYDOY)_(YYDOY)py_as_flown\.bc', family='Cassini-as-flown-CK', version=2,
     dest='Cassini/CK-as-flown', planet='SATURN')

ck_pattern = r'\d{5}_\d{5}[pr][a-z].*\.bc'

def ck_sort_key(basename):
    """Sort prioritizing the version code pa-pz, ra-rz first."""
    basename = basename.lower()
    return (basename[11:13], basename)

# Adapt other functions to receive the same inputs as ck()
def gapfill_ck_adapted(version=None, basename=None, planet=None, gapfill=True,
                       **keywords):

    # If input property gapfill is False, no CK is needed.
    if not gapfill:
        return None

    # If any planets are listed but Saturn is not among them, no CK is needed.
    planet = _input_set(planet, default=set(_DEFAULT_BODY_IDS.keys()))
    if not planet & {'SATURN'}:
        return None

    # Identify explicit basenames that are part of the gapfill CK.
    basename = _input_set(basename)
    basename = {b for b in basename if '_gapfill' in b}

    return gapfill_ck(version=None, basename=basename, **keywords)

def jupiter_ck_adapted(version=None, basename=None, planet=None, **keywords):

    # Version 3 is the same for Jupiter and Saturn, so no special CK is needed.
    version = _input_set(version, default={1,2,3}, ranges=True)
    if not version & {1,2}:
        return None

    # If an explicit planet is listed and JUPITER is not among them, no CK is needed.
    planet = _input_set(planet, default=set(_DEFAULT_BODY_IDS.keys()))
    if not planet & {'JUPITER'}:
        return None

    # Identify explicit basenames that are part of the V1 or V2 Jupiter CK
    basename = _input_set(basename)
    basename = {b for b in basename if basename[6] == '_'}

    return jupiter_ck(version=version, basename=basename, **keywords)

ck_notes = """\
    Version 1 uses the predicted pointing during mission operations.
    Version 2 uses the final regeneration of "as flown" predicted pointing.
    Version 3 contains the mission's final pointing reconstruction from telemetry. This
    version covers the entire mission, whereas Versions 1 and 2 only apply to the Saturn
    tour.

    Note that Versions 1 and 2 have the property that pointing changes are smooth.
    Although the reconstructed pointing should be, in general, more accurate in absolute
    terms, it contains unrealistic, high-frequency "jitter", which was an artifact of the
    processing.
"""

ck_docstrings = {}
ck_docstrings['planet'] = """\
        planet      one or more of "VENUS", "EARTH", "MASURSKY", or "JUPITER", or
                    "SATURN", indicating the phase(s) of the Cassini mission that this CK
                    should cover. If not specified, "SATURN" is the default.
"""
ck_docstrings['gapfill'] = """\
        gapfill     True to include the prerequisite "gapfill" kernel during the Saturn
                    Tour; False otherwise. Default is True.
"""

ck = spicefunc('ck', title='Cassini mission CKs',
               known=_LIVE_CKS + _AS_FLOWN_CKS + _RECONSTRUCTED_CKS,
               unknown=ck_pattern, source=_source('CK'),
               sort=ck_sort_key,
               exclude=False, reduce=True,
               require=(gapfill_ck_adapted, jupiter_ck_adapted),
               default_times=_DEFAULT_TIMES, default_times_key='planet',
               default_ids=_DEFAULT_BODY_IDS, default_ids_key='planet',
               default_properties={'planet': 'SATURN', 'gapfill': True},
               notes=ck_notes, docstrings=ck_docstrings)

del ck_notes, ck_docstrings, ck_pattern, ck_sort_key
del gapfill_ck_adapted, jupiter_ck_adapted

##########################################################################################
