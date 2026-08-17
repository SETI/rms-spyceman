##########################################################################################
# spyceman/solarsystem/Mars.py
##########################################################################################
"""Support for Mars-specific kernels. Last updated 2024-02-01.

The following attributes are defined:

* `NAME`: "MARS".
* `ALL_MOONS`: The set of all IDs for the Martian moons, including aliases.
* `CLASSICAL`: The set of IDs of the "classical" satellites, Phobos and Deimos.
* `SMALL_INNER`: The set of IDs of the small inner moons; same as CLASSICAL.
* `REGULAR`: The set of IDs of the regular satellites; same as CLASSICAL.
* `IRREGULAR`: The set of IDs of the Martian irregular satellites.
* `UNNAMED`: The set of IDs of moons that are not yet officially named.
* `BODY_ID`: The NAIF ID of Mars.
* `SYSTEM`: The set of IDs of the planet and all inner or classical moons.
* `ALL_IDS`: The set of IDs of the planet and all moons, including their aliases.
* `BARYCENTER`: The NAIF ID of the Mars system barycenter.
* `BODY_IDS`: Dictionary that maps every body name to its body ID.
* `BODY_NAMES`: Dictionary that maps every body ID to its name.
* `FRAME_ID`: The NAIF ID of the Mars rotation frame.
* `FRAME_IDS`: Dictionary that maps every body name to its frame ID.
* `FRAME_CENTERS`: Dictionary that maps every frame ID to the body ID of its center.

The following functions are defined:

* `pck()`: Function returning a Kernel object derived from one or more Mars-specific PCK
  PCK files.
* `spk()`: Function returning a Kernel object derived from one or more Mars SPK files.
"""

import warnings

from spyceman.kernelfile  import KernelFile
from spyceman.solarsystem import _spk_sort_key, _srange, _SOURCE
from spyceman.rule        import Rule
from spyceman._cspyce     import CSPYCE
from spyceman._spicefunc  import _spicefunc

##########################################################################################
# Body IDs
##########################################################################################

NAME       = 'MARS'
BODY_ID    = 499
BARYCENTER = BODY_ID // 100
BODY_IDS   = {NAME: BODY_ID, 'BARYCENTER': BARYCENTER, NAME + ' BARYCENTER': BARYCENTER}
BODY_NAMES = {BODY_ID: NAME, BARYCENTER: NAME + ' BARYCENTER'}

ALL_MOONS = _srange(401, 403)
for _body_id in ALL_MOONS:
    _body_name, _found = CSPYCE.bodc2n(_body_id)
    if _found:
        BODY_IDS[_body_name] = _body_id
        BODY_NAMES[_body_id] = _body_name
    else:
        warnings.warn(f'name not identified for body {_body_id}')

# Categorize moons
CLASSICAL   = ALL_MOONS
SMALL_INNER = CLASSICAL
REGULAR     = CLASSICAL
IRREGULAR   = set()
UNNAMED     = set()

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

from ._MARS_SPKS import _MARS_SPKS

_spk_source = (_SOURCE + 'spk/satellites', _SOURCE + 'spk/satellites/a_old_versions')

_rule = Rule(r'mar(NNN).*\.bsp', source=_spk_source, dest='Mars/SPK', planet=NAME,
             family='Mars-SPK')

spk = _spicefunc('spk',
                title = 'Mars satellite SPK',
                known = _MARS_SPKS,
                unknown = _rule.pattern,
                source = _spk_source,
                sort = _spk_sort_key,
                exclude = False,
                reduce = True,
                default_ids = ALL_IDS)

##########################################################################################
# PCKs
##########################################################################################

from ._MARS_PCKS import _MARS_PCKS

_pck_source = (_SOURCE + 'pck', _SOURCE + 'pck/a_old_versions')

_rule = Rule(r'mars_iau2000_v(N+).*\.bsp', source=_pck_source, dest='Mars/PCK',
             planet=NAME, family='Mars-IAU2000-PCK')
KernelFile.mutual_veto(_rule.pattern)       # never more than one furnished

pck = _spicefunc('pck',
                 title = 'Mars PCK',
                 known = _MARS_PCKS,
                 unknown = _rule.pattern,
                 source = _pck_source,
                 sort = 'version',
                 exclude = True,
                 default_ids = ALL_IDS)

##########################################################################################
