##########################################################################################
# spyceman/solarsystem/Neptune.py
##########################################################################################
"""Support for Neptune-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

* `NAME`: "NEPTUNE".
* `ALL_MOONS`: The set of all IDs for Neptune's moons, including aliases.
* `CLASSICAL`: The set with the IDs of Triton and Nereid.
* `SMALL_INNER`: The set of IDs of the small inner moons.
* `REGULAR`: The set of IDs of the regular satellites, including Triton.
* `IRREGULAR`: The set of IDs of the irregular satellites, including Nereid.
* `UNNAMED`: The set of IDs of moons that are not yet officially named.
* `BODY_ID`: The body ID of Neptune.
* `SYSTEM`: The set of IDs of the planet and all inner or classical moons.
* `ALL_IDS`: The set of IDs of the planet and all moons.
* `BARYCENTER`: The NAIF ID of the Neptune system barycenter.
* `BODY_IDS`: Dictionary that maps every body name to its body ID.
* `BODY_NAMES`: Dictionary that maps every body ID to its name.
* `FRAME_ID`: The NAIF ID of the Neptune rotation frame.
* `FRAME_IDS`: Dictionary that maps every body name to its frame ID.
* `FRAME_CENTERS`: Dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

* `spk()`: Function returning a Kernel object derived from one or more Neptune SPK files.
"""

import warnings

from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman._cspyce     import CSPYCE
from spyceman._spicefunc   import _spicefunc

##########################################################################################
# Categorize Neptune's moons and their SPICE IDs
##########################################################################################

NAME       = 'NEPTUNE'
BODY_ID    = 899
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

try:
    CSPYCE.define_body_aliases(814, 'HIPPOCAMP')
except RuntimeError:
    warnings.warn('Pool overflow at ("HIPPOCAMP", 814)', stacklevel=2)

ALL_MOONS = _srange(801, 815)
for _body_id in ALL_MOONS:
    _body_name, _found = CSPYCE.bodc2n(_body_id)
    if _found:
        BODY_IDS[_body_name] = _body_id
        BODY_NAMES[_body_id] = _body_name
    else:
        warnings.warn(f'name not identified for body {_body_id}', stacklevel=2)

# Categorize moons
CLASSICAL   = {801, 802}                        # includes Nereid
SMALL_INNER = _srange(803, 809) | {814}
IRREGULAR   = {802} | _srange(809, 814)         # also includes Nereid
UNNAMED     = set()
REGULAR     = ALL_MOONS - IRREGULAR

SYSTEM      = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS     = {BODY_ID} | ALL_MOONS

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

from ._NEPTUNE_SPKS import _NEPTUNE_SPKS

_spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

_rule = Rule(r'nep(NNN).*\.bsp', source=_spk_source, dest='Neptune/SPK', planet=NAME,
             family='Neptune-SPK')

_default_body_ids = {False: SYSTEM, True: ALL_IDS}

_spk_docstrings = {'irregular': """\
        irregular (bool, optional): True to include Neptune's irregular satellites in
            the returned Kernel object. Otherwise, unless a list of NAIF IDs is
            explicitly provided, the returned Kernel covers only Neptune's inner
            satellites.
"""}

spk = _spicefunc('spk',
                 title = 'Neptune satellite SPK',
                 known = _NEPTUNE_SPKS,
                 unknown = _rule.pattern,
                 source = _spk_source,
                 sort = _spk_sort_key,
                 exclude = False,
                 reduce = True,
                 default_ids = _default_body_ids,
                 default_ids_key = ('irregular',),
                 docstrings = _spk_docstrings)

##########################################################################################
