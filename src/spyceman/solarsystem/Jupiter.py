##########################################################################################
# spyceman/solarsystem/Jupiter.py
##########################################################################################
"""Support for Jupiter-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

* `NAME`: "JUPITER".
* `ALL_MOONS`: The set of all IDs for Jupiter's moons, including aliases.
* `GALILEANS`: The set of IDs of the Galileo satellites.
* `CLASSICAL`: Same as GALILIEANS.
* `SMALL_INNER`: The set of IDs of the small inner moons.
* `REGULAR`: The set of IDs of the regular satellites.
* `IRREGULAR`: The set of IDs of the Jovian irregular satellites, including their aliases.
* `UNNAMED`: The set of IDs of moons that are not yet officially named.
* `BODY_ID`: The NAIF ID of Jupiter.
* `SYSTEM`: The set of IDs of the planet and all inner or classical moons.
* `ALL_IDS`: The set of IDs of the planet and all moons, including their aliases.
* `BARYCENTER`: The NAIF ID of the Jupiter system barycenter.
* `BODY_IDS`: Dictionary that maps every body name to its body ID.
* `BODY_NAMES`: Dictionary that maps every body ID to its name.
* `FRAME_ID`: The NAIF ID of the Jupiter rotation frame.
* `FRAME_IDS`: Dictionary that maps every body name to its frame ID.
* `FRAME_CENTERS`: Dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

* `spk()`: Function returning a Kernel object derived from one or more Jupiter SPK files.
"""

import warnings

from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman._cspyce     import CSPYCE
from spyceman._spicefunc  import _spicefunc

##########################################################################################
# Managed list of known Jovian moons and their SPICE IDs
##########################################################################################

_JUPITER_ALIASES = [
    # Jupiter [new code, old code(s)], [formal name, provisional name(s)]
    [[  549, 55054       ], ['KORE'         , 'S/2003_J_14', 'S2003_J14']],
    [[  550, 55057       ], ['HERSE'        , 'S/2003_J_17', 'S2003_J17']],
    [[  551, 55072       ], [                 'S/2010_J_1' ]],
    [[  552, 55073       ], [                 'S/2010_J_2' ]],
    [[  553, 55076       ], ['DIA'          , 'S/2000_J_11']],
    [[  554              ], [                 'S/2016_J_1' ]],
    [[  555, 55058, 55069], [                 'S/2003_J_18', 'S2003_J18']],
    [[  556, 55075       ], [                 'S/2011_J_2' ]],
    [[  557, 55063       ], ['EIRENE'       , 'S/2003_J_5' , 'S2003_J5' ]],
    [[  558, 55055, 55067], ['PHILOPHROSYNE', 'S/2003_J_15', 'S2003_J15']],
    [[  559              ], [                 'S/2017_J_1' ]],
    [[  560, 55053, 55061], ['EUPHEME'      , 'S/2003_J_3' , 'S2003_J3' ]],
    [[  561, 55059, 55070], [                 'S/2003_J_19', 'S2003_J19']],
    [[  562              ], [                 'S/2016_J_2' ]],
    [[  563              ], [                 'S/2017_J_2' ]],
    [[  564              ], [                 'S/2017_J_3' ]],
    [[  565              ], ['PANDIA'       , 'S/2017_J_4' ]],
    [[  566              ], [                 'S/2017_J_5' ]],
    [[  567              ], [                 'S/2017_J_6' ]],
    [[  568              ], [                 'S/2017_J_7' ]],
    [[  569              ], [                 'S/2017_J_8' ]],
    [[  570              ], [                 'S/2017_J_9' ]],
    [[  571              ], ['ERSA'         , 'S/2018_J_1' ]],
    [[  572, 55074       ], [                 'S/2011_J_1' ]],
    [[55501, 55051, 55060], [                 'S/2003_J_2' , 'S2003_J2' ]],
    [[55502, 55062       ], [                 'S/2003_J_4' , 'S2003_J4' ]],
    [[55503, 55049, 55064], [                 'S/2003_J_9' , 'S2003_J9' ]],
    [[55504, 55050, 55065], [                 'S/2003_J_10', 'S2003_J10']],
    [[55505, 55052, 55066], [                 'S/2003_J_12', 'S2003_J12']],
    [[55506, 55056, 55068], [                 'S/2003_J_16', 'S2003_J16']],
    [[55507, 55071       ], [                 'S/2003_J_23']],
    [[55508              ], [                 'S/2003_J_24']],
    [[55509              ], [                 'S/2011_J_3' ]],
    [[55510              ], [                 'S/2018_J_2' ]],
    [[55511              ], [                 'S/2018_J_3' ]],
    [[55512              ], [                 'S/2021_J_1' ]],
    [[55513              ], [                 'S/2021_J_2' ]],
    [[55514              ], [                 'S/2021_J_3' ]],
    [[55515              ], [                 'S/2021_J_4' ]],
    [[55516              ], [                 'S/2021_J_5' ]],
    [[55517              ], [                 'S/2021_J_6' ]],
    [[55518              ], [                 'S/2016_J_3' ]],
    [[55519              ], [                 'S/2016_J_4' ]],
    [[55520              ], [                 'S/2018_J_4' ]],
    [[55521              ], [                 'S/2022_J_1' ]],
    [[55522              ], [                 'S/2022_J_2' ]],
    [[55523              ], [                 'S/2022_J_3' ]],
]

NAME       = 'JUPITER'
BODY_ID    = 599
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(501, 573)
for _body_id in ALL_MOONS:
    _body_name, _found = CSPYCE.bodc2n(_body_id)
    if _found:
        BODY_IDS[_body_name] = _body_id
        BODY_NAMES[_body_id] = _body_name

# Update the irregulars and their aliases
_warned = False
for _body_ids, _body_names in _JUPITER_ALIASES:
    try:
        CSPYCE.define_body_aliases(*(_body_names + _body_ids))
    except RuntimeError:
        if not _warned:
            warnings.warn(f'Pool overflow at f{tuple(_body_names + _body_ids)}')
            _warned = True

    ALL_MOONS |= set(_body_ids)
    for _body_name in _body_names:
        BODY_IDS[_body_name] = _body_ids[0]
    for _body_id in _body_ids:
        BODY_NAMES[_body_id] = _body_names[0]

# Categorize moons
CLASSICAL = _srange(501, 505)
GALILEANS = CLASSICAL
SMALL_INNER = {505} | _srange(514, 518)
REGULAR = CLASSICAL | SMALL_INNER

UNNAMED = set()
IRREGULAR = set()
for (_body_ids, _body_names) in _JUPITER_ALIASES:
    if not set(_body_ids) & REGULAR:
        IRREGULAR |= set(_body_ids)
    if '_' in _body_names[0]:
        UNNAMED |= set(_body_ids)

SYSTEM  = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS = {BODY_ID} | ALL_MOONS

##########################################################################################
# Frames
##########################################################################################

FRAME_ID, _frame_name, _found = CSPYCE.cidfrm(NAME)
FRAME_IDS = {NAME: FRAME_ID}
FRAME_CENTERS = {FRAME_ID: BODY_ID}
for _body_name, _body_id in BODY_IDS.items():
    _frame_id, _frame_name, _found = CSPYCE.cidfrm(_body_id)
    if not _found:
        _frame_id = _body_id    # if not already defined, use the body ID as the frame ID

    FRAME_IDS[_body_name] = _frame_id
    FRAME_CENTERS[_frame_id] = _body_id

##########################################################################################
# SPKs
##########################################################################################

from ._JUPITER_SPKS import _JUPITER_SPKS

_spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

_rule = Rule(r'jup(NNN).*\.bsp', source=_spk_source, dest='Jupiter/SPK', planet=NAME,
             family='Jupiter-SPK')

_default_body_ids = {False: SYSTEM, True: ALL_IDS}

_spk_docstrings = {'irregular': """\
        irregular (bool, optional): True to include Jupiter's irregular satellites in
            the returned Kernel object. Otherwise, unless a list of NAIF IDs is
            explicitly provided, the returned Kernel covers only Jupiter's inner
            satellites.
"""}

spk = _spicefunc('spk',
                 title = 'Jupiter satellite SPK',
                 known = _JUPITER_SPKS,
                 unknown = _rule.pattern,
                 source = _spk_source,
                 sort = _spk_sort_key,
                 exclude = False,
                 reduce = True,
                 default_ids = _default_body_ids,
                 default_ids_key = ('irregular',),
                 default_properties = {'irregular': False},
                 docstrings = _spk_docstrings)

__all__ = ['spk', 'ALL_IDS', 'ALL_MOONS', 'BARYCENTER', 'BODY_ID', 'BODY_IDS',
           'BODY_NAMES', 'CLASSICAL', 'FRAME_CENTERS', 'FRAME_ID', 'FRAME_IDS',
           'GALILEANS', 'IRREGULAR', 'NAME', 'REGULAR', 'SMALL_INNER', 'SYSTEM',
           'UNNAMED']

##########################################################################################
