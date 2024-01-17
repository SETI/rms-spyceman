##########################################################################################
# spyceman/hosts/cassini/ck.py
##########################################################################################

import os

from spyceman import KernelFile, Rule, spicefunc

_SPK_SOURCE = 'https://naif.jpl.nasa.gov/pub/naif/CASSINI/kernels/ck'

if 'SPICEPATH-CASSINI-CK' in os.environ:
    _CK_DEST = os.environ['SPICEPATH']
elif 'SPICEPATH-CASSINI' in os.environ:
    _CK_DEST = os.path.join(os.path.join(os.environ['SPICEPATH'], 'CK')
elif 'SPICEPATH' in os.environ:
    _CK_DEST = os.path.join(os.path.join(os.environ['SPICEPATH'], 'Cassini', 'CK')
else
    _CK_DEST = ''

##########################################################################################
# Cruise & Jupiter SPK
##########################################################################################

_KNOWN_CRUISE_SPK_BASENAMES = ['000331R_SK_LP0_V1P32.bsp',
                               '000331RB_SK_V1P32_V2P12.bsp',
                               '000331R_SK_V2P12_EP15.bsp',
                               '010420R_SCPSE_EP1_JP83.bsp',
                               '041014R_SCPSE_01066_04199.bsp',
                               '991130_MASURSKY.bsp']
KernelFile.set_info(_KNOWN_CRUISE_SPK_BASENAMES, mission='CASSINI',
                    family='Cassini-cruise-SPK', version={1,2,3})

KernelFile('000331R_SK_LP0_V1P32.bsp'   , planet='VENUS')
KernelFile('000331RB_SK_V1P32_V2P12.bsp', planet='VENUS')
KernelFile('000331R_SK_V2P12_EP15.bsp'  , planet={'VENUS', 'EARTH'})
KernelFile('010420R_SCPSE_EP1_JP83.bsp' , planet={'MASURSKY', 'JUPITER'})
KernelFile('991130_MASURSKY.bsp'        , planet='MASURSKY')

cruise_spk = spicefunc('cruise_spk', title='Cassini cruise SPKs',
                       family='Cassini-cruise-SPK', reduce=False,
                       known=_KNOWN_CRUISE_SPK_BASENAMES,
                       source=_SPK_SOURCE, destination=_SPK_DEST)
cruise_spk.planet={'VENUS', 'EARTH', 'MASURSKY', 'JUPITER'}

##########################################################################################
# "RE" = small, inner satellites
##########################################################################################

_KNOWN_SPK_RE_BASENAMES = [
    '050615AP_RE_04002_09011.bsp',
    '050923AP_RE_04002_09011.bsp',
    '051212AP_RE_90165_14363.bsp',
    '060927AP_RE_90165_14363.bsp',
    '070424AP_RE_90165_14363.bsp',
    '070815AP_RE_90165_14363.bsp',
    '080527AP_RE_90165_18018.bsp',
    '081125AP_RE_90165_18018.bsp',
    '090507AP_RE_90165_18018.bsp',
    '100209AP_RE_90165_18018.bsp',
    '110317AP_RE_90165_18018.bsp',
    '120308AP_RE_90165_18018.bsp',
    '130412AP_RE_90165_18018.bsp',
    '140127AP_RE_90165_18018.bsp',
    '150422AP_RE_90165_18018.bsp',
    '150720AP_RE_90165_18018.bsp',
    '161101AP_RE_90165_18018.bsp',
    '180927AP_RE_90165_18018.bsp',
]

Rule(r'(YYMMDD)[ABC]P_RE_(YYDOY)_(YYDOY)\.bsp', mission='CASSINI', planet='SATURN',
     family='Cassini-small-satellites-SPK')
Rule(r'(0\d|1[0-5])\d{4}[ABC]P_RE_\d{5}_\d{5}\.bsp', version=0)
Rule(r'[2\d{5}[ABC]P_RE_\d{5}_\d{5}\.bsp', version=4)       # placeholder for the future

KernelFile('161101AP_RE_90165_18018.bsp').version = 1
KernelFile('180927AP_RE_90165_18018.bsp').version = {2,3}

re_spk = spicefunc('re_spk', title='Cassini small satellite SPKs',
                   family='Cassini-small-satellites-SPK', reduce=True, sort='alpha',
                   known=_KNOWN_SPK_RE_BASENAMES,
                   source=_SPK_SOURCE, destination=_SPK_DEST)

##########################################################################################
# "IRRE" = irregular satellites
##########################################################################################

_KNOWN_SPK_IRRE_BASENAMES = [
    '060222AP_IRRE_00256_14363.bsp',
    '061204AP_IRRE_04343_14363.bsp',
    '070223BP_IRRE_00256_14363.bsp',
    '070416BP_IRRE_00256_14363.bsp',
    '090202BP_IRRE_00256_50017.bsp',
    '110120BP_IRRE_00256_25017.bsp',
    '120711CP_IRRE_00256_25017.bsp',
    '130528BP_IRRE_00256_25017.bsp',
    '140809BP_IRRE_00256_25017.bsp',
]

Rule(r'(YYMMDD)(V)P_IRRE_(YYDOY)_(YYDOY)\.bsp', mission='CASSINI', planet='SATURN',
     family='Cassini-irregular-satellites-SPK', irregular=True) # new keyword "irregular"
Rule(r'(0\d|1[0-3])\d{4}[ABC]P_IRRE_\d{5}_\d{5}\.bsp', version=0)
Rule(r'[2\d{5}[ABC]P_IRRE_\d{5}_\d{5}\.bsp', version=4)     # placeholder for the future

KernelFile('140809BP_IRRE_00256_25017.bsp').version = {1,2,3}

irre_spk = spicefunc('irre_spk', title='Cassini irregular satellite SPKs',
                     family='Cassini-irregular-satellites-SPK', reduce=True, sort='alpha',
                     known=_KNOWN_SPK_IRRE_BASENAMES,
                     source=_SPK_SOURCE, destination=_SPK_DEST)
irre_spk.irregular = True           # Use this as a prerequisite when irregular=True

##########################################################################################
# "SCPSE" = spacecraft and major satellites
##########################################################################################

from ._SPK_RECONSTRUCTED_V1 import _SPK_RECONSTRUCTED_V1
from ._SPK_RECONSTRUCTED_V2 import _SPK_RECONSTRUCTED_V2
from ._SPK_RECONSTRUCTED_V3 import _SPK_RECONSTRUCTED_V3

_ALT_SPK_SCPSE_BASENAME_V2 = '180628RU_SCPSE_04183_17258.bsp'

_KNOWN_SPK_SCPSE_BASENAMES = (_SPK_RECONSTRUCTED_V1 + _SPK_RECONSTRUCTED_V2 +
                              _SPK_RECONSTRUCTED_V3 + _ALT_SPK_SCPSE_BASENAME_V2)

Rule(r'(YYMMDD)R[A-Z]?_SCPSE_(YYDOY)_(YYDOY)\.bsp', mission='CASSINI', planet='SATURN',
     family='Cassini-reconstructed-SPK')
Rule(r'(0[5-9]|1[0-7])\d{4}RB?_SCPSE_\d{5}_\d{5}\.bsp', version=1)
Rule(r'180628RU_SCPSE_\d{5}_\d{5}\.bsp', version=2)
Rule(r'200128RU_SCPSE_\d{5}_\d{5}\.bsp', version=3)
Rule(r'2[1-9]\d{4}R[A-Z]?_SCPSE_\d{5}_\d{5}\.bsp', version=4)   # placeholder for future
                                                                # version 4

# Among the version 1 files, we need the sort order to put files in release date order,
# but with "RB_" after "R_".
#   050105RB_SCPSE_04247_04336.bsp supersedes 050105R_SCPSE_04247_04336.bsp
#   050414RB_SCPSE_05034_05060.bsp supersedes 050414R_SCPSE_05034_05060.bsp
#   050513RB_SCPSE_05097_05114.bsp supersedes 050513R_SCPSE_05097_05114.bsp
#
# Also, the global version 2 file takes precedence over the individual version 2 file
def _SPK_SCPSE_SORT_KEY(basename):
    return basename.upper().replace('R_', 'RA_')
                           .replace('180628RU_SCPSE_04183_17258',
                                    '180629RU_SCPSE_04183_17258'))

_SPK_NOTES = """\
    This kernel describes the Cassini Saturn tour, including all inner satellites and,
    optionally, the outer, irregular satellites as well.

    Version 3 is the final, reconstructed Cassini tour from January 28, 2020.
    Version 2 is a prior reconstruction of the Cassini tour from June 28, 2018. This
        kernel has known errors and should not be used unless Version 3 is unavailable.
    Version 1 contains the reconstruction of the Cassini tour while the tour was being
        flown during 2004-2017. This version might be appropriate for users trying to
        duplicate prior work.
    All three versions provide the same SPKs for the cruise phase of the mission.

"""

DOCSTRINGS = {}
DOCSTRINGS['planet'] = """\
        planet      one or more of "VENUS", "EARTH", "MASURSKY", "JUPITER", or "SATURN",
                    indicating the phase of the Cassini mission for which this SPK is
                    desired.
"""
DOCSTRINGS['irregular'] = """\
        irregular   True to include the irregular satellites in the returned Kernel when
                    the Saturn is included.
"""

spk = spicefunc('spk', title='Cassini SPKs',
                family='Cassini-reconstructed-SPK', reduce=True,
                sort=_SPK_SCPSE_SORT_KEY,
                known=_KNOWN_SPK_SCPSE_BASENAMES,
                source=_SPK_SOURCE, destination=_SPK_DEST,
                prerequisite=(cruise_spk, re_spk, irre_spk),
                default_times=_TIME_LIMITS, time_key='planet',
                default_naif_ids=_BODY_IDS, naif_id_key='planet',
                notes=_SPK_NOTES,
                propnames=('planet', 'irregular'), docstrings=DOCSTRINGS)

##########################################################################################
