##########################################################################################
# spyceman/hosts/Cassini/__init__.py
##########################################################################################
"""\
spyceman.hosts.Cassini: Support for Cassini-specific kernels.

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

BODY_ID = -81

_TIME_LIMITS = {
    'VENUS'   : ('1998-04-18', '1999-06-25'),
    'EARTH'   : ('1999-08-16', '1999-09-15'),
    'MASURSKY': ('2000-01-23', '2000-01-24'),
    'JUPITER' : ('1999-08-19', '2001-03-24'),
    'SATURN'  : ('2004-01-01', '2017-09-16'),
}

_BODY_IDS = {
    'VENUS'   : {BODY_ID, 2, 299},
    'EARTH'   : {BODY_ID, 3, 301, 399},
    'MASURSKY': {BODY_ID, 2002685},
    'JUPITER' : {BODY_ID, 5, 599} + set(range(501, 517)),
    'SATURN'  : {BODY_ID} + Saturn.SYSTEM,
}

from .spk import spk
from .ck import ck


from spyceman         import CSPYCE, KernelFile, KTuple, Metakernel, Rule, spicefunc
from spyceman.planets import Jupiter, Saturn, Uranus, Neptune


from ./SPK_RECONSTRUCTED_V1 import SPK_RECONSTRUCTED_V1
from ./SPK_RECONSTRUCTED_V2 import SPK_RECONSTRUCTED_V2
from ./SPK_RECONSTRUCTED_V3 import SPK_RECONSTRUCTED_V3









def _cassini_spk_kernels():
    """Create a Kernel object with a planetary system prerequisite for each Voyager SPK.

    This cannot happen at import time because the KernelFile.walk() might not have been
    called yet.
    """

    kernels = []

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

        kernels.append(kfile)

    return kernels

spk = spicefunc('spk', title='Voyager SPKs',
                pattern=r'vgr?[12]_(jup|sat|ura|nep).*\.bsp',
                known=_voyager_spk_kernels,
                exclusions=('voyager', 'planet'),
                propnames=('voyager', 'planet'), docstrings=DOCSTRINGS)





import numpy as np
import os

import julian
import kernel
import textkernel

import .spice_support as spice


class Cassini(object):
    """An instance-free class to hold Cassini-specific parameters."""

    loaded_instruments = []

    initialized = False
    manual_cks = False
    manual_spk = False

    ######################################################################################

    @staticmethod
    def initialize(ck='', planets=None, asof=None,
                   spk='', gapfill=True,
                   mst_pck=True, irregulars=True, sclk=''):
        """Intialize the Cassini mission internals.

        After the first call, later calls to this function are ignored.

        Input:
            ck,spk      Used to specify which C and SPK kernels are used, or
                        blank for the default;
                        'none' to allow manual control of the C kernels.
            planets     A list of planets to pass to define_solar_system. None
                        or 0 means all.
            asof        Only use SPICE kernels that existed before this date;
                        None to ignore.
            gapfill     True to include gapfill CKs. False otherwise.
            mst_pck     True to include MST PCKs, which update the rotation
                        models for some of the small moons.
            irregulars  True to include the irregular satellites;
                        False otherwise.
            sclk        which SCLK to use, one of "tour" or "reconstructed". Use
                        blank for the default, "reconstructed".
        """

        if Cassini.initialized:
            return

        # Define some important paths and frames
        Body.define_solar_system(Cassini.START_TIME, Cassini.STOP_TIME,
                                 asof=asof,
                                 planets=planets,
                                 mst_pck=mst_pck,
                                 irregulars=irregulars)

        _ = oops.path.SpicePath('CASSINI', 'SATURN')

        ck = ck.lower()
        spk = spk.lower()

        Cassini.manual_cks = ck == 'none'
        Cassini.manual_spks = spk == 'none'

        if not Cassini.manual_cks:
            spice.select_saturn_ck(ck)

        if not Cassini.manual_spks:
            spice.select_saturn_spk(spk)

        spice.furnish_sclk(sclk.lower())
        spice.furnish_fk()

        Cassini.initialized = True

    #===========================================================================
    @staticmethod
    def reset():
        """Reset the internal parameters.

        Can be useful for debugging.
        """

        spice.unload_ck()
        spice.unload_spk()
        spice.unload_sclk()
        spice.unload_fk()
        spice.unload_ik()

        Cassini.loaded_instruments = []
        Cassini.initialized = False

    #===========================================================================
    @staticmethod
    def load_ck(t):
        """Ensure that the C kernels applicable at or near the given time in
        seconds TDB have been furnished and prioritized.
        """

        if not Cassini.manual_cks:
            spice.furnish_ck(t)

    #===========================================================================
    @staticmethod
    def load_cks(t0, t1):
        """Ensure that all the C kernels applicable near or within the time
        interval tdb0 to tdb1 have been furnished.
        """

        if not Cassini.manual_cks:
            spice.furnish_ck(t0, t1)

    #===========================================================================
    @staticmethod
    def load_spk(t):
        """Ensure that the SPK kernels applicable at or near the given time in
        seconds TDB have been furnished.
        """

        if not Cassini.manual_spks:
            spice.furnish_spk(t)

    #===========================================================================
    @staticmethod
    def load_spks(t0, t1):
        """Ensure that all the SPK kernels applicable near or within the time
        interval tdb0 to tdb1 have been furnished.
        """

        if not Cassini.manual_spks:
            spice.furnish_spk(t0, t1)

    ######################################################################################
    # Routines for managing the loading other kernels
    ############################################################################

    @staticmethod
    def load_instruments(instruments=[], asof=None):
        """Load the SPICE kernels and defines the basic paths and frames for
        the Cassini mission.

        It is generally only to be called once.

        Input:
            instruments an optional list of instrument names for which to load
                        frames kernels. The frames for ISS, VIMS, UVIS, and CIRS
                        are always loaded.

            asof        if this specifies a date or date-time in ISO format,
                        then only kernels that existed before the specified date
                        are used. Otherwise, the most recent versions are always
                        loaded. IGNORED.
        """

        # Furnish instruments
        for inst in instruments:
            if inst not in Cassini.loaded_instruments:
                spice.furnish_ik(inst)
                Cassini.loaded_instruments.append(inst)

    ############################################################################
    # Routines for managing text kernel information
    ############################################################################

    @staticmethod
    def spice_instrument_kernel(inst, asof=None):
        """A dictionary containing the Instrument Kernel information.

        Also furnishes it for use by the SPICE tools.

        Input:
            inst        one of "ISS", "UVIS", "VIMS", "CIRS", etc.
            asof        an optional date in the past, in ISO date or date-time
                        format. If provided, then the information provided will
                        be applicable as of that date. Otherwise, the most
                        recent information is always provided. IGNORED.

        Return:         a tuple containing:
                            the dictionary generated by textkernel.from_file()
                            the name of the kernel.
        """

        kfile = spice.selected_ik(inst)
        return (kfile.as_dict(), [kfile.name])

    #===========================================================================
    @staticmethod
    def spice_frames_kernel(asof=None):
        """A dictionary containing the Cassini Frames Kernel information.

        Also furnishes the kernels for use by the SPICE tools.

        Input:
            asof        an optional date in the past, in ISO date or date-time
                        format. If provided, then the information provided will
                        be applicable as of that date. Otherwise, the most
                        recent information is always provided. IGNORED.

        Return:         a tuple containing:
                            the dictionary generated by textkernel.from_file()
                            an ordered list of the names of the kernels
        """

        kfile = spice.selected_fk()
        return (kfile.as_dict(), [kfile.name])

    #===========================================================================
    @staticmethod
    def used_kernels(time, inst, return_all_planets=False):
        """The list of kernels associated with a Cassini observation at a
        selected range of times.
        """

        if return_all_planets:
            bodies = [1, 199, 2, 299, 3, 399, 4, 499, 5, 599, 6, 699,
                      7, 799, 8, 899]
            if time[0] >= TOUR:
                bodies += Body.SATURN_MOONS_LOADED
            else:
                bodies += Body.JUPITER_MOONS_LOADED
        else:
            if time[0] >= TOUR:
                bodies = [6, 699] + Body.SATURN_MOONS_LOADED
            else:
                bodies = [5, 599] + Body.JUPITER_MOONS_LOADED

        used = spicedb.used_basenames(time=time, bodies=bodies)

        used += [spice.selected_fk().name, spice.selected_sclk().name]

        if inst:
            used.append(spice.selected_ik(inst).name)

        if time is not None:
            if isinstance(time, (str, numbers.Real)):
                time = [time, time]

            time_tdb = []
            for tval in time:
                if isinstance(tval, str):
                    tdb = julian.tdb_from_tai(julian.tai_from_iso(tval))
                    time_tdb.append(tdb)
                else:
                    time_tdb.append(tval)

            (tmin, tmax) = time_tdb

            used += furnish_spk(tmin, tmax, usage=[])
            used += furnish_ck( tmin, tmax, usage=[])

        return used

################################################################################
