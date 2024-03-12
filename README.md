# rms-spyceman

**Spyceman** is a kernel manager for the SPICE toolkit. It enables users to select kernels based on very high-level constraints (content, release date, version number, etc.) and provides three core capabilities:

(1) It ensures that the correct set of kernels is loaded in the proper order prior to a calculation involving the toolkit, without requiring users to manage, or even know, the names of individual kernel files.

(2) If a needed file is missing, it automatically downloads it from its remote source and stores it into the user's local file system prior to loading.

(3) It enables users to switch between potentially contradictory sets of SPICE kernels at will, so that users can easily compare alternative results or assess changes.

Spyceman can support CSPYCE, SpicePy, or both simultaneously.

For a user who simply wants to use the latest version of a set of the needed SPICE kernels, the steps required are especially simple. For example, if a user plans to work with Cassini data, this is sufficient:

        from spyceman import Recipe
        from spyceman.hosts import Cassini
        from spyceman.solarsystem import Saturn
        default = Recipe.select('default')
        default += Saturn.pck(), Cassini.meta()

Subsequently, the user must simply call `Recipe.furnish(tmin, tmax)` prior to any set of calculations, where `tmin` and `tmax` are the time limits of interest; this ensures that the correct kernels are loaded for that time range.

If a user wants to compare results from different SPICE kernels, they need to define two different instances of the `Recipe` class. For example, to compare the latest versions of all Cassini kernels with those released prior to 2018,

        before = Recipe('before', Saturn.pck(), Cassini.meta(release_date='2018-01-01'))
        after  = Recipe('after',  Saturn.pck(), Cassini.meta())

Then, the user can switch between these kernels by alternately furnishing them for a given time range via:

        before.furnish(tmin, tmax)
        ...
        after.furnish(tmin, tmax)

or:

        Recipe.furnish('before', tmin, tmax)
        ...
        Recipe.furnish('after', tmin, tmax)

Note that it is never necessary to explicitly unload the mutually contradictory kernel files between these calls, as a user would have to do if managing them manually. This is all handled automatically by **Spyceman**.

At any point, the user can find out the actual set of kernel files used for a given calculation by calling `Recipe.used(name, tmin, tmax)`.

## Local Files

At startup, the user must define the environment variable **`SPICE_PATH`**, which indicates the path to one or more directories on the local file system that contain the user's current collection of kernel files. Each of these directories can be organized into arbitrary subdirectories according to the user's preferences.

If Spycemen needs to download a file from a remote source it will save it into a directory defined by the environment variable **`SPICE_DOWNLOADS`** if it exists, or else directly into the first directory identified by **`SPICE_PATH`**.

## Kernel Objects

Under the hood, all operations in Spyceman are handled by objects of class `Kernel`. The subclass `KernelFile` represents an individual kernel file. A KernelFile object can be used to retrieve almost arbitrary information about the file itself via properties. For example,

        KernelFile(name).ktype          # the kernel type, e.g., "SPK", "CK", "IK", etc.
        KernelFile(name).time           # the tuple (tmin, tmax) defining the time range
        KernelFile(name).ids            # the set of NAIF body or frame IDs defined
        KernelFile(name).release_date   # the file's release date
        KernelFile(name).exists         # True if the file exists locally

The subclass `KernelSet` represents a set of mutually compatible kernel files, such as the individual CK or SPK files for a planetary mission.

The subclass `KernelStack` represents a set of other kernel object that must be loaded in a prioritized order.

The subclass `Metakernel` represents a set of Kernel objects of different `ktypes`.

## Kernel generator functions

Each of the sub-modules of `spyceman.hosts` and `spyceman.solarsystem` has a set of functions that return kernel objects based on specified inputs. For example, `spyceman.solarsystem.Mars` has a function `spk()`, which returns a Kernel object with `ktype`=`SPK`, and `pck()`, which returns a Kernel object with `ktype`=`PCK`. Using `help()` on any module indicates what functions it contains; using `help()` on individual kernel provides details about how to use them.

More details TBD.





