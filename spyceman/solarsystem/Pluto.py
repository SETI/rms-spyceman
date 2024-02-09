##########################################################################################
# spyceman/planets/Pluto.py: Kernel management for the Pluto system
##########################################################################################
"""\
Support for Pluto-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

NAME            "PLUTO".
ALL_MOONS       the set of all IDs for Pluto's moons, including aliases.
CLASSICAL       a set with the ID of Charon.
SMALL_INNER     the set of IDs of the small moons.
REGULAR         the set of IDs of the regular satellites, Charon plus the SMALL_INNER.
IRREGULAR       the set of IDs of the irregular satellites.
UNNAMED         the set of IDs of moons that are not yet officially named.
BODY_ID         the body ID of Pluto.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons.
BARYCENTER      the NAIF ID of the Pluto system barycenter.
BODY_IDS        dictionary that maps every body name to its body ID.
BODY_NAMES      dictionary that maps every body ID to its name.

FRAME_ID        the NAIF ID of the Neptune rotation frame.
FRAME_IDS       dictionary that maps every body name to its frame ID.
FRAME_CENTERS   dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

spk()           a Kernel object derived from one or more of Pluto's SPK files.
"""

import warnings

from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman.spicefunc   import spicefunc
from spyceman._cspyce     import CSPYCE

##########################################################################################
# Body IDs
##########################################################################################

NAME       = 'PLUTO'
BODY_ID    = 999
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(901, 906)
for body_id in ALL_MOONS:
    body_name, found = CSPYCE.bodc2n(body_id)
    if found:
        BODY_IDS[body_name] = body_id
        BODY_NAMES[body_id] = body_name
    else:
        warnings.warn('name not identified for body ' + repr(body_id))

# Categorize moons
CLASSICAL   = {901}
SMALL_INNER = _srange(902, 906)
REGULAR     = ALL_MOONS
IRREGULAR   = set()
UNNAMED     = set()

SYSTEM  = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS = {BODY_ID} | ALL_MOONS

del _srange, body_id, body_name, found

##########################################################################################
# Frame IDs
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

from ._PLUTO_SPKS import _PLUTO_SPKS

spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

rule = Rule(r'plu(NNN).*\.bsp', source=spk_source, dest='Pluto/SPK', planet=NAME,
            family='Pluto-SPK')

spk = spicefunc('spk', title='Pluto satellite SPK',
                known=_PLUTO_SPKS,
                unknown=rule.pattern, source=spk_source,
                sort=_spk_sort_key,
                exclude=False, reduce=True,
                default_ids=ALL_IDS)

del spk_source, rule
del spicefunc, _SOURCE, _spk_sort_key

##########################################################################################
