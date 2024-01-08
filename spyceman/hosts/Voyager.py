##########################################################################################
# spyceman/hosts/Voyager.py
##########################################################################################
"""\
spyceman.hosts.Voyager: Support for Voyager-specific kernels.

The following attributes are defined:

VG1, VG2        the body IDs of Voyager 1 and Voyager 2.
VG1_ISSNA, ...  the frame IDs of all the Voyager instruments.

The following functions are defined:

ck()            function returning a C (pointing) kernel given various constraints.
fk()            function returning a frames kernel given various constraints.
ik()            function returning an instrument kernel given various constraints.
sclk()          function returning a clock kernel given various constraints.
spk()           function returning a SP (trajectory) kernel given various constraints.
metakernel()    function returning a Metakernel containing all of the above.
"""

from spyceman         import CSPYCE, KernelFile, KTuple, Metakernel, Rule, spicefunc
from spyceman.planets import Jupiter, Saturn, Uranus, Neptune

################################################
# Body and frame definitions
################################################

BODY_ID = {1: -31, 2: -32}
VG1 = BODY_ID[1]
VG2 = BODY_ID[2]

VG1_SC_BUS        = -31000
VG1_SCAN_PLATFORM = -31100
VG1_HGA           = -31400
VG1_ISSNA         = -31101
VG1_ISSWA         = -31102
VG1_PPS           = -31103
VG1_UVS           = -31104
VG1_UVSOCC        = -31105
VG1_IRIS          = -31106
VG1_IRISOCC       = -31107

VG2_SC_BUS        = -32000
VG2_SCAN_PLATFORM = -32100
VG2_HGA           = -32400
VG2_ISSNA         = -32101
VG2_ISSWA         = -32102
VG2_PPS           = -32103
VG2_UVS           = -32104
VG2_UVSOCC        = -32105
VG2_IRIS          = -32106
VG2_IRISOCC       = -32107

VG1_BUS = VG1_SC_BUS
VG2_BUS = VG1_SC_BUS

FRAME_ID = {}
for key in ('SC_BUS', 'BUS', 'SCAN_PLATFORM', 'HGA', 'ISSNA', 'ISSWA', 'PPS', 'UVS',
            'UVSOCC', 'IRIS', 'IRISOCC'):
    for voyager in (1,2):
        FRAME_ID[voyager, key] = locals()[f'VG{voyager}_{key}']

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

_DATE_RANGES = {
    (1, 'jup'): ('1979-01-04T23:55:45', '-1979-04-13T23:56:44'),
    (2, 'jup'): ('1979-04-25T00:26:27', '-1979-08-29T00:00:00'),
    (1, 'sat'): ('1980-08-06T23:59:09', '-1981-01-01T00:00:00'),
    (2, 'sat'): ('1981-06-01T00:00:00', '-1981-10-21T23:59:00'),
    (2, 'ura'): ('1985-08-21T23:59:05', '-1986-02-25T13:42:00'),
    (2, 'nep'): ('1989-04-03T16:24:35', '-1989-10-03T00:00:00'),
}

_DATE_RANGES[None, 'jup'] = (_DATE_RANGES(1, 'jup')[0], _DATE_RANGES(2, 'jup')[1])
_DATE_RANGES[None, 'sat'] = (_DATE_RANGES(1, 'sat')[0], _DATE_RANGES(2, 'sat')[1])
_DATE_RANGES[None, 'ura'] =  _DATE_RANGES(2, 'ura')
_DATE_RANGES[None, 'nep'] =  _DATE_RANGES(2, 'nep')
_DATE_RANGES[1   , None ] = (_DATE_RANGES(1, 'jup')[0], _DATE_RANGES(1, 'sat')[1])
_DATE_RANGES[2   , None ] = (_DATE_RANGES(2, 'jup')[0], _DATE_RANGES(2, 'nep')[1])
_DATE_RANGES[None, None ] = (_DATE_RANGES(1, 'jup')[0], _DATE_RANGES(2, 'nep')[1])

##########################################################################################
# Define properties
##########################################################################################

# Define voyager and planet, as common properties
Rule(r'vgr?(?P<voyager>[12]).*', voyager=int, mission='VOYAGER')
Rule(r'vg.*(?P<planet>jup|sat|ura|nep).*', planet=_PLANET_NAMES)

DOCSTRINGS = {}
DOCSTRINGS['voyager'] = """\
        voyager     1 or 2 to select one of the two Voyager spacecraft; None to include
                    both.
"""

DOCSTRINGS['planet'] = """\
        planet      use "JUPITER", "SATURN", "URANUS", or "NEPTUNE" to select a specific
                    planetary flyby; enclose multiple values in a tuple; None for all
                    flybys.
"""

DOCSTRINGS['component'] = """\
        component   use "SCAN_PLATFORM" or "BUS" to specify one of the two components of
                    the spacecraft that could be oriented independently.
"""

DOCSTRINGS['source'] = """\
        source      use "QMW" for the Queen Mary College CK; "SEDR" for the SEDR-based CK;
                    None for any.
"""

DOCSTRINGS['ctype'] = """\
        ctype       the type of the C kernel, e.g., 1 or 3.
"""

DOCSTRINGS['instrument'] = """\
        instrument  return results for one or more instruments/frames: "ISSNA", "ISSWA",
                    "PPS", "UVS", "UVSOCC", "IRIS", "IRISOCC", "BUS", "SCAN_PLATFORM", or
                    "HGA". Enclose multiple values inside a tuple. Use None for all
                    instruments.
"""

##########################################################################################
# Managed list of known CKs...
##########################################################################################

_CK_QMW_INFO = [

    KTuple('vg1_jup_qmw_na.bc',
        '1979-01-04T23:55:44.952', '1979-04-13T23:56:42.615',
        {-31001},
        None),
    KTuple('vg1_jup_qmw_wa.bc',
        '1979-02-04T03:19:45.592', '1979-04-13T23:53:30.615',
        {-31002},
        None),
    KTuple('vg2_jup_qmw_na.bc',
        '1979-04-25T00:26:26.963', '1979-07-16T17:06:20.576',
        {-32001},
        None),
    KTuple('vg2_jup_qmw_wa.bc',
        '1979-05-26T00:54:24.416', '1979-07-16T17:08:44.575',
        {-32002},
        None),
    KTuple('vg1_sat_qmw_na.bc',
        '1980-08-23T12:43:44.488', '1980-12-15T23:48:33.158',
        {-31001},
        None),
    KTuple('vg1_sat_qmw_wa.bc',
        '1980-10-25T01:31:44.774', '1980-12-15T23:50:57.158',
        {-31002},
        None),
    KTuple('vg2_sat_qmw_na.bc',
        '1981-06-05T16:35:17.357', '1981-09-25T18:51:06.393',
        {-32001},
        None),
    KTuple('vg2_sat_qmw_wa.bc',
        '1981-06-05T16:37:41.357', '1981-09-25T18:53:30.393',
        {-32002},
        None),
]

Rule(r'vgr?([12])_(jup|sat|ura|nep)_qmw_[nw]a\.bc', version=0,
     family=r'vg\1_\2_qmw.bc', ctype=1, source='QMW', component='SCAN_PLATFORM')

# Note that the QMW kernels do not use the correct frame IDs for ISSNA and ISSWA.
CSPYCE.define_frame_aliases('VG1_ISSNA', VG1_ISSNA, -31001)
CSPYCE.define_frame_aliases('VG1_ISSWA', VG1_ISSWA, -31002)
CSPYCE.define_frame_aliases('VG2_ISSNA', VG2_ISSNA, -32001)
CSPYCE.define_frame_aliases('VG2_ISSWA', VG2_ISSWA, -32002)

_CK_SEDR_INFO = [

    KTuple('vg1_jup_version1_type1_iss_sedr.bc',
        '1979-01-04T23:55:46.932', '1979-04-13T23:56:44.595',
        {-31100},
        '2007-06-05'),
    KTuple('vg2_jup_version1_type1_iss_sedr.bc',
        '1979-04-25T00:26:28.943', '1979-07-16T17:08:46.555',
        {-32100},
        '2007-06-05'),
    KTuple('vg1_sat_version1_type1_iss_sedr.bc',
        '1980-08-23T12:43:46.468', '1980-12-15T23:50:59.138',
        {-31100},
        '2007-06-05'),
    KTuple('vg1_sat_version2_type3_uvs_sedr.bc',
        '1980-08-22T23:10:10.456', '1980-12-16T02:08:35.138',
        {-31104},
        "2007-06-05"),
    KTuple('vg2_sat_version1_type1_iss_sedr.bc',
        '1981-06-05T16:35:19.337', '1981-09-25T18:53:32.373',
        {-32100},
        '2007-06-05'),
    KTuple('vg2_ura_version1_type1_iss_sedr.bc',
        '1985-11-06T17:13:44.887', '1986-02-19T18:43:57.478',
        {-32100},
        '2007-06-05'),
    KTuple('vg2_nep_version1_type1_iss_sedr.bc',
        '1989-04-03T16:24:34.451', '1989-09-19T00:28:44.329',
        {-32100},
        '2013-07-04'),
]

Rule(r'vgr?([12])_(jup|sat|ura|nep)_version(N)_type(P?<ctype>[13])_(iss|uvs)_sedr\.bc',
     family=r'vg\1_\2_versionN_typeN_\5_sedr.bc', ctype=int, source='SEDR',
     component='SCAN_PLATFORM')

scan_platform_ck = spicefunc('scan_platform_ck', title='Voyager scan platform CKs',
                             pattern=r'vgr?[12].*(jup|sat|ura|nep).*\.bc',
                             known=_CK_QMW_INFO + _CK_SEDR_INFO,
                             exclusions=('voyager', 'planet'),
                             propnames=('voyager', 'planet', 'source', 'ctype'),
                             docstrings=DOCSTRINGS)

_CK_BUS_INFO = [

# SEDR bus family
    KTuple('vgr1_super_old.bc',
        '1977-09-05T14:09:23.604', '2027-12-26T23:58:12.291',
        {-31000},
        '2000-02-24'),
    KTuple('vgr2_super_old.bc',
        '1977-08-20T16:06:18.353', '2027-12-27T00:06:24.993',
        {-32000},
        '1999-01-31'),
    KTuple('vgr1_super.bc',
        '1977-09-05T14:09:23.604', '2027-12-26T23:58:12.291',
        {-31000},
        '2000-02-24'),
    KTuple('vgr2_super.bc',
        '1977-08-20T16:06:18.353', '2027-12-27T00:06:24.993',
        {-32000},
        '1999-01-31'),
]

Rule(r'vgr?([12])_super.*\.bc', family=r'vgr\1_super.bc', ctype=3, source='SEDR',
     component='BUS')

# This is an ad hoc version numbering system for the bus CKs.
KernelFile('vgr1_super_old.bc').version=0
KernelFile('vgr2_super_old.bc').version=0
KernelFile('vgr1_super.bc').version=1
KernelFile('vgr2_super.bc').version=1

# This assigns version=2 to any future "vgr?_super" file where the suffix is not "old"
Rule(r'vgr?([12])_super_(?!old).+\.bc', version=2)

bus_ck = spicefunc('bus_ck', title='Voyager bus CKs',
                   pattern=r'vgr?[12]_super.*\.bc', known=_CK_BUS_INFO,
                   exclusions=('voyager',),
                   propnames=('voyager', 'source', 'ctype'), docstrings=DOCSTRINGS)

ck = spicefunc('ck', title='Voyager CKs',
               pattern=None, known=(scan_platform_ck, ck),
               exclusions=('voyager', 'planet', 'component'),
               propnames=('voyager', 'planet', 'source', 'ctype'), docstrings=DOCSTRINGS)

##########################################################################################
# Managed list of known FKs...
##########################################################################################

_VG_FK = [
    KTuple('vg1_v02.tf', None, None,
        {-31400, -31300, -31200, -31107, -31106, -31105, -31104, -31103, -31102,
         -31101, -31100, -31000},
        '2000-11-27'),
    KTuple('vg2_v02.tf', None, None,
        {-32400, -32300, -32200, -32107, -32106, -32105, -32104, -32103, -32102,
         -32101, -32100, -32000},
        '2000-11-27'),
]

Rule(r'vgr?([12])_v(NN).*\.tf', family=r'vg\1_vNN.tf')

fk = spicefunc('fk', title='Voyager FKs',
               pattern=r'vg[12]_v(\d\d)\.tf', known=_VG_FK,
               exclusions=('voyager',),
               propnames='voyager', docstrings=DOCSTRINGS)

##########################################################################################
# Managed list of known IKs...
##########################################################################################

_VG_IK = [
    KTuple('vg1_issna_v02.ti', None, None, {-31101}, '2000-11-27'),
    KTuple('vg1_isswa_v01.ti', None, None, {-31102}, '2000-11-27'),
    KTuple('vg2_issna_v02.ti', None, None, {-32101}, '2000-11-27'),
    KTuple('vg2_isswa_v01.ti', None, None, {-32102}, '2000-11-27'),
]

Rule(r'vgr?[12]_(?P<instrument>[a-z]+)_v\d\d\.ti',  instrument=str.upper)

ik = spicefunc('ik', title='Voyager IK',
               pattern=r'vg[12]_([a-z]+)_v(\d\d)\.ti', known=_VG_IK,
               exclusions=('voyager', 'instrument'),
               propnames=('voyager', 'instrument'), docstrings=DOCSTRINGS)

##########################################################################################
# Managed list of known SCLKs...
##########################################################################################

_SCLK_INFO = [
    KTuple('vg100006.tsc', None, None, {-31}, '1999-10-17'),
    KTuple('vg100010.tsc', None, None, {-31}, '2007-01-19'),
    KTuple('vg100011.tsc', None, None, {-31}, '2010-07-23'),
    KTuple('vg100019.tsc', None, None, {-31}, '2012-01-03'),
    KTuple('vg100042.tsc', None, None, {-31}, '2022-07-25'),
    KTuple('vg200006.tsc', None, None, {-32}, '1999-10-17'),
    KTuple('vg200010.tsc', None, None, {-32}, '2007-01-19'),
    KTuple('vg200011.tsc', None, None, {-32}, '2010-07-20'),
    KTuple('vg200022.tsc', None, None, {-32}, '2011-10-18'),
    KTuple('vg200041.tsc', None, None, {-32}, '2022-07-25'),
]

Rule(r'(?:vg[12](NNNNN)\.tsc')

sclk = spicefunc('sclk', title='Voyager SCLK',
                 pattern=r'vg[12](\d\d\d\d\d)\.tsc', known=_SCLK_INFO,
                 exclusions=('voyager,'),
                 propnames='voyager', docstrings=DOCSTRINGS)

##########################################################################################
# Managed list of known SPKs...
##########################################################################################

_SPK_INFO = [

# Jupiter
KTuple('vg1_jup.bsp',
    '1979-02-06T00:00:00', '1979-04-09T00:00:00',
    {-31, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 501, 502, 503,
     504, 505, 514, 515, 516, 599},
    '1996-09-05'),
KTuple('vg2_jup.bsp',
    '1979-06-08T00:00:00', '1979-08-29T00:00:00',
    {-32, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 501, 502, 503,
     504, 505, 514, 515, 516, 599},
    '1996-09-05'),
KTuple('vgr1_jup204.bsp',
    '1979-01-31T23:59:09.815', '1979-03-18T23:59:09.814',
    {-31},
    '2007-01-26'),
KTuple('vgr2_jup204.bsp',
    '1979-06-04T16:59:09.815', '1979-07-20T23:59:09.816',
    {-32},
    '2007-01-26'),
KTuple('vgr1_jup230.bsp',
    '1979-01-31T23:59:09.815', '1979-03-18T23:59:09.814',
    {-31},
    '2012-02-13'),
KTuple('vgr2_jup230.bsp',
    '1979-06-04T16:59:09.815', '1979-07-20T23:59:09.816',
    {-32},
    '2012-02-13'),

# Saturn
KTuple('vg1_sat.bsp',
    '1980-08-23T00:00:00', '1981-01-01T00:00:00',
    {-31, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 601, 602, 603,
     604, 605, 606, 607, 608, 610, 611, 612, 613, 614, 615, 616, 617, 699},
    '1996-09-05'),
KTuple('vg2_sat.bsp',
    '1981-06-01T00:00:00', '1981-10-21T23:59:00',
    {-32, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 601, 602, 603,
     604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 699},
    '1996-09-05'),
KTuple('vgr1_saturn.bsp',
    '1980-08-06T23:59:08.817', '1980-11-19T23:59:08.817',
    {-31},
    '2003-02-06'),
KTuple('vgr2_saturn.bsp',
    '1981-06-07T23:59:08.815', '1981-09-21T23:59:07.818',
    {-32},
    '2003-02-06'),
KTuple('vgr1_sat261.bsp',
    '1980-08-06T23:59:08.817', '1980-11-19T23:59:08.817',
    {-31},
    '2007-01-26'),
KTuple('vgr2_sat261.bsp',
    '1981-06-07T23:59:08.815', '1981-09-21T23:59:07.818',
    {-32},
    '2007-01-26'),
KTuple('vgr1_sat286.bsp',
    '1980-08-06T23:59:08.817', '1980-11-19T23:59:08.817',
    {-31},
    '2008-05-05'),
KTuple('vgr2_sat286.bsp',
    '1981-06-07T23:59:08.815', '1981-09-21T23:59:07.818',
    {-32},
    '2008-05-05'),
KTuple('vgr1_sat336.bsp',
    '1980-08-06T23:59:08.817', '1980-11-19T23:59:08.817',
    {-31},
    '2010-07-21'),
KTuple('vgr2_sat336.bsp',
    '1981-06-07T23:59:08.815', '1981-09-21T23:59:07.818',
    {-32},
    '2010-07-21'),
KTuple('vgr1_sat337.bsp',
    '1980-08-06T23:59:08.817', '1980-11-19T23:59:08.817',
    {-31},
    '2012-02-13'),
KTuple('vgr2_sat337.bsp',
    '1981-06-07T23:59:08.815', '1981-09-21T23:59:07.818',
    {-32},
    '2012-02-13'),

# Uranus
KTuple('vg2_ura.bsp',
    '1985-11-04T12:00:00', '1986-02-25T13:42:00',
    {-32, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 701, 702, 703,
     704, 705, 799},
    '1996-09-05'),
KTuple('vgr2_ura083.bsp',
    '1977-03-03T23:59:11.815', '2008-12-29T23:58:54.816',
    {-32, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 701, 702, 703,
     704, 705, 799},
    '2007-08-01'),
KTuple('vgr2.ura111.bsp',
    '1985-08-21T23:59:04.817', '1986-02-13T23:59:04.815',
    {-32},
    '2014-10-24'),

# Neptune
KTuple('vg2_nep.bsp',
    '1989-06-03T00:00:00', '1989-10-03T00:00:00',
    {-32, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499, 801, 802, 803,
     804, 805, 806, 807, 808, 899},
    '1999-02-01'),
KTuple('vgr2_nep081.bsp',
    '1988-11-12T23:59:03.817', '1989-10-01T11:59:03.818',
    {-32},
    '2009-06-24'),
]
KernelFile.set_info(_SPK_INFO)

# We use the version number of the associated jup/sat/ura/nep SPK as the version number of
# each Voyager SPK.
Rule(r'vgr?([12]).(jup|sat|ura|nep)(NNN)\.bsp', family=r'vgr\1_\2NNN.bsp')

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

def _voyager_spk_kernels():
    """Create a Kernel object with a planetary system prerequisite for each Voyager SPK.

    This cannot happen at import time because the KernelFile.walk() might not have been
    called yet.
    """

    # Initialize a dictionary basename -> kernel
    kernels = {}

    # For every existing Voyager SPK...
    basenames = KernelFile.find_all(r'vgr?[12]_(jup|sat|ura|nep).*\.bsp')
    for basename in basenames:

        # Determine the spacecraft and planet
        kfile = KernelFile(basename)
        voyager = kfile.properties['voyager']
        planet_key = kfile.properties['planet'][:3].lower()

        # Focus on the relevant date range
        (tmin, tmax) = _DATE_RANGES[voyager, planet_key]

        # Define a planetary system SPK for the same version number as the prerequisite
        planet_key = basename.partition('_')[1][:3].lower()
        module = _MODULES[planet_key]
        prereq = module.spk(tmin=tmin, tmax=tmax, ids=module.SYSTEM,
                            version=kfile.version, expand=True)
        kfile.require(prereq)

        # Exclude any other SPK for this spacecraft and planet
        kfile.exclude(f'vgr?{voyager}_{planet_key}.*\\.bsp')

        kernels[basename] = kfile

    return kernels

spk = spicefunc('spk', title='Voyager SPKs', pattern=r'vgr?[12].(jup|sat|ura|nep).*\.bsp',
                known=_voyager_spk_kernels,
                exclusions=('voyager', 'planet'),
                propnames=('voyager', 'planet'), docstrings=DOCSTRINGS)

##########################################################################################

def metakernel(*, ids=set(), dates=None, voyager=None, planet=None,
                  ck=None, fk=None, ik=None, sclk=None, spk=None):
    """A metakernel supporting one or more Voyager flybys.

    Input:
        voyager     1 or 2 to select one of the two Voyager spacecraft; None (the default)
                    includes both.
        planet      use "JUPITER", "SATURN", "URANUS", or "NEPTUNE" to select a specific
                    planetary flyby; None to include all of the planets.
        ck          optional C kernel to override the default.
        fk          optional frames kernel to override the default.
        ik          optional instrument kernel to override the default.
        sclk        optional spacecraft clock kernel to override the default.
        spk         optional SP kernel to override the default.

        dates       unless overridden, only use kernel files released within this range of
                    dates. Use a tuple of two date strings defining the earliest and
                    latest dates to include. Replace either date value with None or an
                    empty string to ignore that constraint. A single date is treated as
                    the upper limit on the release date.
    """

    planet_key = planet and planet[:3].lower()  # if planet is None, planet_key is None
    tmin, tmax = _DATE_RANGES[voyager, planet_key]

    if isinstance(ids, (set, list, tuple)):
        ids = set(ids)
    else:
        ids = {ids}

    # We need to refer to the kernel creator functions using globals() because we are
    # using the same names for the function arguments.
    if ck is None:
        ck = globals()['ck'](tmin=tmin, tmax=tmax, ids=ids, dates=dates,
                             voyager=voyager, planet=planet)

    if fk is None:
        fk = globals()['fk'](ids=ids, dates=dates, voyager=voyager)

    if ik is None:
        ik = globals()['ik'](ids=ids, dates=dates, voyager=voyager)

    if sclk is None:
        sclk = globals()['sclk'](ids=ids, dates=dates, voyager=voyager)

    if spk is None:
        spk = globals()['spk'](tmin=tmin, tmax=tmax, ids=ids, dates=dates,
                               voyager=voyager, planet=planet)

    return Metakernel(ck=ck, fk=fk, ik=ik, sclk=sclk, spk=spk)

##########################################################################################
