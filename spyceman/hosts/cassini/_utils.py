##########################################################################################
# spyceman/hosts/Cassini/_utils.py
##########################################################################################
"""Cassini SPICE utilities."""

from spyceman.solarsystem import Saturn

BODY_ID = -82

def _source(ktype):

    _SOURCE1 = 'https://naif.jpl.nasa.gov/pub/naif/CASSINI/kernels/'
    _SOURCE2 = ('https://naif.jpl.nasa.gov/pub/naif/pds/data'
                '/co-s_j_e_v-spice-6-v1.0/cosp_1000/data/')

    ktype = ktype.lower()
    return (_SOURCE1 + ktype, _SOURCE2 + ktype)

_DEFAULT_TIMES = {
    'VENUS'   : ('1998-04-18', '1999-06-25'),
    'EARTH'   : ('1999-08-16', '1999-09-15'),
    'MASURSKY': ('2000-01-23', '2000-01-24'),
    'JUPITER' : ('1999-08-19', '2001-03-24'),
    'SATURN'  : ('2004-01-01', '2017-09-16'),
}

# planet -> set of body IDs
_DEFAULT_BODY_IDS = {
    'VENUS'   : {BODY_ID, 2, 299},
    'EARTH'   : {BODY_ID, 3, 301, 399},
    'MASURSKY': {BODY_ID, 2002685},
    'JUPITER' : {BODY_ID, 5, 599} | set(range(501, 517)),
    'SATURN'  : {BODY_ID} | Saturn.SYSTEM,
}

# (planet, irregular) -> set of body IDs
_DEFAULT_BODY_IDS_W_IRREGULARS = {
    'VENUS'   : {BODY_ID, 2, 299},
    'EARTH'   : {BODY_ID, 3, 301, 399},
    'MASURSKY': {BODY_ID, 2002685},
    'JUPITER' : {BODY_ID, 5, 599} | set(range(501, 517)),
    'SATURN'  : {BODY_ID} | Saturn.SYSTEM,
}
for planet, ids in _DEFAULT_BODY_IDS.items():
    _DEFAULT_BODY_IDS_W_IRREGULARS[planet, False] = ids
    _DEFAULT_BODY_IDS_W_IRREGULARS[planet, True] = ids

_DEFAULT_BODY_IDS_W_IRREGULARS['SATURN', True] |= Saturn.ALL_IDS

del planet, ids

##########################################################################################
