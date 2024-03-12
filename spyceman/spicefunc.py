##########################################################################################
# spyceman/spicefunc.py
##########################################################################################

from spyceman.kernel     import Kernel
from spyceman.kernelfile import KernelFile, KTuple
from spyceman.kernelset  import KernelSet
from spyceman._utils     import _input_set, _input_list

DOCSTRING_TEMPLATE = """\
    A Kernel object composed of one or more {TITLE} files selected based
    on name, time range, release date, or other properties.

{NOTES}
    Inputs:
{PROPERTIES}\
        tmin, tmax  only include kernel files with times overlapping this time interval.
                    Express times using a UTC date-time string or in TDB seconds.
        ids         only include kernel files that overlap with this NAIF ID or
                    set/list/tuple of NAIF IDs.
        basename    only include kernel files that match this basename or regular
                    expression. Specify multiple values in a list, set, or tuple. Note:
                    in this context, a string containing only only letters, numbers,
                    underscore, dash ("-") and dot(".") is treated as a literal basename
                    rather than as a match pattern.
        version     only include kernel files that match this version. Use a set to
                    specify multiple acceptable versions. Use a list of two values to
                    specify the minimum and a maximum (inclusive) of acceptable range;
                    in this case, either value can be None to enforce a minimum or a
                    maximum version but not both.
        release_date only include kernel files consistent with this release date. Use a
                    list or tuple of two date strings defining the earliest and latest
                    dates to include. Replace either date value with None or an empty
                    string to ignore that constraint. A single date is treated as the
                    upper limit on the release date.
        expand      if True, the list of kernel files is expanded if necessary to ensure
                    that the entire time range is covered for all of the specified NAIF
                    IDs. In this case, some constraints on name, version, and release date
                    might be violated.
        renew       True to check online sources for new versions of kernel files.

    Note: If no available kernel files overlap the specified time range or set of NAIF
    IDs, this function returns None.
"""

def func_template(func, *, tmin=None, tmax=None, ids=None, basename=None, version=None,
                  release_date=None, expand=False, renew=False, **properties):

    # Internal functions...

    def property_keys(keynames, defaults):
        """The set of dictionary keys compatible with user inputs."""

        keys = set(defaults.keys())
        for i, name in enumerate(keynames):
            value = properties[name]
            valset = _input_set(value)
            if not valset:
                continue
            if len(keynames) == 1:
                keys = {k for k in keys if k in valset}
            else:
                keys = {k for k in keys if k[i] in valset}

        return keys

    def exclusion_keys(property_values, kfile):
        """The set of exclusion keys to which the given KernelFile applies."""

        keylist = [[]]
        for name in func.EXCLUDE:
            options = kfile.properties.get(name, property_values[name])
            if options is None:
                options = property_values[name]
            if not isinstance(options, set):
                options = {options}

            new_keylist = []
            for option in options:
                new_keylist += [k + [option] for k in keylist]
            keylist = new_keylist

        return {tuple(x) for x in keylist}

    #### Begin active code

    # Fill in default property values
    for name in func.PROPNAMES:
        if name not in properties:
            properties[name] = func.DEFAULT_PROPERTIES[name]

    # Fill in default times if necessary
    if tmin is None or tmax is None:
        if func.DEFAULT_TIMES_KEY:
            keys = property_keys(func.DEFAULT_TIMES_KEY, func.DEFAULT_TIMES)
            if tmin is None:
                tmin = min(func.DEFAULT_TIMES[k][0] for k in keys)
            if tmax is None:
                tmax = min(func.DEFAULT_TIMES[k][1] for k in keys)
        elif func.DEFAULT_TIMES:
            if tmin is None:
                tmin = func.DEFAULT_TIMES[0]
            if tmax is None:
                tmax = func.DEFAULT_TIMES[1]

    # Fill in default NAIF IDs if necessary
    if not ids:
        if func.DEFAULT_IDS_KEY:
            keys = property_keys(func.DEFAULT_IDS_KEY, func.DEFAULT_IDS)
            ids = set()
            for key in keys:
                ids |= func.DEFAULT_IDS[key]
        elif func.DEFAULT_IDS:
            ids = func.DEFAULT_IDS

    # Identify all local or known files
    if not func.LOCAL:
        if func.UNKNOWN:
            basenames = set(KernelFile.find_all(func.UNKNOWN, exists=True,
                                                sort=func.SORT))
            basenames |= func.KNOWN
        else:
            basenames = func.KNOWN
        func.LOCALS = list(basenames)
        func.LOCALS.sort(key=func.SORT)

    # Renew basename list if necessary; identify ordered list of all usable basenames
    if renew:
        if not func.LOCAL_AND_REMOTE:
            basenames = set(func.LOCALS)
            for url in func.SOURCE:
                for pattern in func.UNKNOWN:
                    basenames |= set(KernelFile.search_fancy_index(pattern, url))
            func.LOCAL_AND_REMOTE = list(basenames)
            func.LOCAL_AND_REMOTE.sort(key=func.SORT)

        basenames = func.LOCAL_AND_REMOTE
    else:
        basenames = func.LOCAL

    # Switch from basenames to KernelFiles
    kfiles = [KernelFile(b) for b in basenames]

    # Filter based on function inputs
    kfiles = KernelFile.filter_basenames(kfiles, tmin=tmin, tmax=tmax, ids=ids,
                                         name=basename, version=version,
                                         release_date=release_date, expand=expand,
                                         reduce=func.REDUCE)

    # Apply exclusions
    if isinstance(func.EXCLUDE, (list, tuple)):

        # Create a dictionary containing all possible exclusion keys;
        property_values = {}
        for name in func.EXCLUDE:
            property_values[name] = set()
            for kfile in kfiles:
                value = kfile.properties.get(name, set())
                if isinstance(value, set):
                    property_values[name] |= value
                else:
                    property_values[name].add(value)

        # For each kernel starting from highest precedence...
        keys_found = set()
        new_kfiles = []
        for kfile in kfiles[::-1]:

            # If all the exclusion keys were already found, skip
            keys = exclusion_keys(property_values, kfile)
            if not (keys in keys_found):
                keys_found |= keys
                new_kfiles.append(kfile)

        kfiles = new_kfiles[::-1]

    elif func.EXCLUDE:
        if kfiles:
            kfiles = kfiles[-1:]

    # Identify unused basenames
    unused_basenames = set(basenames) - {k.basename for k in kfiles}

    # Construct the kernel
    if not kfiles:
        return None

    if len(kfiles) == 1:
        result = kfiles[-1]
    else:
        result = KernelSet(kfiles, ordered=func.ORDERED)

    # Add shadows and exclusions
    result.add_shadows(func.SHADOWS)
    result.exclude(unused_basenames)

    # Prerequisites and co-requisites
    for kernel in func.REQUIRE:
        if not isinstance(kernel, Kernel):
            kernel = kernel(version=version, basename=basename, tmin=tmin, tmax=tmax,
                            ids=ids, release_date=release_date, expand=expand,
                            renew=renew, **properties)
        result.require(kernel)

    return result


def spicefunc(funcname, title, *, known=[], unknown=None, source=None, sort='alpha',
              exclude=False, reduce=False, ordered=False, shadows=[], require=(),
              default_times=None, default_time_key=(),
              default_ids=None, default_id_key=(),
              default_properties={},
              notes='', docstrings={}, propnames=[]):
    """Function returning a function that returns Kernel objects based on a set of
    standardized inputs plus option case-specific properties.

    Inputs:
        funcname    name of the function, e.g., "spk". Appears in the help message.
        title       optional title string describing the kernels, to appear in the help
                    info, e.g., "Cassini SPK".
        known       list of known KTuples or basenames that can be used.
        unknown     optional regular expression that will match new kernel basenames.
        source      an online directory URL where unknown files can be found; alternately,
                    a list of one or more source URLS.
        sort        an indication of how file basenames are sorted. Use "alpha" for an
                    alphabetical sort, "version" for a version sort, "date" to sort by
                    release date, or provide a function that receives a file basename and
                    returns its sort key.
        exclude     True to prevent more than one file from being furnished; False to
                    allow any number of files to be furnished. Alternatively, as property
                    name or list of property names in which case no more than one file
                    will be furnished for each unique set of these properties.
        reduce      If True, any kernel files whose coverage is eclipsed by kernel files
                    later in the list will be eliminated from the returned Kernel object.
        ordered     True if the known files must be furnished in the order given; False if
                    they can be furnished in any order.
        shadows     optional list of shadow tuples (basename1, basename2, ...] for this
                    kernel such that any file matching the first basename will have a
                    higher precedence than any files matching subsequent basenames.
        require     one or more prerequisite kernels for this kernel. If a function is
                    provided, that function is called using all the same inputs as this
                    function.
        default_times       a two-element tuple of default values for (tmin, tmax).
                            Alternatively, a dictionary of tuples keyed by the
                            default_time_key.
        default_times_key   list of property names used as indices into the default_times
                            dictionary key.
        default_ids         the set of NAIF IDs to use by default. Alternatively, a
                            dictionary of sets using the default_id_key.
        default_ids_key     list of property names used as indices into the default_ids
                            dictionary key.
        default_properties  a dictionary of the default value for each property; property
                            names not included have a default value of None.
        notes       optional, fully-formatted string to insert into the docstring
                    before the inputs.
        docstrings  a dictionary of docstring definitions of parameters, keyed by
                    the property names.
        propnames   ordered list of property names.
    """

    def wrapper(version=None, *, tmin=None, tmax=None, ids=None, dates=None,
                expand=False, download=True, verbose=True, **properties):
        return func_template(wrapper, tmin=tmin, tmax=tmax, ids=ids,
                             dates=dates, version=version, expand=expand, **properties)

    # Set info for the known kernels
    KernelFile.set_info(known)

    # Convert to a set of basenames
    known = {k.basename if isinstance(k, KTuple) else k for k in known}

    # Define sort function, sort known basenames
    sort = KernelFile.basename_sort_key(sort)
    sorted = list(known)
    sorted.sort(key=sort)

    # Define properties and defaults
    propnames = _input_list(propnames)
    if not propnames and docstrings:
        propnames = list(docstrings.keys())

    if not default_properties:
        default_properties = {}

    for propname in propnames:
        if propname not in default_properties:
            default_properties[propname] = None

    # Exclude must be True, False, or an ordered list of property names
    if isinstance(exclude, str):
        exclude = [exclude]
    elif isinstance(exclude, set):
        exclude = list(exclude)

    # Annotate the function
    if title and not title.endswith(' '):
        title = title + ' '

    if isinstance(propnames, (list,tuple)):
        wrapper.PROPNAMES = propnames
    else:
        wrapper.PROPNAMES = [propnames]

    property_docs = ''.join([docstrings[k] for k in wrapper.PROPNAMES])
    wrapper.__doc__ = DOCSTRING_TEMPLATE.format(TITLE=title,
                                                PROPERTIES=property_docs,
                                                NOTES=wrapper.NOTES)
    wrapper.__name__ = funcname

    # Fill in function attributes to define the behavior of the kernel function
    wrapper.FUNCNAME = funcname

    wrapper.KNOWN = known
    wrapper.UNKNOWN = _input_set(unknown)
    wrapper.LOCAL = []
    wrapper.LOCAL_AND_REMOTE = []

    wrapper.SOURCE = _input_list(source)
    wrapper.SORT = sort
    wrapper.EXCLUDE = exclude
    wrapper.ORDERED = ordered
    wrapper.SHADOWS = shadows
    wrapper.REQUIRE = _input_set(require)
    wrapper.DEFAULT_TIMES = default_times or (None, None)
    wrapper.DEFAULT_TIME_KEY = _input_list(default_time_key)
    wrapper.DEFAULT_IDS = default_ids or set()
    wrapper.DEFAULT_ID_KEY = _input_list(default_id_key)
    wrapper.PROPNAMES = propnames
    wrapper.DEFAULT_PROPERTIES = default_properties

    return wrapper

##########################################################################################
