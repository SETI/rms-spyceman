##########################################################################################
# spyceman/planets/pluto.py: Kernel management for the Pluto system
#
# Kernel info last updated 3/19/23
##########################################################################################
"""\
spyceman.planets.pluto: Support for Pluto-specific kernels.

The following attributes are defined:

ALL_MOONS       the set of all IDs for Pluto's moons, including aliases.
CLASSICAL       a set with the ID of Charon.
SMALL_INNER     the set of IDs of the small moons.
REGULAR         the set of IDs of the regular satellites.
IRREGULAR       the set of IDs of the irregular satellites.
UNNAMED         the set of IDs of moons that are not yet officially named.
ID              the NAIF ID of Pluto.
SYSTEM          the set of IDs of the planet and all inner or classical moons.
ALL_IDS         the set of IDs of the planet and all moons.
BARYCENTER      the NAIF ID of the Pluto system barycenter.
spk()           a Kernel object derived from one or more Pluto's SPK files.
"""

from spyceman import CSPYCE, KTuple, spicefunc

def srange(*args):
    return set(range(*args))

# Categorize moons
CLASSICAL   = {901}
SMALL_INNER = srange(902, 906)
REGULAR     = srange(901, 905)
ALL_MOONS   = REGULAR
IRREGULAR   = set()
UNNAMED     = set()

ID          = 999
SYSTEM      = {ID} | CLASSICAL | SMALL_INNER
ALL_IDS     = {ID} | ALL_MOONS
BARYCENTER  = 9

##########################################################################################
# Managed list of known PLUnnn SPK kernels
##########################################################################################

SPK_INFO = [

KTuple('plu006-4.bsp',
    '1978-05-31T23:59:10.815', '2024-12-31T23:58:50.816',
    {3, 9, 10, 301, 399, 901, 999},
    '1996-08-28'),
KTuple('plu006-5.bsp',
    '1999-12-31T23:58:55.816', '2049-12-31T23:58:50.816',
    {3, 9, 10, 399, 901, 999},
    '2002-06-18'),
KTuple('plu008_special.bsp',
    '1978-05-31T23:59:10.815', '2024-12-31T23:58:50.816',
    {3, 9, 10, 301, 399, 901, 999},
    '1999-05-14'),
KTuple('plu013.bsp',
    '1965-01-01T00:00:09', '2050-01-03T23:59:55',
    {3, 9, 10, 399, 901, 999},
    '2005-03-24'),
KTuple('plu017xl.bsp',
    '1900-01-01T00:00:09', '2051-01-27T23:59:57',
    {3, 9, 10, 399, 901, 902, 903, 999},
    '2007-08-15'),
KTuple('plu017.bsp',
    '1990-01-01T00:00:00', '2049-12-31T23:59:56',
    {3, 9, 10, 399, 901, 902, 903, 999},
    '2007-06-20'),
KTuple('plu020.bsp',
    '2005-01-01T00:00:00', '2015-12-31T23:59:58',
    {3, 9, 10, 399, 904, 999},
    '2011-07-21'),
KTuple('plu021.bsp',
    '1965-01-04T00:00:09', '2049-12-30T23:59:57',
    {3, 9, 10, 399, 901, 902, 903, 904, 999},
    '2011-08-11'),
KTuple('plu022.bsp',
    '1964-12-07T00:00:09', '2099-12-28T23:59:58',
    {3, 9, 10, 399, 901, 902, 903, 904, 999},
    '2012-07-06'),
KTuple('plu031.bsp',
    '1900-01-01T00:00:09', '2099-12-31T23:59:58',
    {3, 9, 10, 399, 901, 902, 903, 904, 999},
    '2012-10-24'),
KTuple('plu042.bsp',
    '1900-01-02T00:00:09', '2099-12-30T23:59:58',
    {3, 9, 10, 399, 901, 902, 903, 904, 905, 999},
    '2013-07-12'),
KTuple('plu043.bsp',
    '1900-01-07T00:00:09', '2099-12-30T23:59:58',
    {3, 9, 10, 399, 901, 902, 903, 904, 905, 999},
    '2013-12-21'),
KTuple('plu055.1600-2600.bsp',
    '1599-12-27T23:59:27.816', '2600-01-03T23:58:50.816',
    {901, 902, 903, 904, 905, 999},
    '2016-06-30'),
KTuple('plu055.bsp',
    '1900-01-08T00:00:09', '2099-12-31T23:59:59',
    {3, 9, 10, 399, 901, 902, 903, 904, 905, 999},
    '2015-11-05'),
KTuple('plu058.bsp',
    '1900-01-01T23:59:27.816', '2099-12-27T23:58:50.816',
    {3, 9, 10, 399, 901, 902, 903, 904, 905, 999},
    '2021-06-04'),
]

spk = make_func('spk', pattern=r'plu(\d\d\d).*\.bsp', fnmatch='plu*.bsp',
                       info=SPK_INFO, extras=[], exclusive=False, bodies=ALL_MOONS | {ID})

##########################################################################################
