##########################################################################################
# spyceman/hosts/Voyager/__init__.py
##########################################################################################
"""\
Support for Voyager-specific SPICE kernels.

To use:
    from spyceman.hosts import Voyager

The following attributes are defined:

VG1, VG2                the body IDs of Voyager 1 and Voyager 2.
VG1_ISSNA, ...          the frame IDs of all the Voyager instruments.
BODY_IDS                a dictionary such that BODY_IDS[1] is VG1; BODY_IDS[2] is VG2.
FRAME_IDS               a dictionary such that FRAME_IDS["VG1_ISSNA"] is VG1_ISSNA, etc.
                        Also, FRAME_IDS[1, "ISSNA"] is VG1_ISSNA.
INSTRUMENT_NAMES        the set of instrument names.
BUS_INSTRUMENT_NAMES    the set of instrument names attached to the bus.
SCAN_PLATFORM_INSTRUMENT_NAMES
                        the set of instrument names attached to the scan platform

The following functions are defined:

ck()        function returning a C (pointing) kernel.
fk()        function returning a frames kernel.
ik()        function returning an instrument kernel.
sclk()      function returning a spacecraft clock kernel.
spk()       function returning a SP (trajectory) kernel.
meta()      function returning a Metakernel containing all of the above.
"""

import numbers

from spyceman._cspyce     import CSPYCE
from spyceman._utils      import validate_time as _validate_time
from spyceman._utils      import validate_naif_ids as _validate_naif_ids
from spyceman.kernelfile  import KernelFile, KTuple
from spyceman.kernelset   import KernelSet
from spyceman.metakernel  import Metakernel
from spyceman.rule        import Rule
from spyceman.solarsystem import Jupiter, Saturn, Uranus, Neptune
from spyceman.spicefunc   import spicefunc, _input_set, _intersect_basenames

_MODULES = {
    'jup': Jupiter,
    'sat': Saturn,
    'ura': Uranus,
    'nep': Neptune,
}

_PLANET_NAMES = {
    'jup': 'JUPITER',
    'sat': 'SATURN',
    'ura': 'URANUS',
    'nep': 'NEPTUNE',
}

def _source(ktype):
    return 'https://naif.jpl.nasa.gov/pub/naif/VOYAGER/kernels/' + ktype.lower()

##########################################################################################
# Public body and frame definitions
##########################################################################################

NAME = 'VOYAGER'
BODY_IDS = {1: -31, 2: -32}
VG1 = BODY_IDS[1]
VG2 = BODY_IDS[2]

FRAME_IDS = {
    'VG1_SC_BUS'       : -31000,
    'VG1_SCAN_PLATFORM': -31100,
    'VG1_HGA'          : -31400,
    'VG1_ISSNA'        : -31101,
    'VG1_ISSWA'        : -31102,
    'VG1_PPS'          : -31103,
    'VG1_UVS'          : -31104,
    'VG1_UVSOCC'       : -31105,
    'VG1_IRIS'         : -31106,
    'VG1_IRISOCC'      : -31107,
    'VG2_SC_BUS'       : -32000,
    'VG2_SCAN_PLATFORM': -32100,
    'VG2_HGA'          : -32400,
    'VG2_ISSNA'        : -32101,
    'VG2_ISSWA'        : -32102,
    'VG2_PPS'          : -32103,
    'VG2_UVS'          : -32104,
    'VG2_UVSOCC'       : -32105,
    'VG2_IRIS'         : -32106,
    'VG2_IRISOCC'      : -32107,
}

# Alternative names
FRAME_IDS['VG1_BUS'] = FRAME_IDS['VG1_SC_BUS']
FRAME_IDS['VG2_BUS'] = FRAME_IDS['VG1_SC_BUS']

# Turn these into globals
for key, value in FRAME_IDS.items():
    locals()[key] = value

# Alternative dictionary keys FRAME_IDS[1, "ISSNA"], etc.
keys = list(FRAME_IDS.keys())
for key in keys:
    FRAME_IDS[int(key[2]), key[4:]] = FRAME_IDS[key]

# Sets of instrument names
INSTRUMENT_NAMES = {key[1] for key in FRAME_IDS if isinstance(key, tuple)}
BUS_INSTRUMENT_NAMES = {'SC_BUS', 'BUS', 'HGA'}
SCAN_PLATFORM_INSTRUMENT_NAMES = INSTRUMENT_NAMES - BUS_INSTRUMENT_NAMES

del key, keys, value

##########################################################################################
# Internal date dictionary _DATE_RANGES[voyager, planet] -> range of flyby dates
##########################################################################################

_DEFAULT_TIMES = {    # (voyager, planet) -> time limits
    (1, 'JUPITER'): ('1979-01-04T23:55:45', '1979-04-13T23:56:44'),
    (2, 'JUPITER'): ('1979-04-25T00:26:27', '1979-08-29T00:00:00'),
    (1, 'SATURN' ): ('1980-08-06T23:59:09', '1981-01-01T00:00:00'),
    (2, 'SATURN' ): ('1981-06-01T00:00:00', '1981-10-21T23:59:00'),
    (2, 'URANUS' ): ('1985-08-21T23:59:05', '1986-02-25T13:42:00'),
    (2, 'NEPTUNE'): ('1989-04-03T16:24:35', '1989-10-03T00:00:00'),
}

# Convert times to TDB
_DEFAULT_TIMES = {k:(_validate_time(v[0]),
                     _validate_time(v[1])) for k, v in _DEFAULT_TIMES.items()}

##########################################################################################
# _DEFAULT_BODY_IDS[voyager, planet] -> set of body IDs
##########################################################################################

_DEFAULT_BODY_IDS = {}      # [voyager, planet, irregular] -> set of body IDs
for key, module in _MODULES.items():
    for irregular, ids in [(False, module.SYSTEM), (True, module.ALL_IDS)]:
        _DEFAULT_BODY_IDS[2, _PLANET_NAMES[key], irregular] = ids | {VG2}
        if key in ('ura', 'nep'):
            continue
        _DEFAULT_BODY_IDS[1, _PLANET_NAMES[key], irregular] = ids | {VG1}

del key, module, irregular, ids

##########################################################################################
# _DEFAULT_FRAME_IDS[voyager, instrument] -> set of frame IDs
##########################################################################################

# (voyager, instrument) -> set of all connected frame IDs
_DEFAULT_FRAME_IDS = {}
_FRAME_IDS_BY_VOYAGER = {}
for vgr in (1, 2):
    bus_ids = {i for k,i in FRAME_IDS.items()
               if isinstance(k, tuple) and k[0] == vgr and k[1] in BUS_INSTRUMENT_NAMES}

    scan_platform_ids = {i for k,i in FRAME_IDS.items()
                         if isinstance(k, tuple) and k[0] == vgr
                            and k[1] in SCAN_PLATFORM_INSTRUMENT_NAMES}

    for name in BUS_INSTRUMENT_NAMES:
        _DEFAULT_FRAME_IDS[vgr, name] = bus_ids
    for name in SCAN_PLATFORM_INSTRUMENT_NAMES:
        _DEFAULT_FRAME_IDS[vgr, name] = scan_platform_ids

    # Also allow instrument name "ISS"
    _DEFAULT_FRAME_IDS[vgr, 'ISS'] = scan_platform_ids

    _FRAME_IDS_BY_VOYAGER[vgr] = bus_ids | scan_platform_ids

del vgr, bus_ids, scan_platform_ids, name

##########################################################################################
# Define key properties
##########################################################################################

# Define mission and planet as common properties of all kernels
Rule(r'vgr?(?P<voyager>[12]).*', voyager=int, mission='VOYAGER')
Rule(r'vg.*(?P<planet>jup|sat|ura|nep).*', planet=_PLANET_NAMES)

_DOCSTRINGS = {}
_DOCSTRINGS['voyager'] = """\
        voyager     1 or 2 to select one of the two Voyager spacecraft; None to include
                    both.
"""
_DOCSTRINGS['planet'] = """\
        planet      use "JUPITER", "SATURN", "URANUS", or "NEPTUNE" to select a specific
                    planetary flyby; enclose multiple values in a tuple; None for all
                    flybys.
"""

#### Used by ck()

_DOCSTRINGS['origin'] = """\
        origin      use "QMW" for the Queen Mary College CK; "SEDR" for the SEDR-based CK;
                    None for any.
"""
_DOCSTRINGS['ctype'] = """\
        ctype       the type of the C kernel, e.g., 1 or 3.
"""

#### Used by ck() and ik()

_DOCSTRINGS['instrument'] = """\
        instrument  return results for one or more instruments/frames: "BUS", "HGA",
                    "IRIS", "IRISOCC", "ISSNA", "ISSWA", "PPS", "UVS", "UVSOCC", or
                    "SCAN_PLATFORM". Enclose multiple values inside a set or tuple. Use
                    None for all instruments. "ISS" is equivalent to {"ISSNA", "ISSWA"}.
"""

#### Used by spk()

_DOCSTRINGS['irregular'] = """\
        irregular   True to include the planet's irregular satellites in the returned
                    Kernel object.
"""

##########################################################################################
# Utilities
##########################################################################################

def _voyager_pattern(voyager):
    """Convert the voyager input to a match pattern."""

    if not voyager:
        return '[12]'
    elif isinstance(voyager, numbers.Integral):
        return str(voyager)
    else:
        return '[' + ''.join([str(v) for v in voyager]) + ']'

def _planet_pattern(planet):
    """Convert the planet input to a match pattern."""

    if not planet:
        planet = ['JUPITER', 'SATURN', 'URANUS', 'NEPTUNE']

    if isinstance(planet, str):
        return planet[:3].lower()

    return '(' + '|'.join([planet[:3].lower() for p in planet]) + ')'

##########################################################################################
# CKs
##########################################################################################

from ._VOYAGER_QMW_CKS  import _VOYAGER_QMW_CKS
from ._VOYAGER_SEDR_CKS import _VOYAGER_SEDR_CKS
from ._VOYAGER_BUS_CKS  import _VOYAGER_BUS_CKS

# QMW CKs

# Call the QMW CKs version 0 because the SEDR CKs already have version numbers 1 and 2
Rule(r'vg[12]_(?P<family>jup|sat|ura|nep)_qmw_(?P<_camera>[nw]a)\.bc',
     family='Voyager-QMW-CK', version=0,
     source=_source('CK'), dest='Voyager/CK',
     ctype=1, origin='QMW', instrument='SCAN_PLATFORM', _camera=str.upper)
    # The "_camera" property is used internally to prevent QMW NA and WA CKs for the same
    # flyby from being treated as mutually exclusive.

Rule(r'vg1_(jup|sat|ura|nep)_qmw_([nw]a)\.bc',
     naif_ids=_FRAME_IDS_BY_VOYAGER[1, 'SCAN_PLATFORM'])
Rule(r'vg2_(jup|sat|ura|nep)_qmw_([nw]a)\.bc',
     naif_ids=_FRAME_IDS_BY_VOYAGER[2, 'SCAN_PLATFORM'])

# Note that the QMW kernels do not use the correct frame IDs for ISSNA and ISSWA.
CSPYCE.define_frame_aliases('VG1_ISSNA', FRAME_IDS['VG1_ISSNA'], -31001)
CSPYCE.define_frame_aliases('VG1_ISSWA', FRAME_IDS['VG1_ISSWA'], -31002)
CSPYCE.define_frame_aliases('VG2_ISSNA', FRAME_IDS['VG2_ISSNA'], -32001)
CSPYCE.define_frame_aliases('VG2_ISSWA', FRAME_IDS['VG2_ISSWA'], -32002)

# SEDR CKs

Rule(r'vg([12])_(jup|sat|ura|nep)_version(N)_type(?P<ctype>[13])_'
     r'(iss|uvs|pps|iris)_sedr\.bc',
     family='Voyager-SEDR-CK', source='https://pds-rings.seti.org/voyager/ck/',
     dest='Voyager/CK',
     ctype=int, origin='SEDR', instrument='SCAN_PLATFORM', _camera={'NA','WA'})
    # This "_camera" property holds both "NA" and "WA", so it will always be exclusive of
    # QMW kernels for a given flyby.

Rule(r'vg1_(jup|sat|ura|nep)_version\d_type\d_.*_sedr\.bc',
     naif_ids=_FRAME_IDS_BY_VOYAGER[1, 'SCAN_PLATFORM'])
Rule(r'vg2_(jup|sat|ura|nep)_version\d_type\d_.*_sedr\.bc',
     naif_ids=_FRAME_IDS_BY_VOYAGER[2, 'SCAN_PLATFORM'])

# BUS CKs

Rule(r'vgr?([12])_super.*\.bc', family='Voyager-BUS-CK',
     source=_source('CK'), dest='Voyager/CK',
     ctype=3, origin='SEDR', instrument=BUS_INSTRUMENT_NAMES, _camera='NEITHER')
    # Because the _camera property is "NEITHER", it will not be exclusive of any scan
    # platform kernel.

Rule(r'vgr?1_super.*\.bc', naif_ids=_FRAME_IDS_BY_VOYAGER[1, 'BUS'])
Rule(r'vgr?2_super.*\.bc', naif_ids=_FRAME_IDS_BY_VOYAGER[2, 'BUS'])

# This is an ad hoc version numbering system for the bus CKs.
KernelFile('vgr1_super_old.bc').version=1
KernelFile('vgr2_super_old.bc').version=1
KernelFile('vgr1_super.bc').version=2
KernelFile('vgr2_super.bc').version=2
KernelFile.veto(r'vgr?([12])_super.*\.bc', r'vgr?\1_super.*\.bc')

# This assigns version=3 to any future "vgr?_super" file where the suffix is not "old"
Rule(r'vgr?([12])_super_(?!old).+\.bc', version=3)

# We need to ensure that a CK request for the frame ID of a particular instrument returns
# the CK for the associated component, which would be either the scan platform or the bus.
# To make that work, we remove the naif_ids attribute of each KTuple so that the naif_ids
# defined in the rules above will take precedence.
scan_platform_cks = []
for ck_ in _VOYAGER_QMW_CKS + _VOYAGER_SEDR_CKS:
    scan_platform_cks.append(KTuple(*ck_[:3], set(), ck_[-1]))

bus_cks = []
for ck_ in _VOYAGER_BUS_CKS:
    bus_cks.append(KTuple(*ck_[:3], set(), ck_[-1]))

ck_pattern = r'vgr?[12]_.*\.bc'

ck_notes = """\
    This function generates a C (pointing) Kernel object for one or more Voyager
    instruments.

    The only version available is 2, released 2000-11-27.
"""

ck = spicefunc('ck', title='Voyager CK',
               known=scan_platform_cks + bus_cks,
               unknown=ck_pattern, source=_source('CK'),
               exclude=('voyager', 'planet', '_camera'), reduce=False,
               default_times=_DEFAULT_TIMES, default_times_key=('voyager', 'planet'),
               default_ids=_DEFAULT_FRAME_IDS, default_ids_key=('voyager', 'instrument'),
               notes=ck_notes,
               propnames=('voyager', 'planet', 'origin', 'ctype', 'instrument'),
               docstrings=_DOCSTRINGS)

del ck_, ck_pattern, scan_platform_cks, bus_cks

##########################################################################################
# FKs
##########################################################################################

from ._VOYAGER_FKS import _VOYAGER_FKS

rule = Rule(r'vgr?([12])_v(NN).*\.tf', family='Voyager-FK',
     source=_source('FK'), dest='Voyager/FK')
KernelFile.veto(r'vgr?([12]).*\.tf', r'vgr?\1.*\.tf')

fk_notes = """\
    This function generates a Frames Kernel object for the Voyager instruments.

    The only available version is 2, released 2000-11-27.
"""

fk = spicefunc('fk', title='Voyager FK',
               known=_VOYAGER_FKS,
               unknown=rule.pattern, source=_source('FK'),
               exclude=('voyager',),
               default_ids=_FRAME_IDS_BY_VOYAGER, default_ids_key=('voyager',),
               notes=fk_notes,
               propnames=('voyager',), docstrings=_DOCSTRINGS)

del rule, fk_notes

##########################################################################################
# IKs
##########################################################################################

from ._VOYAGER_IKS import _VOYAGER_IKS

rule = Rule(r'vgr?[12].*\.ti', source=_source('IK'), dest='Voyager/IK',
            family='Voyager-IK')
Rule(r'vgr?[12]_issna_v(NN)\.ti', instrument={'ISSNA', 'ISS'})
Rule(r'vgr?[12]_isswa_v(NN)\.ti', instrument={'ISSWA', 'ISS'})
Rule(r'vgr?[12]_(?!iss)(?P<instrument>[a-z]+)_v(NN)\.ti', instrument=str.upper)
KernelFile.veto(r'vgr?([12])_([a-z]+)_.*\.ti', r'vgr?\1_\2.*\.ti')

ik_notes = """\
    This function generates an Instrument Kernel object for one or more of the Voyager
    instruments.

    The highest version is 2 for the narrow angle cameras (instrument "ISSNA") and 1 for
    the wide angle cameras (instrument "ISSWA"). These were released on 2000-11-27. No
    other instrument kernels have been released by NAIF.
"""

ik = spicefunc('ik', title='Voyager IK',
               known=_VOYAGER_IKS,
               unknown=rule.pattern, source=_source('IK'),
               exclude=('voyager', 'instrument'),
               notes=ik_notes,
               propnames=('voyager', 'instrument'), docstrings=_DOCSTRINGS)

del rule, ik_notes

##########################################################################################
# SCLKs
##########################################################################################

from ._VOYAGER_SCLKS import _VOYAGER_SCLKS

sclk_source = _source('SCLK')
sclk_source = (sclk_source, sclk_source + '/a_older_versions')      # two directories!

rule = Rule(r'vg[12](NNNNN)\.tsc', source=sclk_source, dest='Voyager/SCLK',
            family='Voyager-SCLK')
KernelFile.mutual_veto(rule.pattern)

sclk_notes = """\
    This function generates a Clock Kernel object for either or both of the Voyager
    spacecraft.

    Because Voyager remains an active mission decades after the flybys, new clock kernels
    continue to be released by JPL. However, version 6 from 1999-10-17, the earliest
    version available, covers the period through the Neptune encounter. Later versions are
    not needed for analysis of data from the planetary flybys.
"""

sclk = spicefunc('sclk', title='Voyager SCLK',
                 known=_VOYAGER_SCLKS,
                 unknown=rule.pattern, source=sclk_source,
                 exclude=('voyager',),
                 notes=sclk_notes,
                 propnames=('voyager',), docstrings=_DOCSTRINGS)

del sclk_source, rule, sclk_notes

##########################################################################################
# SPKs
##########################################################################################

from ._VOYAGER_SPKS import _VOYAGER_SPKS

family_dict = {k:'Voyager-' + v.capitalize() + '-SPK' for k,v in _PLANET_NAMES.items()}
rule = Rule(r'vgr?([12]).(?:<family>jup|sat|ura|nep).*\.bsp', source=_source('SPK'),
            dest='Voyager/SPK', family=family_dict)
KernelFile.veto(rule.pattern, r'vgr?\1.\2.*\.bsp')

# We use the version number of the associated jup/sat/ura/nep SPK as the version number of
# each Voyager SPK.
Rule(r'vgr?[12].(jup|sat|ura|nep)(NNN)\.bsp')       # sets version number if in basename

# Unfortunately, some early SPK files do not embed the planetary system kernel version
# into the name, so we need to add these manually.
KernelFile('vg1_jup.bsp'    ).version=100
KernelFile('vg2_jup.bsp'    ).version=100
KernelFile('vg1_sat.bsp'    ).version=86
KernelFile('vg2_sat.bsp'    ).version=86
KernelFile('vgr1_saturn.bsp').version=132
KernelFile('vgr2_saturn.bsp').version=132
KernelFile('vg2_ura.bsp'    ).version=33
KernelFile('vg2_nep.bsp'    ).version=22

# Provide a KernelSet of planet SPKs using the same inputs as spk()
def planet_spk(version=None, basename=None, tmin=None, tmax=None, ids=None, expand=None,
               voyager=None, planet=None, irregular=False, **keywords):

    # Create a set of flybys based on voyager and planet
    voyager = _input_set(voyager, default={1,2})
    planet = _input_set(planet, default={'JUPITER', 'SATURN', 'URANUS', 'NEPTUNE'})

    flybys = set()
    for v in voyager:
        for p in planet:
            flybys.add((v,p))

    del flybys[1, 'URANUS']
    del flybys[1, 'NEPTUNE']

    # Filter the flybys based on tmin and tmax
    if tmin is not None:
        tmin = _validate_time(tmin)
        flybys = {f for f in flybys if tmin < _DEFAULT_TIMES[f][1]}

    if tmax is not None:
        tmax = _validate_time(tmax)
        flybys = {f for f in flybys if tmax > _DEFAULT_TIMES[f][0]}

    # Convert to a set of planets only
    planets = {f[1] for f in flybys}

    # Create a list of prerequisite basenames
    prereq = []
    ids = _validate_naif_ids(ids)
    for planet in planets:
        pla = planet[:3].lower()
        module = _MODULES[pla]
        planet_ids = ids & module.ALL_IDS
        if not planet_ids:
            planet_ids = (module.ALL_IDS if irregular else module.SYSTEM)
        planet_basenames = _intersect_basenames(basename, pla + r'.*\.spk')

        spk = module.spk(version=version, basenames=planet_basenames,
                         tmin=tmin, tmax=tmax, ids=planet_ids, expand=True,
                         irregular=irregular, **keywords)
        if spk:
            prereq += spk.basenames

    return KernelSet(prereq)

spk_notes = """\
    This function generates an SP (trajectory) Kernel object for one or more of the
    Voyager planetary flybys. All kernels include the inner satellites of each planet for
    which a flyby is included.

    Versions are defined by the version of the associated planetary satellite kernel.
    For example, if planet="SATURN" and version=337, the associated Saturn satellite
    kernel is sat337.bsp.

    Available versions and their release years are as follows:
        Jupiter: 100 (1996), 204 (2007), 230 (2012);
        Saturn: 86 (1996), 132 (2003), 261 (2007), 286 (2008), 336 (2010), 337 (2012);
        Uranus: 33 (1996), 83 (2007), 111 (2014);
        Neptune: 22 (1999), 81 (2009).
"""

spk = spicefunc('spk', title='Voyager SPK',
                known=_VOYAGER_SPKS,
                unknown=rule.pattern, source=_source('SPK'),
                exclude=('voyager', 'planet'),
                require=(planet_spk,),
                default_times=_DEFAULT_TIMES, default_times_key=('voyager', 'planet'),
                default_ids=_DEFAULT_BODY_IDS, default_ids_key=('voyager', 'planet',
                                                                'irregular'),
                notes=spk_notes,
                propnames=('voyager', 'planet', 'irregular'), docstrings=_DOCSTRINGS)

del family_dict, rule, spk_notes, planet_spk

##########################################################################################
# Metakernel...
##########################################################################################

def meta(voyager=None, planet=None, instrument=None, *, irregular=False,
         tmin=None, tmax=None, ids=None,
         ck={}, fk={}, ik={}, sclk={}, spk={}):
    """A metakernel object for one or more flybys of the Voyager mission.

    Input:
        voyager     1 or 2 to select one of the two Voyager spacecraft; None to include
                    both.
        planet      use "JUPITER", "SATURN", "URANUS", or "NEPTUNE" to select a specific
                    planetary flyby; enclose multiple values in a tuple; None for all
                    flybys.
        instrument  return results for one or more instruments/frames: "BUS", "HGA",
                    "IRIS", "IRISOCC", "ISSNA", "ISSWA", "PPS", "UVS", "UVSOCC", or
                    "SCAN_PLATFORM". Enclose multiple values inside a set or tuple. Use
                    None for all instruments. "ISS" is equivalent to {"ISSNA", "ISSWA"}.
        irregular   True to include the planet's irregular satellites in the returned
                    Kernel object.
        ck, fk, ik, sclk, spk
                    optional dictionaries listing any non-default inputs to one of the
                    Voyager kernel functions of the same name.
    """

    # _meta avoids the name conflicts between ck the input and ck the function, etc.
    return _meta(voyager=voyager, planet=planet, instrument=instrument,
                 irregular=irregular, tmin=tmin, tmax=tmax, ids=ids,
                 ck_=ck, fk_=fk, ik_=ik, sclk_=sclk, spk_=spk)

def _meta(*, voyager, planet, instrument, irregular, tmin, tmax, ids,
          ck_, fk_, ik_, pck_, sclk_, spk_):

    ck_   = ck(voyager=voyager, planet=planet, instrument=instrument,
               tmin=tmin, tmax=tmax, ids=ids, **ck_)
    fk_   = fk(voyager=voyager, instrument=instrument, ids=ids, **fk_)
    ik_   = ik(voyager=voyager, instrument=instrument, ids=ids, **ik_)
    sclk_ = sclk(voyager=voyager, **sclk_)
    spk_  = spk(voyager=voyager, planet=planet, irregular=irregular,
                tmin=tmin, tmax=tmax, ids=ids, **spk_)

    return Metakernel([ck_, fk_, ik_, sclk_, spk_])

##########################################################################################

# Cleanup. Remove extraneous symbols from dir().
del _DOCSTRINGS
del _PLANET_NAMES
del _source
del spicefunc

##########################################################################################
