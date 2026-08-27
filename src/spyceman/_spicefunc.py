##########################################################################################
# spyceman/_spicefunc.py
##########################################################################################

from spyceman._downloads import search_fancy_index
from spyceman.kernel     import Kernel
from spyceman.kernelfile import KernelFile, KTuple
from spyceman.kernelset  import KernelSet
from spyceman._utils     import _input_set, _input_list

_DOCSTRING_TEMPLATE = """\
    A Kernel object composed of one or more {TITLE} files selected based
    on name, time range, release date, or other properties.

{NOTES}\
    Parameters:
{PROPERTIES}\
        tmin (float or str, optional): Only include kernel files whose coverage extends to
            or beyond this time, expressed as a UTC date-time string or in seconds TDB.
        tmax (float or str, optional): Only include kernel files whose coverage begins at
            or before this time, expressed as a UTC date-time string or in seconds TDB.
        ids (int, set, list, or tuple, optional): Only include kernel files that overlap
            this NAIF ID or collection of NAIF IDs.
        basename (str, list, set, or tuple, optional): Only include kernel files that
            match this basename or regular expression, or one of these. Note: in this
            context, a string containing only letters, numbers, underscore, dash ("-") and
            dot (".") is treated as a literal basename rather than as a match pattern.
        version (int, str, tuple, set, or  list, optional): Only include kernel files that
            match this version. Use a set to specify multiple acceptable versions, or a
            list of two values to specify an inclusive range; in the latter case, either
            value can be None to enforce a minimum or a maximum version but not both.
        release_date (str, list, or tuple, optional): Only include kernel files consistent
            with this release date. Use a list or tuple of two date strings defining the
            earliest and latest dates to include, replacing either with None or an empty
            string to ignore that constraint. A single date is treated as the upper limit
            on the release date.
        expand (bool, optional): True to expand the list of kernel files where necessary
            to ensure that the entire time range is covered for all of the specified NAIF
            IDs. In this case, some constraints on name, version, and release date might
            be violated.
        renew (bool, optional): True to check online sources for new versions of kernel
            files.

    Returns:
        Kernel or None: A Kernel object composed of the selected kernel files; None if no
            available kernel file overlaps the specified time range or set of NAIF IDs.

    Notes:
        The returned Kernel object is not guaranteed to cover the entire time range
        `(tmin, tmax)` or to include all of the IDs specified. It is merely guaranteed
        that it will _not_ include any Kernels that do not contribute to the time range or
        IDs.
"""


def _func_template(func, *, tmin=None, tmax=None, ids=None, basename=None, version=None,
                   release_date=None, expand=False, renew=False, **properties):
    """The code shared by every kernel function that _spicefunc() generates.

    The function attributes attached by `_spicefunc()` supply the defaults, the known and
    unknown basenames, and the sort, exclusion, and requirement rules; this function
    applies the caller's constraints on top of them.

    Parameters:
        func (function): The generated function whose attributes define the behavior.
        tmin (float, str, optional): Lower time limit in seconds TDB or as a date-time
            string; None for all times.
        tmax (float, str, optional): Upper time limit in seconds TDB or as a date-time
            string; None for all times.
        ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore NAIF
            IDs.
        basename (str, list, set, tuple, optional): Only include kernel files matching
            this basename or regular expression, or one of these.
        version (int, str, tuple, set, list, optional): Only include kernel files
            matching this version; a list of two values defines an inclusive range.
        release_date (str, list, tuple, optional): Only include kernel files consistent
            with this release date; a list or tuple of two dates defines a range, and a
            single date is treated as the upper limit.
        expand (bool, optional): True to widen the selection where necessary so that the
            entire time range is covered for every specified NAIF ID, even if that
            violates the constraints on name, version, or release date.
        renew (bool, optional): True to check the online sources for kernel files that
            are not present locally.
        **properties: Additional constraints on property values. A kernel file whose
            value for a named property is not among those given is excluded.

    Returns:
        Kernel or None: A Kernel object covering the selected files: the KernelFile itself
            if only one was selected, otherwise a KernelSet. None if no available kernel
            file satisfies the constraints.
    """

    # Internal functions...

    def property_keys(keynames, defaults):
        """The set of dictionary keys compatible with user inputs.

        Parameters:
            keynames (list[str]): The property names that make up the dictionary key, in
                order. A single name means the key is that property's value; several
                names mean the key is a tuple of them.
            defaults (dict): The dictionary of default values to select keys from.

        Returns:
            set: Those keys of the defaults dictionary consistent with the property
                values the caller supplied.
        """

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
        """The set of exclusion keys to which the given KernelFile applies.

        Parameters:
            property_values (dict): Every value observed among the candidate files for
                each property named in the function's exclusion list, keyed by property
                name. Used for a file that does not define one of those properties, and
                which therefore applies to all of its values.
            kfile (KernelFile): The kernel file to characterize.

        Returns:
            set[tuple]: One tuple per combination of property values this file applies
                to, each ordered to match the function's exclusion list.
        """

        keylist = [[]]
        for name in func._EXCLUDE:
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
    for name in func._PROPNAMES:
        if name not in properties:
            properties[name] = func._DEFAULT_PROPERTIES[name]

    # Fill in default times if necessary
    if tmin is None or tmax is None:
        if func._DEFAULT_TIMES_KEY:
            keys = property_keys(func._DEFAULT_TIMES_KEY, func._DEFAULT_TIMES)
            if tmin is None:
                tmin = min(func._DEFAULT_TIMES[k][0] for k in keys)
            if tmax is None:
                tmax = max(func._DEFAULT_TIMES[k][1] for k in keys)
        elif func._DEFAULT_TIMES:
            if tmin is None:
                tmin = func._DEFAULT_TIMES[0]
            if tmax is None:
                tmax = func._DEFAULT_TIMES[1]

    # Fill in default NAIF IDs if necessary
    if not ids:
        if func._DEFAULT_IDS_KEY:
            keys = property_keys(func._DEFAULT_IDS_KEY, func._DEFAULT_IDS)
            ids = set()
            for key in keys:
                ids |= func._DEFAULT_IDS[key]
        elif func._DEFAULT_IDS:
            ids = func._DEFAULT_IDS

    # Identify all local or known files
    if not func._LOCAL:
        if func._UNKNOWN:
            basenames = set(KernelFile.find_all(func._UNKNOWN, exists=True,
                                                sort=func._SORT))
            basenames |= func._KNOWN
        else:
            basenames = func._KNOWN
        func._LOCAL = list(basenames)
        func._LOCAL.sort(key=func._SORT)

    # Renew basename list if necessary; identify ordered list of all usable basenames
    if renew:
        if not func._LOCAL_AND_REMOTE:
            basenames = set(func._LOCAL)
            for url in func._SOURCE:
                for pattern in func._UNKNOWN:
                    basenames |= set(search_fancy_index(pattern, url))
            func._LOCAL_AND_REMOTE = list(basenames)
            func._LOCAL_AND_REMOTE.sort(key=func._SORT)

        basenames = func._LOCAL_AND_REMOTE
    else:
        basenames = func._LOCAL

    # Switch from basenames to KernelFiles
    kfiles = [KernelFile(b) for b in basenames]

    # Filter based on function inputs
    kfiles = KernelFile.filter_basenames(kfiles, tmin=tmin, tmax=tmax, ids=ids,
                                         name=basename, version=version,
                                         release_date=release_date, expand=expand,
                                         reduce=func._REDUCE)

    # Apply exclusions
    if isinstance(func._EXCLUDE, (list, tuple)):

        # Create a dictionary containing all possible exclusion keys;
        property_values = {}
        for name in func._EXCLUDE:
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

            # Skip this file if every key it applies to is already covered by a
            # higher-precedence file. exclusion_keys() returns a set of keys, so the
            # test is set containment, not membership of the set as a single element.
            keys = exclusion_keys(property_values, kfile)
            if not keys <= keys_found:
                keys_found |= keys
                new_kfiles.append(kfile)

        kfiles = new_kfiles[::-1]

    elif func._EXCLUDE:
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
        result = KernelSet(kfiles, ordered=func._ORDERED)

    # Add shadows and exclusions
    result.add_shadows(func._SHADOWS)
    result.exclude(*unused_basenames)

    # Prerequisites and co-requisites
    for kernel in func._REQUIRE:
        if not isinstance(kernel, Kernel):
            kernel = kernel(version=version, basename=basename, tmin=tmin, tmax=tmax,
                            ids=ids, release_date=release_date, expand=expand,
                            renew=renew, **properties)
        if kernel is None:      # an adapter returns None when it does not apply
            continue

        result.require(kernel)

    return result


def _spicefunc(funcname, title, *, known=[], unknown=None, source=None, sort='alpha',
               exclude=False, reduce=False, ordered=False, shadows=[], require=(),
               default_times=None, default_times_key=(),
               default_ids=None, default_ids_key=(),
               default_properties={},
               notes='', docstrings={}, propnames=[]):
    """Function returning a function that returns Kernel objects based on a set of
    standardized inputs plus optional case-specific properties.

    The returned function shares a single documented signature, generated from
    _DOCSTRING_TEMPLATE, so that every kernel function in the package accepts the same
    constraints. The arguments here define which files that function chooses among and
    how it ranks and filters them.

    Parameters:
        funcname (str): Name of the generated function, e.g., "spk". It appears in the
            help message.
        title (str): A title describing these kernels for the help text, e.g.,
            "Cassini SPK".
        known (list[KTuple], list[str], optional): The known KTuples or basenames that
            the generated function can choose among.
        unknown (str, set, optional): A regular expression, or set of them, matching
            kernel basenames that are not among the known files. Any file that matches
            this pattern will be treated as a usable kernel.
        source (str, list[str], optional): A URL, or list of URLs, of online directories
            where unknown files can be found.
        sort (str, function, optional): How basenames are ordered. Use "alpha" to sort
            alphabetically, "version" to sort by version, "date" to sort by release date,
            or supply a function that maps a basename to its sort key.
        exclude (bool, str, list[str], set[str], optional): True to furnish no more than
            one file; False to allow any number. Alternatively, a property name or list
            of property names, in which case no more than one file is furnished for each
            distinct combination of those property values.
        reduce (bool, optional): True to drop any kernel file whose coverage is eclipsed
            by files later in the list.
        ordered (bool, optional): True if the known files must be furnished in the order
            given; False if they can be furnished in any order.
        shadows (list, optional): Shadow tuples (basename1, basename2, ...) such that a
            file matching the first basename takes precedence over files matching the
            subsequent ones.
        require (Kernel, function, list, tuple, optional): One or more prerequisite
            kernels. A function is called with the same inputs as the generated function.
        default_times (tuple, dict, optional): A two-element tuple giving the default
            (tmin, tmax). Alternatively, a dictionary of such tuples indexed by
            `default_times_key`.
        default_times_key (str, list[str], optional): The property names forming the
            key into the `default_times` dictionary.
        default_ids (set[int], dict, optional): The NAIF IDs to use by default.
            Alternatively, a dictionary of such sets indexed by `default_ids_key`. Note
            that there is no requirement that the returned Kernel object actually include
            all of these IDs.
        default_ids_key (str, list[str], optional): The property names forming the key
            into the `default_ids` dictionary.
        default_properties (dict, optional): The default value of each property. A
            property absent from this dictionary defaults to None.
        notes (str, optional): A fully formatted string to insert into the generated
            docstring ahead of the inputs.
        docstrings (dict, optional): The docstring text describing each property, keyed
            by property name.
        propnames (list[str], optional): The property names, in the order they should
            appear in the generated docstring. Defaults to the keys of `docstrings`.

    Returns:
        function: The generated kernel function, carrying the attributes that
            `_func_template()` reads to do its work.
    """

    def wrapper(version=None, *, tmin=None, tmax=None, ids=None, basename=None,
                release_date=None, expand=False, renew=False, **properties):
        """Return a Kernel object selected from this function's kernel files.

        This docstring is replaced below by one built from _DOCSTRING_TEMPLATE, so the
        text here is visible only to a reader of the source. The parameters must match
        that template: they are the documented public interface of every generated
        kernel function.

        Parameters:
            version (int, str, tuple, set, or list, optional): Only include kernel files
                matching this version; a list of two values defines an inclusive range.
            tmin (float or str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float or str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int or set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
            basename (str, list, set, ir tuple, optional): Only include kernel files
                matching this basename or regular expression, or one of these.
            release_date (str, list, or tuple, optional): Only include kernel files
                consistent with this release date or range of release dates.
            expand (bool, optional): True to widen the selection where necessary so that
                the entire time range is covered for every specified NAIF ID.
            renew (bool, optional): True to check the online sources for kernel files that
                are not present locally.
            **properties: Additional constraints on property values.

        Returns:
            Kernel or None: A Kernel object covering the selected files, or None if no
                available kernel satisfies the constraints.
        """

        return _func_template(wrapper, tmin=tmin, tmax=tmax, ids=ids, basename=basename,
                              version=version, release_date=release_date, expand=expand,
                              renew=renew, **properties)

    # Set info for the known kernels
    KernelFile.set_info(known)

    # Convert to a set of basenames
    known = {k.basename if isinstance(k, KTuple) else k for k in known}

    # Define the sort function. The known basenames are not ordered here: `known` is a
    # set, it is unioned with the discovered basenames in `_func_template()`, and the
    # result is sorted there using this key.
    sort = KernelFile.basename_sort_key(sort)

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

    # _DOCSTRING_TEMPLATE splices {NOTES} directly ahead of "Parameters:", so a non-empty
    # block supplies its own trailing blank line and an empty one contributes nothing.
    notes = notes.rstrip('\n') + '\n\n' if notes.strip() else ''

    property_docs = ''.join([docstrings[k] for k in propnames])
    wrapper.__doc__ = _DOCSTRING_TEMPLATE.format(TITLE=title,
                                                 PROPERTIES=property_docs,
                                                 NOTES=notes)
    wrapper.__name__ = funcname

    # Fill in function attributes to define the behavior of the kernel function
    wrapper._FUNCNAME = funcname
    wrapper._KNOWN = known
    wrapper._UNKNOWN = _input_set(unknown)
    wrapper._LOCAL = []
    wrapper._LOCAL_AND_REMOTE = []
    wrapper._SOURCE = _input_list(source)
    wrapper._SORT = sort
    wrapper._EXCLUDE = exclude
    wrapper._REDUCE = reduce
    wrapper._ORDERED = ordered
    wrapper._SHADOWS = shadows
    wrapper._REQUIRE = _input_set(require)
    wrapper._DEFAULT_TIMES = default_times or (None, None)
    wrapper._DEFAULT_TIMES_KEY = _input_list(default_times_key)
    wrapper._DEFAULT_IDS = default_ids or set()
    wrapper._DEFAULT_IDS_KEY = _input_list(default_ids_key)
    wrapper._PROPNAMES = propnames          # a list, from _input_list() above
    wrapper._DEFAULT_PROPERTIES = default_properties

    return wrapper

##########################################################################################
