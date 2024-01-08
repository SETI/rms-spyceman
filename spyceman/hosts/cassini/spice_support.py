##########################################################################################
# hosts/cassini/spice.py
##########################################################################################

from kernel             import Kernel
from kernel.kernelfile  import KernelFile
from kernel.kernelset   import KernelSet

if not KernelFile.ABSPATHS:
    raise RuntimeError('No SPICE kernels have been identified')


_TOUR = (2003 - 2000) * 365 * 86400     # Rough TDB dividing Saturn from Jupiter


_WARNINGS = set()       # used to track any warnings so they are not repeated

def _warn_about_missing(basenames, planet, ktype, name):

    warning_name = planet + '-' + ktype + '-' + name
    if warning_name not in _WARNINGS:
        missing = []
        for basename in basenames:
            if not KernelFile(basename).exists:
                missing.append(basename)
        nmissing = len(missing)
        if nmissing == 1:
            warnings.warn(f'missing {planet} {ktype} file {missing[0]}')
        elif nmissing > 1:
            warnings.warn(f'{nmissing} missing  {planet} {ktype} files including '
                          f'{missing[0]}')

        _WARNINGS.append(warning_name)

def furnish(tmin, tmax=None, inst=''):
    """Furnish the selected Cassini kernels for the given time or time range."""

    tmax = tmin if tmax is None else tmin

    if tmin < TOUR:
        jupiter_ck().furnish(tmin, tmax)
        jupiter_spk().furnish(tmin, tmax)

    if tmax > TOUR:
        saturn_ck().furnish(tmin, tmax)
        saturn_spk().furnish(tmin, tmax)

def unload():
    """Unload the selected Cassini kernels."""

    jupiter_ck().unload()
    jupiter_spk().unload()

    saturn_ck().unload()
    saturn_spk().unload()

##########################################################################################
# SPK support
##########################################################################################

# Define the rule for interpreting release dates and time limits from most Cassini SPKs
_ = DateTimeRule(r'(YYMMDD)[RA][A-Z]?_(?:SCPSE|RE)_(YYDOY)_(YYDOY)(\.bsp)')

from ._SPK_RECONSTRUCTED_V1 import _SPK_RECONSTRUCTED_V1
from ._SPK_RECONSTRUCTED_V2 import _SPK_RECONSTRUCTED_V2
from ._SPK_RECONSTRUCTED_V3 import _SPK_RECONSTRUCTED_V3

_SPK_JUPITER_BASENAMES = [          # includes cruise to Jupiter
    '000331R_SK_LP0_V1P32',         # 1997-10-15T09:26:08|1998-05-28T21:22:00
    '000331RB_SK_V1P32_V2P12',      # 1998-05-28T21:21:59|1998-05-28T21:22:00
    '000331R_SK_V2P12_EP15',        # 1999-07-06T16:00:00|1999-09-02T12:00:00
    '010420R_SCPSE_EP1_JP83',       # 1999-08-19T01:58:56|2001-03-23T23:58:56
]

_SPK_JUPITER = KernelSet(_SPK_JUPITER_BASENAMES)

# This ensures that conflicting SPKs are always unloaded
Kernel.mutual_exclusions(_SPK_RECONSTRUCTED_V1, _SPK_RECONSTRUCTED_V2,
                         _SPK_RECONSTRUCTED_V3)

_SATURN_SPK_OPTIONS = {
    'reconstructed-v1': _SPK_RECONSTRUCTED_V1,
    'reconstructed-v2': _SPK_RECONSTRUCTED_V2,
    'reconstructed-v3': _SPK_RECONSTRUCTED_V3,
}

_JUPITER_SPK_OPTIONS = {
    'reconstructed': _SPK_JUPITER,
}

_SELECTED_SATURN_SPK = None
_SELECTED_JUPITER_SPK = None


def saturn_spk(name=''):
    """Set and return the SP kernel set for the Saturn tour, one of "reconstructed-v1",
    "reconstructed-v2", or "reconstructed-v3".

    Use a blank name to return the kernel set currently selected.
    """

    global _SELECTED_SATURN_SPK

    if not name:
        if _SELECTED_SATURN_SPK is None:
            return saturn_spk('reconstructed-v3')
        return _SELECTED_SATURN_SPK

    kernel = _SATURN_SPK_OPTIONS[name]      # KeyError on invalid name
    _warn_about_missing(kernel.basenames, 'Saturn', 'SPK', name)
    _SELECTED_SATURN_SPK = kernel


def jupiter_spk(name=''):
    """Set and return the SP kernel set to use for the Jupiter cruise and flyby.
    Currently, the only supported option is "reconstructed".

    Use a blank name to return the kernel set currently selected.
    """

    global _SELECTED_JUPITER_SPK

    if not name:
        if _SELECTED_JUPITER_SPK is None:
            return jupiter_spk('reconstructed')
        return _SELECTED_JUPITER_SPK

    kernel = _JUPITER_SPK_OPTIONS[name]     # KeyError on invalid name
    _warn_about_missing(kernel.basenames, 'Jupiter', 'SPK', name)
    _SELECTED_JUPITER_SPK = _JUPITER_SPK_OPTIONS[name]  # KeyError on invalid name

##########################################################################################
# CK support
##########################################################################################

# Define the rule for interpreting time limits from Cassini CKs
_ = TimeRule(r'(YYDOY)(_)(YYDOY)([pr][a-z]_.*\.bsp)')   # Saturn

from .ck_gapfill          import CK_GAPFILL_PATTERN, ck_gapfill
from .ck_v1_live          import CK_V1_PATTERN, ck_v1_live
from .ck_v2_as_flown      import CK_V2_PATTERN, ck_v2_as_flown
from .ck_v3_reconstructed import CK_V3_PATTERN, ck_v3_reconstructed

KernelFile.exclude_basenames((CK_V1_PATTERN,), (CK_V2_PATTERN,), (CK_V3_PATTERN,))
KernelFile.prerequisite_basenames(CK_V1_PATTERN, CK_GAPFILL_PATTERN)
KernelFile.prerequisite_basenames(CK_V2_PATTERN, CK_GAPFILL_PATTERN)
KernelFile.prerequisite_basenames(CK_V3_PATTERN, CK_GAPFILL_PATTERN)

_ = TimeRule(r'(YYMMDD)(_)(YYMMDD)r?[ab]?\.bsp', family='YYMMDD_YYMMDDrX.bsp')

from .ck_jupiter import ck_jupiter


def saturn_ck(name=''):
    """Set and return the C kernel set to use for the Saturn tour, one of "predicted-v1",
    "predicted-v2", or "reconstructed".

    Use a blank name to return the kernel set currently selected.
    """

    global _SELECTED_SATURN_CK

    if not name:
        if _SELECTED_SATURN_CK is None:
            return saturn_ck('reconstructed')
        return _SELECTED_SATURN_CK

    kernel = _SATURN_CK_OPTIONS[name]       # KeyError on failure
    _warn_about_missing(kernel.basenames, 'Saturn', 'CK', name)
    _SELECTED_SATURN_CK = kernel
    return _SELECTED_SATURN_CK


def jupiter_ck(name=''):
    """Set and return the C kernel set to use for the Jupiter flyby. Currently, the only
    supported option is "predicted".

    Use a blank name to return the kernel set currently selected.
    """

    global _SELECTED_JUPITER_CK

    if not name:
        if _SELECTED_JUPITER_CK is None:
            return jupiter_ck('predicted')
        return _SELECTED_JUPITER_CK

    kernel = _JUPITER_CK_OPTIONS[name]      # KeyError on failure
    _warn_about_missing(kernel.basenames + kernel.extras, 'Jupiter', 'CK', name)
    _SELECTED_JUPITER_CK = kernel
    return _SELECTED_JUPITER_CK


##########################################################################################
# Instrument kernel (IK) support
##########################################################################################

_LAST_IK_VERSION_RELEASED = {
    'CAPS' :  3,
    'CDA'  :  1,
    'CIRS' : 10,
    'INMS' :  2,
    'ISS'  : 10,
    'MAG'  :  1,
    'MIMI' : 11,
    'RADAR': 11,
    'RPWS' :  1,
    'RSS'  :  3,
    'SRU'  :  2,
    'UVIS' :  7,
    'VIMS' :  6,
}

# Build a dictionary of IKs by instrument, version number
_IK_VERSIONS = {k:{} for k in _LAST_IK_VERSION_RELEASED}
regex = re.compile(r'cas_([a-z]+)_v(\d\d)\.ti')
basenames = KernelFile.find_all(regex)
for basename in basenames:
    match = regex.match(basename)
    inst = match.group(1)
    version = int(match.group(2))
    _IK_VERSIONS[inst][version] = KernelFile(basename)

for key, kernel_dict in _IK_VERSIONS.items():
    Kernel.mutual_exclusions(kernel_dict.values())

_IK_FURNISHED = {}


def ik(inst, version=''):
    """Furnish and return a Cassini instrument kernel for a given instrument and version
    number.

    Use "latest" for the latest version. Use a blank name (the default) to return the
    instrument kernel currently selected for the specified instrument.
    """

    if inst not in _IK_VERSIONS:
        basenames = KernelFile.find_all('cas_' + inst.lower() + r'_v\d\d\.ti')

    if not version:
        if inst not in _IK_FURNISHED:
            return ik(inst, version='latest')
        return _IK_FURNISHED[inst]

    if version = 'latest':
        if not _IK_VERSIONS[inst]:
            raise ValueError(f'no Cassini {inst} instrument kernel matching '
                             f'"cas_{inst.lower()}_v*.ti" was found')
        version = max(_IK_VERSIONS[inst].keys())
        latest = _LAST_IK_VERSION_RELEASED[inst]
        warning_name = inst + '-ik'
        if version != latest and warning_name not in WARNINGS:
            warnings.warn(f'cas_{inst}_v{latest:02d}.ti is missing; using '
                          + _IK_VERSIONS[inst][version]))
            WARNINGS.add(warning_name)

    kernel = _IK_VERSIONS[inst][version]
    _IK_FURNISHED[inst] = kernel
    kernel.furnish()
    return kernel

##########################################################################################
# Instrument frames kernel (FK) support
##########################################################################################

LAST_IFK_VERSION_RELEASED = 43
IFK_VERSIONS = KernelFile.version_dict(r'cas_v(\d\d)\.tf', exclusions=True)
IFK_FURNISHED = None


def furnish_ifk(version='latest'):
    """Select a Cassini instrument frames kernel by version number or 'latest' for the
    latest.
    """

    if not version:
        version = 'latest'

    if version = 'latest':
        version = max(IFK_VERSIONS.keys()):
        latest = LAST_IFK_VERSION_RELEASED
        if version != latest and 'ifk' not in WARNINGS:
            warnings.warn(f'cas_v{latest:02d}.tf is missing; using {IFK_VERSIONS[fk]}')
            WARNINGS.add('ifk')

    IFK_FURNISHED = IFK_VERSIONS[version]
    IFK_FURNISHED.furnish()

    return IK_FURNISHED[inst]


def selected_ifk(inst):
    """The selected frames kernel as a KernelFile object."""

    if not IFK_FURNISHED:
        furnish_ifk()

    return IFK_FURNISHED


def unload_ifk()
    """Unload the instrument frames kernel."""

    global IFK_FURNISHED

    if IFK_FURNISHED:
        IFK_FURNISHED.unload()
        IFK_FURNISHED = None

##########################################################################################
# Cassini planetary constants and "rocks" frames kernel support
##########################################################################################

# Find the Nav and non-Nav PCKs
LAST_PCK_RELEASE_DATE = '2017-12-15'
pck_nav_pattern = r'cpck([0-3][A-Z][a-z][a-z]20[01][0-9])_Nav\.tpc'
PCK_NAV_VERSIONS = KernelFile.version_dict(pck_nav_pattern, vkey=True, exclusions=False)
pck_nonav_pattern = r'cpck([0-3][A-Z][a-z][a-z]20[01][0-9])\.tpc'
PCK_NAV_VERSIONS = KernelFile.version_dict(pck_nonav_pattern, vkey=True, exclusions=False)
PCK_VERSIONS = {True: PCK_NAV_VERSIONS, False: PCK_NONAV_VERSIONS}

# Nav and no-Nav versions are all exclusive of one another
Kernel.mutual_exclusions(list(PCK_NAV_VERSIONS.values()) +
                         list(PCK_NONAV_VERSIONS.values()))
PCK_FURNISHED = None

# Find the rocks PCKs
LAST_RPCK_RELEASE_DATE = '2011-01-21'
rpck_pattern = r'cpck_rock_([0-3][A-Z][a-z][a-z]20[01][0-9])\.tpc'
RPCK_VERSIONS = KernelFile.version_dict(rpck_pattern, vkey=True, exclusions=True)
RPCK_FURNISHED = None

# Find the rocks FKs
LAST_RFK_VERSION_RELEASED = 18
RFK_VERSIONS = KernelFile.version_dict(r'cas_rocks_v\d\d\.tf', vkey=True, exclusions=True)
RFK_FURNISHED = None

# Find the MST PCKs
MST_PCK_MOONS = {
    'aegaeon'   : 653,
    'atlas'     : 615,
    'calypso'   : 614,
    'daphnis'   : 635,
    'enceladus' : 602,
    'epimetheus': 611,
    'helene'    : 612,
    'janus'     : 610,
    'methone'   : 632,
    'pallene'   : 633,
    'pan'       : 618,
    'telesto'   : 613,
}

basenames = KernelFile.find_all(r'[a-z]+_mst201[38]\.bpc')
kernels = []
for basename in basenames:
    kernel = KernelFile(basename)
    kernel.release_date = '2018-09-27'
    kernel.time = ('2004-01-01T11:58:55.816', '2018-01-01T11:58:50.816')
    name = basename.partition('_')
    kernel.naif_ids = {MST_PCK_MOONS[name]}
    kernel.append(kernels)

MST_PCK = KernelSet(kernels)
MST_PCK_FURNISHED = False


def furnish_pck(date='latest', nav=False, rpck='latest', rfk='latest', mst=False,
                general=None):
    """Furnish Cassini planetary constants and frames kernels.

    Inputs:
        date        release date in 'yyyy-mm-dd' format. If this is not an exact match,
                    the  PCK with the latest release date prior to this date is furnished.
                    Use "latest" for the latest.
        nav         True (default) to use the Nav version; False to use the non-Nav
                    version.
        rpck        release date of the "rocks" PCK in 'yyyy-mm-dd' format. If this is not
                    an exact match, the  PCK with the latest release date prior to this
                    date is furnished. Use 'latest' for latest.
        rfk         version number of the "rocks" frames kernel, or 'latest' for the
                    latest.
        mst         True to furnish the MST rotation frames of small Saturn moons.
        general     If specified, this is the basename of a general NAIF PCK file that
                    should be furnished after the Cassini PCK but before the rocks and
                    "mst" kernels.

    Note: The Nav version of the PCK only defines gravity fields and planetary poles as
    used for navigating the spacecraft.

    The non-Nav version contains additional constants describing the sizes and rotation
    states of the Sun, Venus, Earth and the Moon, Jupiter and its largest moons, Saturn
    and its largest moons, and Saturn ring parameters. Note that some of this information
    is also defined in NAIF's general PCK file. For this reason, if you want to use the
    non-Nav PCK but alo want to use general PCK values from a later source, specify the
    basename of the later PCK at input.
    """

    global PCK_FURNISHED, RPCK_FURNISHED, RFK_FURNISHED, MST_PCK_FURNISHED

    ############################################
    # Identify the PCK
    ############################################

    if not date:
        date = 'latest'

    if date == 'latest':
        date = max(k for k in PCK_VERSIONS[nav])
        if date != LAST_PCK_RELEASE_DATE and 'pck' not in WARNINGS:
            warnings.warn('cpck15Dec2017' + ('_Nav.tpc' if nav else '.tpc')
                          + ' is missing; using ' + PCK_VERSIONS[nav][date])
            WARNINGS.add('pck')

    elif date not in PCK_VERSIONS[nav]:
        dates = max(k for k in PCK_VERSIONS[nav] if k < date)

    selected_pck = PCK_VERSIONS[nav][date]

    ############################################
    # Identify the rocks PCK
    ############################################

    if not rpck:
        rpck = 'latest'

    if rpck == 'latest':
        rpck = max(k for k in RPCK_VERSIONS[nav])
        if rpck != LAST_RPCK_RELEASE_DATE and 'rpck' not in WARNINGS:
            warnings.warn('cpck_rock_21Jan2021.tpc is missing; using '
                          + RPCK_VERSIONS[date])
            WARNINGS.add('rpck')

    elif rpck not in RPCK_VERSIONS:
        rpck = max(k for k in RPCK_VERSIONS if k < rpck)

    selected_rpck = PCK_VERSIONS[rpck]

    ############################################
    # Identify the rocks frames kernel
    ############################################

    if not rfk:
        rfk = 'latest'

    if rfk == 'latest':
        rfk = max(RFK_VERSIONS.keys()):
        if version != LAST_RFK_VERSION_RELEASED and 'rfk' not in WARNINGS:
            warnings.warn('cas_rocks_v%02d.tf is missing; using %s'
                          % (LAST_RFK_VERSION_RELEASED, RFK_VERSIONS[rfk]))
            WARNINGS.add('rfk')

    IFK_FURNISHED = IFK_VERSIONS[version]
    IFK_FURNISHED.furnish()


    elif date not in PCK_VERSIONS[nav]:
        dates = max(k for k in PCK_VERSIONS[nav].keys() if k < date)

    pck = PCK_VERSIONS[nav][date]


'2011-01-21'
rpck_pattern = r'cpck_rock_([0-3][A-Z][a-z][a-z]20[01][0-9])\.tpc'



    if general_pck:
        if isinstance(general_pck, str):
            general_pck = KernelFile(general_pck)
        general_pck.furnish()

    return PCK_FURNISHED

def selected_pck(inst):
    """The selected Cassini planetary constants kernel as a KernelFile object.
    """

    if not PCK_FURNISHED:
        furnish_pck()

    return PCK_FURNISHED

def unload_pck()
    """Unload the Cassini planetary constants kernel."""

    global PCK_FURNISHED

    if PCK_FURNISHED:
        PCK_FURNISHED.unload()
        PCK_FURNISHED = None

##########################################################################################
# Cassini "rock" planetary constants kernels
##########################################################################################

LAST_RPCK_RELEASE_DATE = '2011-01-21'

rpck_pattern = r'cpck_rock_([0-3][A-Z][a-z][a-z]20[01][0-9])\.tpc'
basenames = KernelFile.find_all(rpck_pattern)
RPCK_VERSIONS = {KernelFile(b).release_date:b for b in basenames}

RPCK_PATTERN = r'cpck_rock_([0-3][A-Z][a-z][a-z]20[01][0-9])\.tpc'
RPCK_VERSIONS = KernelFile.pattern_dict(RPCK_NAV_PATTERN)

RPCK_FURNISHED = None

def furnish_rpck(date='', general_pck=None):
    """Select a Cassini "rock" planetary constants kernel by date.

    Inputs:
        date        release date in 'yyyy-mm-dd' format. If this is not an exact match,
                    the  PCK with the latest release date prior to this date is furnished.
        general_pck If specified, this is the Kernel object or basename of a general NAIF
                    NAIF PCK file that should be furnished after the specified PCK is
                    furnished.
    """

    global RPCK_FURNISHED

    if not date:

        # If the latest RPCK was not found, warn
        date = max(k for k in RPCK_VERSIONS.keys())
        if date != LAST_RPCK_RELEASE_DATE and 'RPCK' not in WARNINGS:
            warnings.warn('cpck_rock_21Jan2011.tpc is missing; using '
                          + RPCK_VERSIONS[latest])
            WARNINGS.add('RPCK')

    RPCK_FURNISHED = RPCK_VERSIONS[nav][date]
    RPCK_FURNISHED.furnish()

    if general_pck:
        if isinstance(general_pck, str):
            general_pck = KernelFile(general_pck)
        general_pck.furnish()

    return RPCK_FURNISHED

def selected_pck(inst):
    """The selected Cassini planetary constants kernel as a KernelFile object.
    """

    if not RPCK_FURNISHED:
        furnish_pck()

    return RPCK_FURNISHED

def unload_pck()
    """Unload the Cassini planetary constants kernel."""

    global RPCK_FURNISHED

    if RPCK_FURNISHED:
        RPCK_FURNISHED.unload()
        RPCK_FURNISHED = None

##########################################################################################
# Spacecraft clock kernels
##########################################################################################

basenames = KernelFile.find_all(r'cas00\d\d\d\.tsc')
SCLK_OPTIONS = {KernelFile(b).version:KernelFile(b) for b in basenames}

if 172 in SCLK_OPTIONS:
    SCLK_OPTIONS['reconstructed'] = SCLK_OPTIONS[172]
if 171 in SCLK_OPTIONS:
    SCLK_OPTIONS['tour'] = SCLK_OPTIONS[171]

for version, basename in SCLK_OPTIONS.items():
    SCLK_OPTIONS[version] = KernelFile(basename)

Kernel.mutual_exclusions(*SCLK_OPTIONS.values())

SCLK_FURNISHED = None

def furnish_sclk(version=''):
    """Furnish the spacecraft clock kernel, one of "tour" or "reconstructed", or an
    integer 1-172, and return the KernelFile object.

    Use a blank name to select the default, "reconstructed".
    """

    global SCLK_FURNISHED

    name = name or 'reconstructed'
    SCLK_FURNISHED = SCLK_OPTIONS[name]     # KeyError on invalid name
    SCLK_FURNISHED.furnish()
    return SCLK_FURNISHED

def selected_sclk(inst):
    """This spacecraft clock kernel as a KernelFile object."""

    if SCLK_FURNISHED is None:
        furnish_sclk()

    return SCLK_FURNISHED

def unload_sclk()
    """Unload the spacecraft clock kernel."""

    global SCLK_FURNISHED

    if SCLK_FURNISHED:
        SCLK_FURNISHED.unload()
        SCLK_FURNISHED = None

##########################################################################################
# Cassini binary PCKs for the Saturn moons
##########################################################################################

# Fill in the MST PCK kernel info
MST_PCK_MOONS = {
    'aegaeon'   : 653,
    'atlas'     : 615,
    'calypso'   : 614,
    'daphnis'   : 635,
    'enceladus' : 602,
    'epimetheus': 611,
    'helene'    : 612,
    'janus'     : 610,
    'methone'   : 632,
    'pallene'   : 633,
    'pan'       : 618,
    'telesto'   : 613,
}

basenames = KernelFile.find_all(r'[a-z]+_mst201[38]\.bpc')

kernels = []
for basename in basenames:
    kernel = KernelFile(basename)
    kernel.release_date = '2018-09-27'
    kernel.time = ('2004-01-01T11:58:55.816', '2018-01-01T11:58:50.816')
    name = basename.partition('_')
    kernel.naif_ids = {MST_PCK_MOONS[name]}
    kernel.append(MST_PCK_KERNELS)

MST_PCK = KernelSet(kernels)

def furnish_mst_pck():
    """Furnish the MST PCKs to the top.

    Note that these should be loaded after any text PCK files. This level of
    kernel management is left to the user.
    """

    if 'mst-pck' not in WARNINGS:
        for kernel in MST_PCK_KERNELS:
            if not kernel.exists:
                warnings.warn(kernel.name + ' missing')
        WARNINGS.add('mst-pck')

    MST_PCK.furnish()

def unload_mst_pck()
    """Unload the spacecraft clock kernel."""

    MST_PCK.unload()

##########################################################################################
