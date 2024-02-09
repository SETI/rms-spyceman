##########################################################################################
# spyceman/hosts/Cassini/__init__.py
##########################################################################################
"""\
spyceman.hosts.Cassini: Support for Cassini-specific kernels.

The following attributes are defined:

NAME            'CASSINI'.
BODY_ID         the body ID of Cassini, -82.
FRAME_IDS       a dictionary mapping frame name or (instrument, component) to frame ID.
FRAME_NAMES     a dictionary mapping frame ID to frame name.
INSTRUMENT_NAMES set of all instrument names.
INSTRUMENT_IDS  a dictionary mapping each instrument to the associated set of frame IDs.

The following functions are defined:

spk()           function returning a C (pointing) kernel for any part of the mission.
fk()            function returning a frames kernel.
ik()            function returning an instrument kernel.
sclk()          function returning a spacecraft clock kernel.
spk()           function returning an SP (trajectory) kernel for any part of the mission.
meta()          function returning a Metakernel containing all of the above.

The following, more focused kernel functions are also available, although the ones listed
above will meet most users' needs:

gapfill_ck()    a low-precedence "gapfill" CK for the Saturn tour.
jupiter_ck()    a CK for the Jupiter flyby.

cruise_spk()    SPK for the cruise to Saturn including the Jupiter flyby.
small_satellite_spk()       SPK for Saturn's small satellites.
irregular_satellite_spk()   SPK for Saturn's irregular satellites.
"""

from spyceman.kernelfile  import KernelFile
from spyceman.metakernel  import Metakernel
from spyceman.rule        import Rule
from spyceman.spicefunc   import spicefunc

from .ck     import gapfill_ck, jupiter_ck, ck
from .spk    import cruise_spk, small_satellite_spk, irregular_satellite_spk, spk
from ._utils import BODY_ID, _source

NAME = 'CASSINI'

INSTRUMENT_NAMES = {'CAPS', 'CDA', 'CIRS', 'INMS', 'ISS', 'MAG', 'MIMI', 'RADAR', 'RPWS',
                    'RSS', 'UVIS', 'VIMS'}

FRAME_IDS = {   # from cas_v43.tf
    'SC_COORD'     : -82000,
    'HGA'          : -82101,
    'LGA1'         : -82102,
    'LGA2'         : -82103,
    'XBAND'        : -82104,
    'KABAND'       : -82105,
    'KUBAND'       : -82106,
    'SBAND'        : -82107,
    'XBAND_TRUE'   : -82108,
    'ISS_NAC'      : -82360,
    'ISS_WAC'      : -82361,
    'CIRS_FP1'     : -82890,
    'CIRS_FP3'     : -82891,
    'CIRS_FP4'     : -82892,
    'CIRS_FPB'     : -82893,
    'UVIS_FUV'     : -82840,
    'UVIS_EUV'     : -82842,
    'UVIS_SOLAR'   : -82843,
    'UVIS_SOL_OFF' : -82849,
    'UVIS_HSP'     : -82844,
    'UVIS_HDAC'    : -82845,
    'VIMS_V'       : -82370,
    'VIMS_IR'      : -82371,
    'VIMS_IR_SOL'  : -82372,
    'CAPS'         : -82820,
    'CDA'          : -82790,
    'INMS'         : -82740,
    'MAG_PLUS'     : -82350,
    'MAG_MINUS'    : -82351,
    'MIMI_CHEMS'   : -82760,
    'MIMI_INCA'    : -82761,
    'MIMI_LEMMS1'  : -82762,
    'MIMI_LEMMS2'  : -82763,
    'RADAR_1'      : -82810,
    'RADAR_2'      : -82811,
    'RADAR_3'      : -82812,
    'RADAR_4'      : -82813,
    'RADAR_5'      : -82814,
    'RPWS'         : -82730,
    'RPWS_EXPLUS'  : -82731,
    'RPWS_EXMINUS' : -82732,
    'RPWS_EZPLUS'  : -82733,
    'RPWS_LP'      : -82734,
    'RPWS_EDIPOLE' : -82735,
    'RPWS_EXZPLANE': -82736,
    'RPWS_EXPZP'   : -82737,
    'RPWS_EXMZP'   : -82738,
    'RPWS_EDPZP'   : -82739,
}

FRAME_NAMES = {v:k for k,v in FRAME_IDS.items()}

FRAME_IDS['SC'] = FRAME_IDS['SC_COORD']     # alt name

# Add keys that are tuples (instrument, component) and then clean up
keys = list(FRAME_IDS.keys())
for key in keys:
    parts = key.partition('_')
    if parts[1] == '_':
        FRAME_IDS[parts[0], parts[2]] = FRAME_IDS[key]

del FRAME_IDS['SC', 'COORD']    # "SC_COORD" has a different use of underscore

# RSS is not in the frame names for the antennas
for key in ('HGA', 'LGA1', 'LGA2', 'XBAND', 'KABAND', 'KUBAND', 'SBAND', 'XBAND_TRUE'):
    FRAME_IDS['RSS', key] = FRAME_IDS[key]

INSTRUMENT_IDS = {k:set() for k in INSTRUMENT_NAMES}
for key, frame_id in FRAME_IDS.items():
    if key in INSTRUMENT_NAMES:
        INSTRUMENT_IDS[key].add(frame_id)
    elif isinstance(key, tuple) and key[0] in INSTRUMENT_NAMES:
        INSTRUMENT_IDS[key[0]].add(frame_id)

del frame_id,  key, keys, parts

##########################################################################################
# FKs
##########################################################################################

from ._CASSINI_FKS import _CASSINI_FKS

rule = Rule(r'cas_v(NN)\.tf', mission='CASSINI',  source=_source('FK'), dest='Cassini/FK')
KernelFile.mutual_veto(rule.pattern)

fk_source = _source('FK')
fk_source = [fk_source] + [fk_source + f'/release.{i:02d}' for i in range(1, 14)]

fk_notes = """\
    The final Cassini frames kernel is version 43.
"""

fk = spicefunc('fk', title='Cassini FK',
               known=_CASSINI_FKS,
               unknown=rule.pattern, source=fk_source,
               exclude=True,    # never more than one
               notes=fk_notes)

del rule, fk_source, fk_notes

##########################################################################################
# IKs
##########################################################################################

from ._CASSINI_IKS import _CASSINI_IKS

rule = Rule(r'cas_(?P<instrument>[a-z]+)_v(NN)\.ti', mission='CASSINI',
            instrument=str.upper, source=_source('IK'), dest='Cassini/IK')
KernelFile.veto(r'cas_([a-z]+)_v(\d\d)\.ti', r'cas_\1_v\d\d\.ti')

ik_source = _source('IK')
ik_source = [ik_source] + [ik_source + f'/release.{i:02d}' for i in range(1, 14)]

ik_notes = """\
    This function returns an Instrument Kernel object for one or more instruments.

    The last versions of these files are: CAPS=3, CDA=1, CIRS=10, INMS=2, ISS=10, MAG=1,
    MIMI=11, RADAR=11, RPWS=1, RSS=3, UVIS=7, VIMS=6.
"""

ik_docstrings = {'instrument': """\
        instrument  One or more of the Cassini instruments: "CAPS", "CDA", "CIRS", "INMS",
                    "ISS", "MAG", "MIMI", "RADAR", "RPWS", "RSS", "UVIS", or "VIMS". Use
                    None or an empty set to include all instruments.
"""}

ik = spicefunc('ik', title='Cassini IK',
               known=_CASSINI_IKS,
               unknown=rule.pattern, source=ik_source,
               exclude=('instrument',),
               notes=ik_notes, docstrings=ik_docstrings)

del rule, ik_source, ik_notes, ik_docstrings

##########################################################################################
# SCLKs
##########################################################################################

from ._CASSINI_SCLKS import _CASSINI_SCLKS

rule = Rule(r'cas(NNNNN)\.tsc', mission='CASSINI', source=_source('SCLK'),
            dest='Cassini/SCLK')
KernelFile.mutual_veto(rule.pattern)

sclk_notes = """\

    The final Cassini clock kernel is version 172. However, it differs from all prior
    clock kernels in that it corrects an error or nearly one second that appeared in
    earlier kernels. Users who which to reconstruct work that they did prior to 2018 might
    consider using version 171.
"""

sclk = spicefunc('sclk', title='Cassini SCLK',
                 known=_CASSINI_SCLKS,
                 unknown=rule.pattern, source=_source('SCLK'),
                 exclude=True,      # never more than one
                 notes=sclk_notes)

del rule, sclk_notes

##########################################################################################
# Metakernel...
##########################################################################################

def meta(planet=None, instrument=None, *, irregular=False,
         tmin=None, tmax=None, ids=None,
         ck={}, fk={}, ik={}, sclk={}, spk={}):
    """A metakernel object for the Cassini mission or any subset thereof.

    Input:
        planet      one or more of "VENUS", "EARTH", "MASURSKY", or "JUPITER", or
                    "SATURN", indicating the phase(s) of the Cassini mission that this
                    metakernel should cover. If not specified, "SATURN" is the default.
                    "ISS", "MAG", "MIMI", "RADAR", "RPWS", "RSS", "UVIS", or "VIMS". Use
                    None or an empty set to include all instruments.
        irregular   True to include Saturn's planet's irregular satellites in the SPK.
        ck, fk, ik, sclk, spk
                    optional dictionaries listing any non-default inputs to one of the
                    Cassini kernel functions of the same name.
    """

    # _meta avoids the name conflicts between ck the input and ck the function, etc.
    return _meta(planet=planet, instrument=instrument, irregular=irregular,
                 tmin=tmin, tmax=tmax, ids=ids,
                 ck_=ck, fk_=fk, ik_=ik, sclk_=sclk, spk_=spk)

def _meta(*, planet, instrument, irregular, tmin, tmax, ids,
          ck_, fk_, ik_, pck_, sclk_, spk_):

    ck_   = ck(planet=planet, instrument=instrument,
               tmin=tmin, tmax=tmax, ids=ids, **ck_)
    fk_   = fk(ids=ids, **fk_)
    ik_   = ik(instrument=instrument, ids=ids, **ik_)
    sclk_ = sclk(**sclk_)
    spk_  = spk(planet=planet, irregular=irregular,
                tmin=tmin, tmax=tmax, ids=ids, **spk_)

    return Metakernel([ck_, fk_, ik_, sclk_, spk_])

##########################################################################################
