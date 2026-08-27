##########################################################################################
# spyceman/solarsystem/Neptune.py
##########################################################################################
"""Support for Neptune-specific kernels. Last updated 2024-02-01.

Attributes:
    NAME (str): "NEPTUNE".
    ALL_MOONS (set[int]): NAIF IDs for all of Neptune's moons, including aliases.
    CLASSICAL (set[int]): NAIF IDs of the "classical" satellites, Triton and Nereid.
    SMALL_INNER (set[int]): NAIF IDs of the small inner moons.
    REGULAR (set[int]): NAIF IDs of the regular satellites, including Triton.
    IRREGULAR (set[int]): NAIF IDs of the irregular satellites, including Nereid, plus all
        aliases.
    UNNAMED (set[int]): NAIF IDs of moons that are not yet officially named.
    BODY_ID (int): The NAIF ID of Neptune.
    SYSTEM (set[int]): NAIF IDs of the planet and all inner or classical moons.
    ALL_IDS (set[int]): NAIF IDs of the planet and all moons, including their aliases.
    BARYCENTER (int): NAIF ID of the Neptune system barycenter.
    BODY_IDS (dict[str, int]): Mapping from every body name to its body ID.
    BODY_NAMES (dict[int, str]): Mapping from every body ID to its name.
    FRAME_ID (int): The NAIF ID of the Neptune rotation frame.
    FRAME_IDS (dict[str, int]): Mapping from every body name to its frame ID.
    FRAME_CENTERS (dict[int, int]): Mapping from every frame ID to the body ID of its
        center.

Methods:
    spk(): Function returning a Kernel object derived from one or more Neptune SPK files.
"""

import warnings

from spyceman._cspyce     import _CSPYCE
from spyceman._spicefunc  import _spicefunc
from spyceman.rule        import Rule as _Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE_URL

##########################################################################################
# Categorize Neptune's moons and their SPICE IDs
##########################################################################################

NAME       = 'NEPTUNE'
BODY_ID    = 899
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

try:
    _CSPYCE.define_body_aliases(814, 'HIPPOCAMP')
except RuntimeError:
    warnings.warn('Pool overflow at ("HIPPOCAMP", 814)', stacklevel=2)

ALL_MOONS = _srange(801, 815)
for _body_id in ALL_MOONS:
    _body_name, _found = _CSPYCE.bodc2n(_body_id)
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

from ._NEPTUNE_SPKS import _NEPTUNE_SPKS

_spk_source = (_SOURCE_URL + 'spk/satellites',
               _SOURCE_URL + 'spk/satellites/a_old_versions')

_rule = _Rule(r'nep(NNN).*\.bsp', source=_spk_source, dest='Neptune/SPK', planet=NAME,
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
                 default_ids_key = 'irregular',
                 docstrings = _spk_docstrings)

__all__ = ['spk', 'ALL_IDS', 'ALL_MOONS', 'BARYCENTER', 'BODY_ID', 'BODY_IDS',
           'BODY_NAMES', 'CLASSICAL', 'FRAME_CENTERS', 'FRAME_ID', 'FRAME_IDS',
           'IRREGULAR', 'NAME', 'REGULAR', 'SMALL_INNER', 'SYSTEM', 'UNNAMED']

##########################################################################################
