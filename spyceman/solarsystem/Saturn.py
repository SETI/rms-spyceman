##########################################################################################
# spyceman/solarsystem/Saturn.py: Kernel management for the Saturn system
##########################################################################################
"""\
Support for Saturn-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

NAME            "SATURN".
ALL_MOONS       the set of all IDs for Saturn's moons, including aliases.
CLASSICAL       the set of IDs of the "classical" satellites, Mimas to Phoebe.
SMALL_INNER     the set of IDs of the small inner moons.
REGULAR         the set of IDs of the regular satellites.
IRREGULAR       the set of IDs of Saturn's irregular satellites, including their aliases.
UNNAMED         the set of IDs of moons that are not yet officially named.
BODY_ID         the NAIF ID of Saturn.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons, including their aliases.
BARYCENTER      the NAIF ID of the Saturn system barycenter.
BODY_IDS        dictionary that maps every body name to its body ID.
BODY_NAMES      dictionary that maps every body ID to its name.

FRAME_ID        the NAIF ID of the Saturn rotation frame.
FRAME_IDS       dictionary that maps every body name to its frame ID.
FRAME_CENTERS   dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

pck()           function returning a Kernel object derived from one or more
                Saturn-specific PCK files.
spk()           function returning a Kernel object derived from one or more Saturn SPK
                files.
"""

import warnings

from spyceman.kernelfile  import KernelFile
from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman.spicefunc   import spicefunc
from spyceman._cspyce     import CSPYCE

##########################################################################################
# Managed list of known Saturnian moons and their SPICE IDs
##########################################################################################

_SATURN_ALIASES = [
    # [new code, old code(s)], [formal name, NAIF name(s)]
    [[  636, 65038], ['AEGIR'    , 'S/2004_S_10', 'S10_2004']],
    [[  637, 65039], ['BEBHIONN' , 'S/2004_S_11', 'S11_2004']],
    [[  638, 65043], ['BERGELMIR', 'S/2004_S_15', 'S15_2004']],
    [[  639, 65046], ['BESTLA'   , 'S/2004_S_18', 'S18_2004']],
    [[  640, 65037], ['FARBAUTI' , 'S/2004_S_9' , 'S9_2004' ]],
    [[  641, 65044], ['FENRIR'   , 'S/2004_S_16', 'S16_2004']],
    [[  642, 65036], ['FORNJOT'  , 'S/2004_S_8' , 'S8_2004' ]],
    [[  643, 65042], ['HATI'     , 'S/2004_S_14', 'S14_2004']],
    [[  644, 65047], ['HYRROKKIN', 'S/2004_S_19', 'S19_2004']],
    [[  645, 65049], ['KARI'     , 'S/2006_S_2' , 'S2_2006' ]],
    [[  646, 65052], ['LOGE'     , 'S/2006_S_5' , 'S5_2006' ]],
    [[  647,      ], ['SKOLL'    , 'S/2006_S_8' , 'S8_2006' ]],
    [[  648, 65054], ['SURTUR'   , 'S/2006_S_7' , 'S7_2006' ]],
    [[  650, 65053], ['JARNSAXA' , 'S/2006_S_6' , 'S06_2006']],
    [[  651, 65051], ['GREIP'    , 'S/2006_S_4' , 'S04_2006']],
    [[  652,      ], ['TARQEQ'   , 'S/2007_S_1' , 'S01_2007']],
    [[  653, 65060], ['AEGAEON'  , 'K07S4'                  ]], # temporary Cassini name
    [[  654, 65080], ['GRIDR'    , 'S/2004_S_20', 'S20_2004']],
    [[  655, 65073], ['ANGRBODA' , 'S/2004_S_22', 'S22_2004']],
    [[  656, 65071], ['SKRYMIR'  , 'S/2004_S_23', 'S23_2004']],
    [[  657, 65072], ['GERD'     , 'S/2004_S_25', 'S25_2004']],
    [[  658, 65068], [             'S/2004_S_26', 'S26_2004']],
    [[  659, 65065], ['EGGTHER'  , 'S/2004_S_27', 'S27_2004']],
    [[  660, 65066], [             'S/2004_S_29', 'S29_2004']],
    [[  661, 65078], ['BELI'     , 'S/2004_S_30', 'S30_2004']],
    [[  662, 65074], ['GUNNLOD'  , 'S/2004_S_32', 'S32_2004']],
    [[  663, 65075], ['THIAZZI'  , 'S/2004_S_33', 'S33_2004']],
    [[  664, 65076], [             'S/2004_S_34', 'S34_2004']],
    [[  665, 65069], ['ALVALDI'  , 'S/2004_S_35', 'S35_2004']],
    [[  666, 65083], ['GEIRROD'  , 'S/2004_S_38', 'S38_2004']],
    [[65067,      ], [             'S/2004_S_31', 'S31_2004']],
    [[65070,      ], [             'S/2004_S_24', 'S24_2004']],
    [[65077,      ], [             'S/2004_S_28', 'S28_2004']],
    [[65079,      ], [             'S/2004_S_21', 'S21_2004']],
    [[65081,      ], [             'S/2004_S_36', 'S36_2004']],
    [[65082,      ], [             'S/2004_S_37', 'S37_2004']],
    [[65084,      ], [             'S/2004_S_39', 'S39_2004']],
    [[65085, 65035], [             'S/2004_S_7' , 'S7_2004' ]],
    [[65086, 65040], [             'S/2004_S_12', 'S12_2004']],
    [[65088, 65045], [             'S/2004_S_17', 'S17_2004']],
    [[65089, 65048], [             'S/2006_S_1' , 'S01_2006']],
    [[65090, 65050], [             'S/2006_S_3' , 'S03_2006']],
    [[65091, 65055], [             'S/2007_S_2' , 'S02_2007']],
    [[65092, 65056], [             'S/2007_S_3' , 'S03_2007']],
    [[65093,      ], [             'S/2004_S_1' ]],
    [[65094,      ], [             'S/2019_S_2' ]],
    [[65095,      ], [             'S/2019_S_3' ]],
    [[65096,      ], [             'S/2020_S_1' ]],
    [[65097,      ], [             'S/2020_S_2' ]],
    [[65098,      ], [             'S/2004_S_40']],
    [[65100,      ], [             'S/2006_S_9' ]],
    [[65101,      ], [             'S/2007_S_5' ]],
    [[65102,      ], [             'S/2020_S_3' ]],
    [[65103,      ], [             'S/2019_S_4' ]],
    [[65104,      ], [             'S/2004_S_41']],
    [[65105,      ], [             'S/2020_S_4' ]],
    [[65106,      ], [             'S/2020_S_5' ]],
    [[65107,      ], [             'S/2007_S_6' ]],
    [[65108,      ], [             'S/2004_S_42']],
    [[65109,      ], [             'S/2006_S_10']],
    [[65110,      ], [             'S/2019_S_5' ]],
    [[65111,      ], [             'S/2004_S_43']],
    [[65112,      ], [             'S/2004_S_44']],
    [[65113,      ], [             'S/2004_S_45']],
    [[65114,      ], [             'S/2006_S_11']],
    [[65115,      ], [             'S/2006_S_12']],
    [[65116,      ], [             'S/2019_S_6' ]],
    [[65117,      ], [             'S/2006_S_13']],
    [[65118,      ], [             'S/2019_S_7' ]],
    [[65119,      ], [             'S/2019_S_8' ]],
    [[65120,      ], [             'S/2019_S_9' ]],
    [[65121,      ], [             'S/2004_S_46']],
    [[65122,      ], [             'S/2019_S_10']],
    [[65123,      ], [             'S/2004_S_47']],
    [[65124,      ], [             'S/2019_S_11']],
    [[65125,      ], [             'S/2006_S_14']],
    [[65126,      ], [             'S/2019_S_12']],
    [[65127,      ], [             'S/2020_S_6' ]],
    [[65128,      ], [             'S/2019_S_13']],
    [[65129,      ], [             'S/2005_S_4' ]],
    [[65130,      ], [             'S/2007_S_7' ]],
    [[65131,      ], [             'S/2007_S_8' ]],
    [[65132,      ], [             'S/2020_S_7' ]],
    [[65133,      ], [             'S/2019_S_14']],
    [[65134,      ], [             'S/2019_S_15']],
    [[65135,      ], [             'S/2005_S_5' ]],
    [[65136,      ], [             'S/2006_S_15']],
    [[65137,      ], [             'S/2006_S_16']],
    [[65138,      ], [             'S/2006_S_17']],
    [[65139,      ], [             'S/2004_S_48']],
    [[65140,      ], [             'S/2020_S_8' ]],
    [[65141,      ], [             'S/2004_S_49']],
    [[65142,      ], [             'S/2004_S_50']],
    [[65143,      ], [             'S/2006_S_18']],
    [[65144,      ], [             'S/2019_S_16']],
    [[65145,      ], [             'S/2019_S_17']],
    [[65146,      ], [             'S/2019_S_18']],
    [[65147,      ], [             'S/2019_S_19']],
    [[65148,      ], [             'S/2019_S_20']],
    [[65149,      ], [             'S/2006_S_19']],
    [[65150,      ], [             'S/2004_S_51']],
    [[65151,      ], [             'S/2020_S_9' ]],
    [[65152,      ], [             'S/2004_S_52']],
    [[65153,      ], [             'S/2007_S_9' ]],
    [[65154,      ], [             'S/2004_S_53']],
    [[65155,      ], [             'S/2020_S_10']],
    [[65156,      ], [             'S/2019_S_21']],
    [[65157,      ], [             'S/2006_S_20']],
]

NAME       = 'SATURN'
BODY_ID    = 699
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(601, 667)
for body_id in ALL_MOONS:
    body_name, found = CSPYCE.bodc2n(body_id)
    if found:
        BODY_IDS[body_name] = body_id
        BODY_NAMES[body_id] = body_name

# Update the irregulars and their aliases
warned = False
for body_ids, body_names in _SATURN_ALIASES:
    try:
        CSPYCE.define_body_aliases(*(body_names + body_ids))
    except RuntimeError:
        if not warned:
            warnings.warn(f'Pool overflow at f{tuple(body_names + body_ids)}')
            warned = True

    ALL_MOONS |= set(body_ids)
    for body_name in body_names:
        BODY_IDS[body_name] = body_ids[0]
    for body_id in body_ids:
        BODY_NAMES[body_id] = body_names[0]

# Categorize moons
CLASSICAL = _srange(601, 609)                       # excludes Phoebe (609) for now
SMALL_INNER = _srange(610, 619) | _srange(632, 636) | {649, 653}
REGULAR = CLASSICAL | SMALL_INNER

UNNAMED = set()
IRREGULAR = set()
for (body_ids, body_names) in _SATURN_ALIASES:
    if not set(body_ids) & REGULAR:
        IRREGULAR |= set(body_ids)
    if '_' in body_names[0]:
        UNNAMED |= set(body_ids)

# Add Phoebe as a classical
CLASSICAL.add(609)

SYSTEM  = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS = {BODY_ID} | ALL_MOONS

del _srange, body_id, body_ids, body_name, body_names, warned

##########################################################################################
# Frames
##########################################################################################

FRAME_ID, frame_name, found = CSPYCE.cidfrm(NAME)
FRAME_IDS = {NAME: FRAME_ID}
FRAME_CENTERS = {FRAME_ID: BODY_ID}
for body_name, body_id in BODY_IDS.items():
    frame_id, frame_name, found = CSPYCE.cidfrm(body_id)
    if not found:
        frame_id = body_id      # if not already defined, use the body ID as the frame ID

    FRAME_IDS[body_name] = frame_id
    FRAME_CENTERS[frame_id] = body_id

del body_id, body_name, frame_id, frame_name, found

##########################################################################################
# SPKs
##########################################################################################

from ._SATURN_SPKS import _SATURN_SPKS

spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

rule = Rule(r'sat(NNN).*\.bsp', source=spk_source, dest='Saturn/SPK', planet=NAME,
            family='Saturn-SPK')

default_body_ids = {False: SYSTEM, True: ALL_IDS}

spk_docstrings = {'irregular': """\
        irregular   True to include Saturn's irregular satellites in the returned Kernel
                    object. Otherwise, unless a list of NAIF IDs is explicitly provided,
                    the returned Kernel will only cover Saturn's inner satellites.
"""}

spk = spicefunc('spk', title='Saturn satellite SPK',
                known=_SATURN_SPKS,
                unknown=rule.pattern, source=spk_source,
                sort=_spk_sort_key,
                exclude=False, reduce=True,
                default_ids=default_body_ids, default_ids_key=('irregular',),
                docstrings=spk_docstrings)

del spk_source, rule, default_body_ids, spk_docstrings, _spk_sort_key

##########################################################################################
# PCKs
##########################################################################################

from ._CASSINI_ROCK_PCKS import _CASSINI_ROCK_PCKS
from ._SATURN_MST_PCKS import _SATURN_MST_PCKS
from ._SATURN_SSD_PCKS import _SATURN_SSD_PCKS

pck_source = _SOURCE + 'pck'

name_to_body_id_set = {k.lower():{v} for k,v in BODY_IDS.items() if '_' not in k}

rule1 = Rule(r'cpck_rock_(DDMONYYYY)\.tpc', version=1, origin='CASSINI', planet='SATURN',
             source=pck_source, dest='Saturn/PCK-Cassini', family='Saturn-Cassini-PCK')
KernelFile.mutual_veto(rule1.pattern)                   # never more than one furnished

rule2 = Rule(r'(?P<naif_ids>[a-z]+)_mst201[38]\.bpc', version=1,
             naif_ids=name_to_body_id_set, origin='MST', planet='SATURN',
             source=pck_source, dest='Saturn/PCK-MST', family='Saturn-MST-PCK')
KernelFile.supersede(rule2.pattern, r'pck\d{5}\.tpc')   # supersedes any standard PCK

rule3 = Rule(r'(?P<naif_ids>[a-z]+)_ssd_(YYMMDD)_v(N+)\.tpc',
             naif_ids=name_to_body_id_set, source=pck_source, dest='Saturn/PCK-SSD',
             origin='SSD', planet='SATURN', family='Saturn-SSD-PCK')
KernelFile.supersede(r'enceladus_ssd_.*\.tpc', r'pck\d{5}.*\.tpc')
    # According to the documentation, the Enceladus file can only be furnished above the
    # general PCK.

# Precedence order is Cassini, MST, SSD.
def pck_sort_order(basename):
    if basename[:4] == 'cpck':
        return (0, basename)
    if '_mst201' in basename:
        return (1, basename)
    return (2, basename)

pck_notes = """\
    This function generates a Planetary Constants Kernel object for one or more of
    Saturn's satellites. It should be furnished after one of the general PCKs from NAIF,
    e.g., "pck00011.tpc".

    The "CASSINI"-origin kernels include masses, shapes, and rotation states of all the
    small, inner moons and all of the irregular satellites known at the time of the
    mission.

    The "MST" kernels provide binary descriptions of the irregular rotations of the inner
    moons Aegaeon, Atlas, Calypso, Daphnis, Enceladus, Epimetheus, Helene, Janus, Methone,
    Pallene, Pan, and Telesto.

    The "SSD" kernels currently only provides a new rotation model for Enceladus.
"""

pck_docstrings = {'origin': """\
        producer    use "CASSINI" for one of the Cassini "rocks" PCKs; "MST" for or more
                    of the inner satellite rotation models by Matt Tiscareno; "SSD" for
                    a later rotation model from JPL's Solar System Dynamics team. To
                    combine multiple sources, use a set, list, or tuple. An input value of
                    None uses all sources.
"""}

pck = spicefunc('pck', title='Saturn satellite PCK',
                known=_CASSINI_ROCK_PCKS + _SATURN_MST_PCKS + _SATURN_SSD_PCKS,
                unknown=(rule1.pattern, rule3.pattern), source=pck_source,
                sort=pck_sort_order,
                exclude=False, reduce=True,
                notes=pck_notes, docstrings=pck_docstrings)

del pck_source, name_to_body_id_set, rule1, rule2, rule3, pck_sort_order, pck_notes
del pck_docstrings
del spicefunc, _SOURCE

##########################################################################################
