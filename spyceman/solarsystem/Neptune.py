##########################################################################################
# spyceman/planets/Neptune.py: Kernel management for the Neptune system
##########################################################################################
"""\
Support for Neptune-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

NAME            "NEPTUNE".
ALL_MOONS       the set of all IDs for Neptune's moons, including aliases.
CLASSICAL       a set with the IDs of Triton and Nereid.
SMALL_INNER     the set of IDs of the small inner moons.
REGULAR         the set of IDs of the regular satellites, including Triton.
IRREGULAR       the set of IDs of the irregular satellites, including Nereid.
UNNAMED         the set of IDs of moons that are not yet officially named.
BODY_ID         the body ID of Neptune.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons.
BARYCENTER      the NAIF ID of the Neptune system barycenter.
BODY_IDS        dictionary that maps every body name to its body ID.
BODY_NAMES      dictionary that maps every body ID to its name.

FRAME_ID        the NAIF ID of the Neptune rotation frame.
FRAME_IDS       dictionary that maps every body name to its frame ID.
FRAME_CENTERS   dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

spk()           a Kernel object derived from one or more Neptune SPK files.
"""

import warnings

from spyceman.rule        import Rule
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman.spicefunc   import spicefunc
from spyceman._cspyce     import CSPYCE

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
    warnings.warn('Pool overflow at ("HIPPOCAMP", 814)')

ALL_MOONS = _srange(801, 815)
for body_id in ALL_MOONS:
    body_name, found = CSPYCE.bodc2n(body_id)
    if found:
        BODY_IDS[body_name] = body_id
        BODY_NAMES[body_id] = body_name
    else:
        warnings.warn('name not identified for body ' + repr(body_id))

# Categorize moons
CLASSICAL   = {801, 802}                        # includes Nereid
SMALL_INNER = _srange(803, 809) | {814}
IRREGULAR   = {802} | _srange(809, 814)         # also includes Nereid
UNNAMED     = set()
REGULAR     = ALL_MOONS - IRREGULAR

SYSTEM      = {BODY_ID} | CLASSICAL | SMALL_INNER
ALL_IDS     = {BODY_ID} | ALL_MOONS

del _srange, body_id, body_name, found

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

from ._NEPTUNE_SPKS import _NEPTUNE_SPKS

spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

rule = Rule(r'nep(NNN).*\.bsp', source=spk_source, dest='Neptune/SPK', planet=NAME,
            family='Neptune-SPK')

default_body_ids = {False: SYSTEM, True: ALL_IDS}

spk_docstrings = {'irregular': """\
        irregular   True to include Neptune's irregular satellites in the returned Kernel
                    object. Otherwise, unless a list of NAIF IDs is explicitly provided,
                    the returned Kernel will only cover Neptune's inner satellites.
"""}

spk = spicefunc('spk', title='Neptune satellite SPK',
                known=_NEPTUNE_SPKS,
                unknown=rule.pattern, source=spk_source,
                sort=_spk_sort_key,
                exclude=False, reduce=True,
                default_ids=default_body_ids, default_ids_key=('irregular',),
                docstrings=spk_docstrings)

del spk_source, rule, default_body_ids, spk_docstrings
del spicefunc, _SOURCE, _spk_sort_key

##########################################################################################
