##########################################################################################
# spyceman/planets/mars.py: Kernel management for the Mars system
#
# Kernel info last updated 3/19/23
##########################################################################################
"""\
spyceman.planets.mars: Support for Mars-specific kernels.

The following attributes are defined:

ALL_MOONS       the set of all IDs for Mars's moons, including aliases.
CLASSICAL       a set with the IDs of Phobos and Deimos.
SMALL_INNER     the set of IDs of the small moons, same as CLASSICAL.
REGULAR         the set of IDs of the regular satellites, same as CLASSICAL.
IRREGULAR       the set of IDs of the irregular satellites, currently empty.
UNNAMED         the set of IDs of moons that are not yet officially named.
ID              the NAIF ID of Mars.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons.
BARYCENTER      the NAIF ID of the Mars system barycenter.
spk()           a Kernel object derived from one or more Mars SPK files.
pck()           a Kernel object derived from one or more Mars PCK files
"""

from spyceman import CSPYCE, KTuple, spicefunc

# Categorize moons
CLASSICAL   = {401, 402}
SMALL_INNER = CLASSICAL
REGULAR     = CLASSICAL
IRREGULAR   = set()
ALL_MOONS   = CLASSICAL
UNNAMED     = set()

ID          = 499
SYSTEM      = {ID} | CLASSICAL
ALL_IDS     = {ID} | ALL_MOONS
BARYCENTER  = 4

##########################################################################################
# Managed list of known MARnnn SPK kernels
##########################################################################################

SPK_INFO = [

KTuple('mar022-1.bsp',
    '1971-09-30T23:59:27.818', '1972-09-30T23:59:16.818',
    {3, 4, 10, 399, 401, 402, 499},
    '1999-09-05'),
KTuple('mar022-LONG.bsp',
    '1976-05-31T23:59:12.815', '2026-01-01T23:58:50.816',
    {3, 4, 10, 301, 399, 401, 402, 499},
    '1995-08-29'),      # was 1989-03-02
KTuple('mar033-7.bsp',
    '1976-06-01T00:00:00', '2025-01-11T23:57:54',
    {3, 4, 10, 399, 401, 402, 499},
    '1997-06-19'),
KTuple('mar063.bsp',
    '1962-12-03T00:00:09', '2050-01-02T23:59:56',
    {3, 4, 10, 399, 401, 402, 499},
    '2007-08-14'),
KTuple('mar080.bsp',
    '1900-01-04T00:00:09', '2051-01-01T23:59:57',
    {3, 4, 10, 399, 401, 402, 499},
    '2008-04-01'),
KTuple('mar085.bsp',
    '1900-01-04T00:00:09', '2051-01-01T23:59:57',
    {3, 4, 10, 399, 401, 402, 499},
    '2008-04-01'),
KTuple('mar097.1600-1900.bsp',
    '1599-12-31T23:59:27.816', '1900-01-07T23:59:27.816',
    {401, 402, 499},
    '2016-06-29'),
KTuple('mar097.1900-2100.bsp',
    '1900-01-03T23:59:27.816', '2100-01-02T23:58:50.816',
    {401, 402, 499},
    '2016-06-29'),
KTuple('mar097.2100-2600.bsp',
    '2099-12-31T23:58:50.816', '2600-01-03T23:58:50.816',
    {401, 402, 499},
    '2016-06-29'),
KTuple('mar097.bsp',
    '1900-01-04T00:00:09', '2099-12-31T23:59:58',
    {3, 4, 10, 399, 401, 402, 499},
    '2011-05-24'),
]

spk = make_func('spk', pattern=r'mar(\d\d\d).*\.bsp', fnmatch='mar*.bsp',
                info=SPK_INFO, extras=[], bodies=ALL_MOONS | {ID}, exclusive=False)

##########################################################################################
# Managed list of known Mars PCK kernels
##########################################################################################

PCK_INFO = [

KTuple('mars_iau2000_v0.tpc',
    None, None,
    {4, 401, 402, 499},
    '2001-12-11'),
KTuple('mars_iau2000_v1.tpc',
    None, None,
    {4, 401, 402, 499},
    '2023-01-18'),
]

# According to comments in mars_iau2000_v1.tpc, both pck00011.tpc and
# pck00011_n0066.tpc are incompatible with mars_iau2000_v0.tpc. In other
# regards, the v0 and v1 files are functionally identical.

# This prevents the incompatibility from ever arising. However, note that the
# unloading of pck00011 might be an unexpected side-effect of loading _v0.
# Still, it is for the user's own protection.
KernelFile.globally_exclude(r'pck00011.*\.tpc', 'mars_iau2000_v0.tpc')

pck = make_func('pck', pattern=r'mars_iau2000_v(\d)\.tpc', fnmatch='mars_iau2000_v*.tpc',
                       info=PCK_INFO, extras=[], exclusive=True, bodies=ALL_MOONS | {ID})

##########################################################################################
