##########################################################################################
# spyceman/planets/Mars.py: Kernel management for the Mars system
##########################################################################################
"""\
Support for Mars-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

NAME            "MARS".
ALL_MOONS       the set of all IDs for the Martian moons, including aliases.
CLASSICAL       the set of IDs of the "classical" satellites, Phobos and Deimos.
SMALL_INNER     the set of IDs of the small inner moons; same as CLASSICAL.
REGULAR         the set of IDs of the regular satellites; same as CLASSICAL.
IRREGULAR       the set of IDs of the Martian irregular satellites.
UNNAMED         the set of IDs of moons that are not yet officially named.
BODY_ID         the NAIF ID of Mars.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons, including their aliases.
BARYCENTER      the NAIF ID of the Mars system barycenter.
BODY_IDS        dictionary that maps every body name to its body ID.
BODY_NAMES      dictionary that maps every body ID to its name.

FRAME_ID        the NAIF ID of the Mars rotation frame.
FRAME_IDS       dictionary that maps every body name to its frame ID.
FRAME_CENTERS   dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

pck()           function returning a Kernel object derived from one or more Mars-specific
                PCK files.
spk()           function returning a Kernel object derived from one or more Mars SPK
                files.
"""

import warnings

from spyceman.kernelfile  import KernelFile
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman.spicefunc   import spicefunc
from spyceman.rule        import Rule
from spyceman._cspyce     import CSPYCE

##########################################################################################
# Body IDs
##########################################################################################

NAME       = 'MARS'
BODY_ID    = 499
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(401, 403)
for body_id in ALL_MOONS:
    body_name, found = CSPYCE.bodc2n(body_id)
    if found:
        BODY_IDS[body_name] = body_id
        BODY_NAMES[body_id] = body_name
    else:
        warnings.warn('name not identified for body ' + repr(body_id))

# Categorize moons
CLASSICAL   = ALL_MOONS
SMALL_INNER = CLASSICAL
REGULAR     = CLASSICAL
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

from ._MARS_SPKS import _MARS_SPKS

spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

rule = Rule(r'mar(NNN).*\.bsp', source=spk_source, dest='Mars/SPK', planet=NAME,
            family='Mars-SPK')

spk = spicefunc('spk', title='Mars satellite SPK',
                known=_MARS_SPKS,
                unknown=rule.pattern, source=spk_source,
                sort=_spk_sort_key,
                exclude=False, reduce=True,
                default_ids=ALL_IDS)

del spk_source, rule, _spk_sort_key

##########################################################################################
# PCKs
##########################################################################################

from ._MARS_PCKS import _MARS_PCKS

pck_source = (_SOURCE + 'pck', _SOURCE + 'pck/a_old_versions')

rule = Rule(r'mars_iau2000_v(N+).*\.bsp', source=pck_source, dest='Mars/PCK', planet=NAME,
            family='Mars-IAU2000-PCK')
KernelFile.mutual_veto(rule.pattern)        # never more than one furnished

pck = spicefunc('pck', title='Mars PCK',
                known=_MARS_PCKS,
                unknown=rule.pattern, source=pck_source,
                sort='version',
                exclude=True,
                default_ids=ALL_IDS)

del pck_source, rule
del spicefunc, _SOURCE

##########################################################################################
