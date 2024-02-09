##########################################################################################
# spyceman/hosts/Cassini/spk.py
##########################################################################################
"""Cassini SPK constructor functions:

cruise_spk()                SPK for the cruise to Saturn including the Jupiter flyby.
small_satellite_spk()       SPK for Saturn's small satellites.
irregular__satellite_spk()  SPK for Saturn's irregular satellites.
spk()                       function returning an SP (trajectory) kernel for any part of
                            the mission.
"""

from spyceman.hosts._utils import _intersect_basenames
from spyceman.kernelfile   import KernelFile
from spyceman.rule         import Rule
from spyceman.spicefunc    import spicefunc, _input_set

from ._utils import _DEFAULT_TIMES, _DEFAULT_BODY_IDS, _DEFAULT_BODY_IDS_W_IRREGULARS, \
                    _source

##########################################################################################
# Cruise SPK
##########################################################################################

from ._CRUISE_SPKS import _CRUISE_SPKS

# File names follow no pattern so all file attributes are defined manually.
# All files are "version 1".
KernelFile.set_info(_CRUISE_SPKS, version=1, family='Cassini-cruise-SPK',
                    source=_source('SPK'), dest='Cassini/SPK-cruise',
                    mission='CASSINI')

KernelFile('000331R_SK_LP0_V1P32.bsp'   , planet='VENUS')
KernelFile('000331RB_SK_V1P32_V2P12.bsp', planet='VENUS')
KernelFile('000331R_SK_V2P12_EP15.bsp'  , planet={'VENUS', 'EARTH'})
KernelFile('010420R_SCPSE_EP1_JP83.bsp' , planet={'MASURSKY', 'JUPITER'})
KernelFile('991130_MASURSKY.bsp'        , planet='MASURSKY')

cruise_spk_notes = """\
    Depending on inputs, this kernel can describe any part of the Cassini trajectory from
    launch in 1997 to Saturn approach in 2004.

    During the Jupiter flyby, the inner satellites plus Himalia, Elara, Pasiphae, Sinope,
    Lysithea, Carme, Ananke, and Leda are included.

    Version 1 is the final reconstruction.
"""

cruise_spk_docstrings = {'planet': """\
        planet      one or more of "VENUS", "EARTH", "MASURSKY", or "JUPITER", indicating
                    the phase(s) of the Cassini mission that this SPK should cover.
"""}

cruise_spk = spicefunc('cruise_spk',
            title='Cassini cruise SPKs',
            known=_CRUISE_SPKS,
            exclude=False,
            default_times=_DEFAULT_TIMES, default_times_key='planet',
            default_ids=_DEFAULT_BODY_IDS, default_ids_key='planet',
            notes=cruise_spk_notes, docstrings=cruise_spk_docstrings)

del cruise_spk_notes, cruise_spk_docstrings

##########################################################################################
# Small satellite SPK
##########################################################################################

from ._SMALL_SATELLITE_SPKS import _SMALL_SATELLITE_SPKS

# This rule will assign the dates, naif IDs, family, mission, and planet to every matching
# file.
rule = Rule(r'(YYMMDD)[ABC]P_RE_(YYDOY)_(YYDOY)\.bsp',
            family='Cassini-small-satellite-SPK',
            naif_ids=_SMALL_SATELLITE_SPKS[-1].naif_ids,
            source=_source('SPK'), dest='Cassini/SPK-small-satellites',
            mission='CASSINI', planet='SATURN')
KernelFile.mutual_veto(rule.pattern)    # only one of these at a time
_SMALL_SATELLITE_SPK_PATTERN = rule.pattern

small_satellite_spk_notes = """\
    This kernel describes the small inner satellites of Saturn during the Saturn tour.
    Included are Janus, Epimetheus, Helene, Telesto, Calypso, Atlas, Prometheus, Pandora,
    Methone, Pallene, Polydeuces, Anthe, and Aegaeon.

    Versions are identified by the release date, with the last release on 2018-09-27.
"""

small_satellite_spk = spicefunc('small_satellite_spk',
            title='Cassini small satellite SPKs',
            known=_SMALL_SATELLITE_SPKS,
            unknown=rule.pattern, source=_source('SPK'),
            exclude=True,
            default_times=(_SMALL_SATELLITE_SPKS[-1].start_time,
                           _SMALL_SATELLITE_SPKS[-1].end_time),
            default_ids=_SMALL_SATELLITE_SPKS[-1].naif_ids,
            notes=small_satellite_spk_notes)
    # The default sort is alphabetical, which is equivalent to chronological in this case.

del rule, small_satellite_spk_notes

##########################################################################################
# Irregular satellite SPK
##########################################################################################

from ._IRREGULAR_SATELLITE_SPKS import _IRREGULAR_SATELLITE_SPKS

# This rule will assign the dates, naif IDs, family, mission, and planet to every matching
# file. It also introduces the property "irregular" = True; used below.
rule = Rule(r'(YYMMDD)[ABC]P_IRRE_(YYDOY)_(YYDOY)\.bsp',
            family='Cassini-irregular-satellite-SPK',
            naif_ids=_IRREGULAR_SATELLITE_SPKS[-1].naif_ids,
            source=_source('SPK'), dest='Cassini/SPK-irregular-satellites',
            mission='CASSINI', planet='SATURN', irregular=True)
KernelFile.mutual_veto(rule.pattern)    # only one of these at a time
_IRREGULAR_SATELLITE_SPK_PATTERN = rule.pattern

irregular_satellite_spk_notes = """\
    This kernel describes all the outer, irregular satellites of Saturn during the Saturn
    tour.

    Versions are identified by release date, with the last release on 2014-08-09.
"""

irregular_satellite_spk = spicefunc('irregular_satellite_spk',
            title='Cassini irregular satellite SPKs',
            known=_IRREGULAR_SATELLITE_SPKS,
            unknown=rule.pattern, source=_source('SPK'),
            exclude=True,
            default_times=(_IRREGULAR_SATELLITE_SPKS[-1].start_time,
                           _IRREGULAR_SATELLITE_SPKS[-1].end_time),
            default_ids=_IRREGULAR_SATELLITE_SPKS[-1].naif_ids,
            notes=irregular_satellite_spk_notes)
    # The default sort is alphabetical, which is equivalent to chronological.

del rule, irregular_satellite_spk_notes

##########################################################################################
# General SPK
##########################################################################################

from ._TOUR_SPKS_V1 import _TOUR_SPKS_V1
from ._TOUR_SPKS_V2 import _TOUR_SPKS_V2, _ALT_TOUR_SPK_V2
from ._TOUR_SPKS_V3 import _TOUR_SPKS_V3

_TOUR_SPKS = _TOUR_SPKS_V1 + _TOUR_SPKS_V2 + _ALT_TOUR_SPK_V2 + _TOUR_SPKS_V3

# This rule will assign the time limits, release date, source, mission, and planet to any
# files matching the pattern.
Rule(r'(YYMMDD)R[A-Z]?_SCPSE_(YYDOY)_(YYDOY)\.bsp', naif_ids=_TOUR_SPKS_V3[-1].naif_ids,
     source=_source('SPK'), mission='CASSINI', planet='SATURN')

# Assign individual versions and destinations based on the year
v1_rule = Rule(r'(0[4-9]|1[0-7])R[A-Z]?_SCPSE_(YYDOY)_(YYDOY)\.bsp', version=1,
               dest='Cassini/SPK-tour-v1')
v2_rule = Rule(r'180628RU_SCPSE_(YYDOY)_(YYDOY)\.bsp', version=2,
               dest='Cassini/SPK-tour-v2')
v3_rule = Rule(r'200128RU_SCPSE_(YYDOY)_(YYDOY)\.bsp', version=3,
               dest='Cassini/SPK-tour-v3')

# Prepare for a future version 4
v4_rule = Rule(r'(2[1-9]|[3-9]\d)\d{4}R[A-Z]?_SCPSE_(YYDOY)_(YYDOY)\.bsp', version=4,
               dest='Cassini/SPK-tour-v4')

# Disallow different versions at the same time
KernelFile.group_vetos(v1_rule.pattern, v2_rule.pattern, v3_rule.pattern, v4_rule.pattern)

# Among the version 1 files, we need the sort order to put files in release date order,
# but with "RB_" after "R_":
#   050105RB_SCPSE_04247_04336.bsp supersedes 050105R_SCPSE_04247_04336.bsp
#   050414RB_SCPSE_05034_05060.bsp supersedes 050414R_SCPSE_05034_05060.bsp
#   050513RB_SCPSE_05097_05114.bsp supersedes 050513R_SCPSE_05097_05114.bsp
#
# Also, the global, "alt" version 2 file takes precedence over the individual version 2
# files.
def tour_spk_sort_key(basename):
    return (basename.upper().replace('R_', 'RA_')
                            .replace('180628RU_SCPSE_04183_17258',
                                     '180629RU_SCPSE_04183_17258'))

tour_spk_pattern = r'(2[1-9]|[3-9]\d)\d{4}R[U-Z]?_SCPSE_(YYDOY)_(YYDOY)\.bsp'

# Adapt cruise_spk() to receive the same inputs as spk()
def _cruise_spk_adapted(version=None, planet=None, basename=None, **keywords):

    # If only planet SATURN is required, no cruise SPK is needed
    planet = _input_set(planet)
    not_saturn = planet - {'SATURN'}
    if planet and not not_saturn:
        return None

    # If basenames are explicitly listed, but without any cruise basenames, return None
    if basename:
        basename = _intersect_basenames(basename, {rec.basename for rec in _CRUISE_SPKS})
        if not basename:
            return None

    # The version input is ignored for cruise SPKs
    return cruise_spk(version=None, planet=not_saturn, basename=basename, **keywords)

# Adapt small_satellite_spk() to receive the same inputs as spk()
def _small_satellite_spk_adapted(version=None, basename=None, **keywords):

    # Replace the version with the associated small satellite SPK release date
    version_dict = {1: '2016-11-01',
                    2: '2018-09-27',
                    3: '2018-09-27'}

    version = {version_dict[v] for v in _input_set(version, range=True)}

    # Remove explicit basenames that are not part of this SPK
    basename = _intersect_basenames(basename, _SMALL_SATELLITE_SPK_PATTERN)

    return small_satellite_spk(version=version, basename=basename, **keywords)

# Adapt irregular_satellite_spk() to receive the same inputs as spk()
def _irregular_satellite_spk_adapted(version=None, basename=None, irregular=None,
                                     **keywords):

    # Explicit irregular=False input disables this SPK
    if irregular is not None and not irregular:
        return None

    # The tour spk versions all map to the latest irregular satellite SPK
    if version is not None:
        version = '2014-08-09'

    # Remove explicit basenames that are not part of this SPK
    basename = _intersect_basenames(basename, _IRREGULAR_SATELLITE_SPK_PATTERN)

    # Note that this will return None if a set of NAIF IDs is explicitly provided but
    # one that does not include any of the irregular satellite IDs.
    return irregular_satellite_spk(version=version, basename=basename, **keywords)

spk_notes = """\
    This kernel generates an SPK Kernel object the Cassini mission or any subset thereof.
    During the Saturn tour, it includes all inner satellites and, optionally, the outer,
    irregular satellites. During the Jupiter flyby, it includes the inner Jovian moons and
    the largest irregulars. All kernels are reconstructions, not predictions.

    Version 1 contains the ongoing reconstruction of the Cassini tour during mission
    operations. This version might be appropriate for users trying to duplicate prior
    work.

    Version 2 is a prior reconstruction of the Cassini tour dated 2018-06-28. This kernel
    has known errors and should not be used unless Version 3 is unavailable.

    Version 3 is the final, reconstructed Cassini tour dated 2020-01-28.

    For the cruise to Saturn, including the Jupiter flyby, version numbers are ignored.
"""

spk_docstrings = {}
spk_docstrings['planet'] = """\
        planet      one or more of "VENUS", "EARTH", "MASURSKY", or "JUPITER", or
                    "SATURN", indicating the phase(s) of the Cassini mission that this SPK
                    should cover. If not specified, "SATURN" is the default.
"""
spk_docstrings['irregular'] = """\
        irregular   True to include Saturn's irregular satellites in the returned Kernel.
"""

spk = spicefunc('spk', title='Cassini mission SPKs',
            known=_TOUR_SPKS_V1 + _TOUR_SPKS_V2 + _ALT_TOUR_SPK_V2 + _TOUR_SPKS_V3,
            unknown=tour_spk_pattern, source=_source('SPK'),
            sort=tour_spk_sort_key,
            exclude=False, reduce=True,
            require=(_cruise_spk_adapted,
                     _small_satellite_spk_adapted,
                     _irregular_satellite_spk_adapted),
            default_times=_DEFAULT_TIMES, default_times_key='planet',
            default_ids=_DEFAULT_BODY_IDS_W_IRREGULARS,
            default_ids_key=('planet', 'irregular'),
            notes=spk_notes, docstrings=spk_docstrings,
            default_properties={'planet': 'SATURN', 'irregular': False})

del spk_notes, spk_docstrings, v1_rule, v2_rule, v3_rule, v4_rule
del _cruise_spk_adapted, _small_satellite_spk_adapted, _irregular_satellite_spk_adapted

##########################################################################################
