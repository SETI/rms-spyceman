##########################################################################################
# spyceman/maker.py
##########################################################################################

from spyceman.kernelfile import KernelFile
from spyceman.kernelset  import KernelSet

# This function executes once, the first time the function() is called.
# Note that it makes use of attributes attached to the function itself.

DOCSTRING_TEMPLATE = """\
    A Kernel object composed of one or more {TITLE} files selected based on
    name, time range, release date, or other properties.

{NOTES}
    Inputs:
{PROPERTIES}\
        name        select one or more {TITLE} files by name:
                    - a single basename or version number for that pre-defined Kernel
                      object;
                    - "latest" for the default Kernel object;
                    - a regular expression to filter the available kernel basenames and
                      return a new KernelSet;
                    - a tuple of one or more regular expressions or basenames, which will
                      be used to define and return a new KernelSet. Note: in this
                      context, a string containing only only letters, digits, underscore,
                      dash, and dot is treated as a literal basename rather than a regular
                      expression.
        tmin, tmax  only include kernel files with times overlapping this time interval,
                    specified in TDB seconds.
        ids         only include kernel files that refer to one or more of these NAIF IDs.
        dates       only include kernel files released within this range of dates. Use a
                    a tuple of two date strings defining the earliest and latest dates to
                    include. Replace either date value with None or an empty string to
                    ignore that constraint. A single date is treated as the upper limit on
                    the release date.
        versions    only include kernel files within this range of versions. Use a tuple
                    of two version numbers defining the minimum and maximum (inclusive) to
                    be included. Replace either value with None to ignore that constraint.
                    A single version number is treated as the upper limit.
        expand      if True, the returned list of basenames is expanded if necessary to
                    ensure that all of the specified NAIF IDs are covered for the entire
                    time range tmin to tmax. In this case, some constraints on the name,
                    release date, and version might be violated.
"""

# This is the template for a kernel-generator function. It allows the same function to be
# used for LSKs, PCKs, DE SPKs, Mars, Jupiter, etc. It is "wrapped" by the function below,
# make_func, so that each version of the function has its own attributes defining PATTERN,
# INFO, EXTRAS, etc.

def func_template(func, name=None, *, tmin=None, tmax=None, ids=None, dates=None,
                        versions=None, expand=False, **properties):

    # Make sure everything is initialized
    if not func.INITIALIZED:
        _initialize(func)

    # Use "latest" if all inputs are defaults
    if (all(x is None for x in (name, tmin, tmax, ids, dates, versions))
        and all(v is None for v in properties.values())):
            name = 'latest'

    # Retrieve a pre-defined kernel option if defined by name or version
    selected = None
    try:
        selected = func.OPTIONS[name]
        name = None
    except (KeyError, TypeError):
        pass

    if selected is None:
        try:
            selected = func.OPTIONS[versions]
            versions = None
        except (KeyError, TypeError):
            pass


    if not isinstance(known, (list,tuple)):
        known = [known]

    for x in known:
        if hasattr(x, '__call__'):

        if isinstance(x, Kernel):

        if isinstance(x, KTuple):

        if isinstance(x, str):





    # Use this list of basenames as a starting point, allowing for other constraints
    if selected:
        basenames = selected.get_basenames()
    else:
        basenames = func.BASENAMES

    # Filter basenames based on given attributes
    basenames = KernelFile.filter_basenames(basenames, name=name, tmin=tmin, tmax=tmax,
                                            ids=ids, dates=dates, versions=versions,
                                            expand=expand, reduce=True,
                                            **properties)

    if not basenames:
        raise ValueError(f'No {func.TITLE} files match the constraints')

    # If the basename list is unchanged, use the kernel originally selected
    if selected and set(selected.get_basenames()) == set(basenames):
        return selected

    # Otherwise, return a new Kernel object
    return KernelSet(basenames, ordered=func.ordered)


def spicefunc(funcname, pattern, *, tuples, extras, exclusive, reduce, bodies=set(),
              title='', propnames=[], docstrings={}, notes='',
              basenames=None, use_alts=True, missing='warn'):
    """
    Inputs:
        funcname    name of the function, e.g., "spk". Appears in the help message.
        pattern     regular expression for the basenames as a string or re.Pattern.
        title       optional title string describing the kernels, to appear in the help
                    info, e.g., "Cassini".
        tuples      list of KTuples or basenames.
        extras      list of KTuples or basenames to be treated as special-purpose only.
        exclusive   True if all the file basenames should be exclusive of one another.
        bodies      set of NAIF IDs, needed if exclusive is False to determine what is the
                    minimum set of kernels.
        propnames   optional list of property names for added input options.
        docstrings  a dictionary of docstring definitions of parameters, keyed by the
                    property names.
        basenames   optional list of basenames to use in place of the pattern.
        use_alts    True to use files identified by pattern in addition to those listed
                    by basename; False to use basenames only. Ignored if no basenames are
                    provided.
        missing     How to handle missing files.
    """

    def wrapper(name=None, tmin=None, tmax=None, ids=None, dates=None,
                versions=None, expand=False, **properties):
        return func_template(wrapper, name=name, tmin=tmin, tmax=tmax, ids=ids,
                             dates=dates, versions=versions, expand=expand, **properties)

    wrapper.INITIALIZED = False
    wrapper.FUNCNAME = funcname
    wrapper.PATTERN = re.compile(pattern)
    wrapper.INFO = info
    wrapper.EXTRAS = extras
    wrapper.EXCLUSIVE = exclusive
    wrapper.BODIES = bodies
    wrapper.BASENAMES = basenames
    wrapper.NOTES = notes

    if title and not title.endswith(' '):
        title = title + ' '
    wrapper.TITLE = title

    if isinstance(propnames, (list,tuple)):
        wrapper.PROPNAMES = propnames
    else:
        wrapper.PROPNAMES = [propnames]

    property_docs = ''.join([docstrings[k] for k in wrapper.PROPNAMES])
    wrapper.__doc__ = DOCSTRING_TEMPLATE.format(TITLE=wrapper.TITLE,
                                                PROPERTIES=property_docs,
                                                NOTES=wrapper.NOTES)
    wrapper.__name__ = funcname

    return wrapper


def _initialize(func):

    KernelFile.initialize()

    if func.INITIALIZED:
        return

    # In the list of known basenames, those in EXTRAS occur before those in INFO to ensure
    # that they never take precedence.
    merged = func.EXTRAS + func.INFO

    # Define the known kernels
    ktuples = [k for k in merged if not isinstance(k, str)]
    load_ktuples(ktuples)
    known_basenames = [k if isinstance(k,str) else k.basename for k in merged]

    # Identify the local kernels
    if not func.BASENAMES:
        func.BASENAMES = KernelFile.find_all(func.PATTERN, order=known_basenames)
            # order=known_basenames ensures the order of file names in BASENAMES matches
            # the order in INFO, so if INFO is in priority order, BASENAMES will be too.

    if not func.BASENAMES:
        raise RuntimeError(f'No {func.TITLE} files found matching pattern '
                           + repr(func.PATTERN))

    # Apply exclusion; define "latest"
    latest = None
    if func.EXCLUSIVE:
        KernelFile.exclude_basenames(func.BASENAMES)
        latest = KernelFile(func.BASENAMES[-1])
    else:
        latest = KernelSet(func.BASENAMES, ordered=True, reduce=True,
                           naif_ids=func.BODIES)
        basenames = latest.get_basenames()
        if len(basenames) == 1:
            latest = KernelFile(basenames[0])

    func.OPTIONS = {'latest': latest}
        # This is the default version of the kernel. It will always use the latest
        # available kernel files for any time, any NAIF ID. If it is None here, it will be
        # be replaced below.

    # Add KernelFiles keyed by basename to the OPTIONS dictionary
    for basename in func.BASENAMES:
        kernel = KernelFile(basename)
        func.OPTIONS[basename] = kernel

        # Also key by altnames
        for altname in kernel.altnames:
            func.OPTIONS[altname] = kernel

    # Create KernelSets for any kernel versions that are spread across multiple files
    vdict = {}
    for basename in func.BASENAMES:
        version = KernelFile(basename).version
        vdict.setdefault(version, []).append(basename)

    for version, basenames in vdict.items():
        if len(basenames) == 1:     # With only one file, reuse the KernelFile
            func.OPTIONS[version] = func.OPTIONS[basenames[0]]
        elif not func.EXCLUSIVE:
            func.OPTIONS[version] = KernelSet(basenames, ordered=True)

    func.INITIALIZED = True

##########################################################################################
