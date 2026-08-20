##########################################################################################
# spyceman/solarsystem/Uranus.py
##########################################################################################
"""Support for Uranus-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

* `NAME`: "URANUS".
* `ALL_MOONS`: The set of all IDs for Uranus's moons, including aliases.
* `CLASSICAL`: The set with the IDs of Miranda through Oberon.
* `SMALL_INNER`: The set of IDs of the small inner moons.
* `REGULAR`: The set of IDs of the regular regular Uranian moons.
* `IRREGULAR`: The set of IDs of the Uranian irregular satellites.
* `UNNAMED`: The set of IDs of moons that are not yet officially named.
* `BODY_ID`: The body ID of Uranus.
* `SYSTEM`: The set of IDs of the planet and all inner or classical moons.
* `ALL_IDS`: The set of IDs of the planet and all moons.
* `BARYCENTER`: The NAIF ID of the Uranus system barycenter.
* `BODY_IDS`: Dictionary that maps every body name to its body ID.
* `BODY_NAMES`: Dictionary that maps every body ID to its name.
* `FRAME_ID`: The NAIF ID of the Uranus rotation frame.
* `FRAME_IDS`: Dictionary that maps every body name to its frame ID.
* `FRAME_CENTERS`: Dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

* `spk()`: Function returning a Kernel object derived from one or more Uranus SPK files.
"""

import warnings

from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman._cspyce     import CSPYCE
from spyceman._spicefunc  import _spicefunc

##########################################################################################
# Body IDs
##########################################################################################

NAME       = 'URANUS'
BODY_ID    = 799
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(701, 728)
for _body_id in ALL_MOONS:
    _body_name, _found = CSPYCE.bodc2n(_body_id)
    if _found:
        BODY_IDS[_body_name] = _body_id
        BODY_NAMES[_body_id] = _body_name
    else:
        warnings.warn(f'name not identified for body {_body_id}', stacklevel=2)

# Categorize moons
CLASSICAL = _srange(701, 706)               # Miranda through Oberon
SMALL_INNER = _srange(706, 716) | {725, 726, 727}
REGULAR = CLASSICAL | SMALL_INNER
IRREGULAR = ALL_MOONS - REGULAR
UNNAMED = set()

SYSTEM  = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS = {BODY_ID} | ALL_MOONS

##########################################################################################
# Frame IDs
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

from ._URANUS_SPKS import _URANUS_SPKS

_spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

_rule = Rule(r'ura(NNN).*\.bsp', source=_spk_source, dest='Uranus/SPK', planet=NAME,
             family='Uranus-SPK')

_default_body_ids = {False: SYSTEM, True: ALL_IDS}

_spk_docstrings = {'irregular': """\
        irregular (bool, optional): True to include Uranus's irregular satellites in
            the returned Kernel object. Otherwise, unless a list of NAIF IDs is
            explicitly provided, the returned Kernel covers only Uranus's inner
            satellites.
"""}

spk = _spicefunc('spk',
                 title = 'Uranus satellite SPK',
                 known = _URANUS_SPKS,
                 unknown = _rule.pattern,
                 source = _spk_source,
                 sort = _spk_sort_key,
                 exclude = False,
                 reduce = True,
                 default_ids = _default_body_ids,
                 default_ids_key = ('irregular',),
                 propnames = ('irregular',),
                 docstrings = _spk_docstrings)

##########################################################################################
