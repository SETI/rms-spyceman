##########################################################################################
# spyceman/solarsystem/Pluto.py
##########################################################################################
"""Support for Pluto-specific kernels. Last updated 2024-02-01.

Attributes:
    NAME (str): "PLUTO".
    ALL_MOONS (set[int]): NAIF IDs for Pluto's moons, including aliases.
    CLASSICAL (set[int]): NAIF IDs of the "classical" satellite, Charon.
    SMALL_INNER (set[int]): NAIF IDs of the small moons.
    REGULAR (set[int]): NAIF IDs of the regular satellites, Charon plus SMALL_INNER.
    IRREGULAR (set[int]): NAIF IDs of any irregular satellites, including their aliases.
    UNNAMED (set[int]): NAIF IDs of any moons that are not yet officially named.
    BODY_ID (int): The NAIF ID of Pluto.
    SYSTEM (set[int]): NAIF IDs of the planet and all inner or classical moons.
    ALL_IDS (set[int]): NAIF IDs of the planet and all moons, including their aliases.
    BARYCENTER (int): NAIF ID of the Pluto system barycenter.
    BODY_IDS (dict[str, int]): Mapping from every body name to its body ID.
    BODY_NAMES (dict[int, str]): Mapping from every body ID to its name.
    FRAME_ID (int): The NAIF ID of the Pluto rotation frame.
    FRAME_IDS (dict[str, int]): Mapping from every body name to its frame ID.
    FRAME_CENTERS (dict[int, int]): Mapping from every frame ID to the body ID of its
        center.

Methods:
    spk(): Function returning a Kernel object derived from one or more Pluto SPK files.
"""

import warnings

from spyceman._cspyce     import _CSPYCE
from spyceman._spicefunc  import _spicefunc
from spyceman.rule        import Rule as _Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE_URL

##########################################################################################
# Body IDs
##########################################################################################

NAME       = 'PLUTO'
BODY_ID    = 999
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(901, 906)
for _body_id in ALL_MOONS:
    _body_name, _found = _CSPYCE.bodc2n(_body_id)
    if _found:
        BODY_IDS[_body_name] = _body_id
        BODY_NAMES[_body_id] = _body_name
    else:
        warnings.warn(f'name not identified for body {_body_id}', stacklevel=2)

# Categorize moons
CLASSICAL   = {901}
SMALL_INNER = _srange(902, 906)
REGULAR     = ALL_MOONS
IRREGULAR   = set()
UNNAMED     = set()

SYSTEM  = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS = {BODY_ID} | ALL_MOONS

##########################################################################################
# Frame IDs
##########################################################################################

FRAME_ID, _frame_name, _found = _CSPYCE.cidfrm(NAME)
FRAME_IDS = {NAME: FRAME_ID}
FRAME_CENTERS = {FRAME_ID: BODY_ID}
for _body_name, _body_id in BODY_IDS.items():
    _frame_id, _frame_name, _found = _CSPYCE.cidfrm(_body_id)
    if not _found:
        _frame_id = _body_id    # if not already defined, use the body ID as the frame ID

    FRAME_IDS[_body_name] = _frame_id
    FRAME_CENTERS[_frame_id] = _body_id

##########################################################################################
# SPKs
##########################################################################################

from ._PLUTO_SPKS import _PLUTO_SPKS

_spk_source = (_SOURCE_URL + 'spk/satellites',
               _SOURCE_URL + 'spk/satellites/a_old_versions')

_rule = _Rule(r'plu(NNN).*\.bsp', source=_spk_source, dest='Pluto/SPK', planet=NAME,
              family='Pluto-SPK')

spk = _spicefunc('spk',
                 title = 'Pluto satellite SPK',
                 known = _PLUTO_SPKS,
                 unknown = _rule.pattern,
                 source = _spk_source,
                 sort = _spk_sort_key,
                 exclude = False,
                 reduce = True,
                 default_ids = ALL_IDS)

__all__ = ['spk', 'ALL_IDS', 'ALL_MOONS', 'BARYCENTER', 'BODY_ID', 'BODY_IDS',
           'BODY_NAMES', 'CLASSICAL', 'FRAME_CENTERS', 'FRAME_ID', 'FRAME_IDS',
           'IRREGULAR', 'NAME', 'REGULAR', 'SMALL_INNER', 'SYSTEM', 'UNNAMED']

##########################################################################################
