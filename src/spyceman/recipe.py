##########################################################################################
# spyceman/recipe.py
##########################################################################################

import functools
import inspect
import re
import textkernel

from spyceman.kernelfile  import KernelFile
from spyceman.kernelstack import KernelStack
from spyceman.metakernel  import Metakernel
from spyceman.solarsystem import General
from spyceman._ktypes     import _KTYPES

_NUMBERED_NAME = re.compile(r'(.*) (\d+)')

##########################################################################################
# Hacks to allow some convenient syntax
##########################################################################################


class _class_property(property):
    """This decorator allows us to define properties of the class rather than those of an
    instance.
    """

    def __get__(self, owner_self, owner_cls):
        """Return the property from the class it is defined on.

        Parameters:
            owner_self (object): The instance through which the attribute was reached, if
                any. It is ignored, so that the class-level value is returned either way.
            owner_cls (type): The class on which the property is defined.

        Returns:
            object: Whatever the wrapped getter returns for the class.
        """

        return self.fget(owner_cls)


class _attribute_desc(property):
    """This "descriptor" class enables a Recipe attribute to be referenced as a property.

    In addition, if the attribute name is applied to the class itself, it returns the
    corresponding attribute of the currently selected Recipe.
    """

    def __init__(self, name):
        """Construct a descriptor for the named attribute.

        Parameters:
            name (str): Name of the private attribute this descriptor exposes.
        """

        self.private_name = name

    def __get__(self, obj, objtype=None):
        """Return the named attribute of a Recipe.

        Parameters:
            obj (Recipe, optional): The Recipe to read from; None when the attribute is
                reached through the class, in which case the currently selected Recipe is
                used.
            objtype (type, optional): The owning class. It is unused.

        Returns:
            object: The value of the named attribute.
        """

        if obj is None:
            obj = Recipe._RECIPES[Recipe._SELECTION]
        return getattr(obj, self.private_name)


class _recursive_attribute_desc(property):
    """This "descriptor" class works like _attribute_desc, but if a referenced attribute
    is an empty list, it returns the corresponding property of the reference object, if
    any, instead.
    """

    def __init__(self, name):
        """Construct a descriptor for the named attribute.

        Parameters:
            name (str): Name of the private attribute this descriptor exposes.
        """

        self.private_name = name

    def __get__(self, obj, objtype=None):
        """Return the named attribute, falling back on the reference Recipe.

        Where the attribute is empty, the chain of reference Recipes is followed until a
        non-empty value is found or the chain ends.

        Parameters:
            obj (Recipe, optional): The Recipe to read from; None when the attribute is
                reached through the class, in which case the currently selected Recipe is
                used.
            objtype (type, optional): The owning class. It is unused.

        Returns:
            object: The value of the named attribute, or the first non-empty value found
                among the reference Recipes.
        """

        if obj is None:
            obj = Recipe._RECIPES[Recipe._SELECTION]
        attr = getattr(obj, self.private_name)

        while not attr:
            if obj.reference is None:
                break
            obj = obj.reference
            attr = getattr(obj, self.private_name)

        return attr


class _tkdict_desc(property):
    """This "descriptor" class enables a Recipe's text_kernel dictionary to be referenced
    as a property.

    In addition, if the attribute name is applied to the class itself, it returns the
    corresponding attribute of the currently selected Recipe.
    """

    def __get__(self, obj, objtype=None):
        """Return the Recipe's text kernel dictionary, rebuilding it if it is stale.

        Parameters:
            obj (Recipe, optional): The Recipe to read from; None when the attribute is
                reached through the class, in which case the currently selected Recipe is
                used.
            objtype (type, optional): The owning class. It is unused.

        Returns:
            dict: The merged text kernel dictionary for every text kernel this Recipe
                furnishes.
        """

        if obj is None:
            obj = Recipe._RECIPES[Recipe._SELECTION]

        if obj._tkdict_count != obj._change_count:
            tkdict = {}
            for ktype in _KTYPES:
                kernels = getattr(obj, ktype)
                for kernel in kernels:
                    for basename in kernel.basenames:
                        kfile = KernelFile(basename)
                        if kfile.is_text:
                            tkdict = textkernel.from_file(kfile.abspath, tkdict=tkdict)

            obj._tkdict = tkdict
            obj._tkdict_count = obj._change_count

        return obj._tkdict


def _fix_args(rec=None, *args, **kwargs):
    """Internal function to munge input arguments depending on whether the first
    argument is a Recipe or the name of a Recipe.

    This is what lets each wrapped method be called on an instance, on a Recipe name, or
    with no Recipe at all.

    Parameters:
        rec (Recipe, str, optional): A Recipe, the name of one, or None. Anything else is
            treated as the first real argument, and the currently selected Recipe is used
            instead.
        *args: The remaining positional arguments.
        **kwargs: The keyword arguments, passed through unchanged.

    Returns:
        (Recipe, list, dict): The Recipe to operate on, the positional arguments, and the
            keyword arguments.

    """

    if isinstance(rec, Recipe):         # if first arg is a Recipe, leave it alone
        pass
    elif isinstance(rec, str) and rec in Recipe._RECIPES:
        rec = Recipe._RECIPES[rec]      # if first arg is a string, use it as a key
    else:                               # otherwise, use selected Recipe
        # In this case, rec is really the first argument
        if rec is not None:
            if args and args[0] is None:
                args = [rec] + list(args[1:])
            else:
                args = [rec] + list(args)
        rec = Recipe._RECIPES[Recipe._SELECTION]

    return (rec, args, kwargs)


def _wrap_func(funcname):
    """Create a version of the named function without its leading underscore.

    The wrapper can be applied to the Recipe class overall, to the name of a Recipe, or
    to a Recipe instance. Applied to a name, via Recipe.funcname(name, ...), it operates
    on the Recipe having that name; with the name or instance omitted entirely, it
    operates on the currently selected Recipe.

    Parameters:
        funcname (str): Name of the underscore-prefixed method to wrap.
    """

    func = getattr(Recipe, funcname)

    def wrapper(*args, **kwargs):
        """Call the wrapped method on the Recipe identified by the leading argument.

        This docstring is replaced by that of the wrapped method when
        functools.update_wrapper() runs below; it is here so that the source satisfies
        the project docstring standard.

        Parameters:
            *args: The leading argument may be the Recipe class, a Recipe name, or a
                Recipe instance, or it may be omitted to use the selected Recipe. The
                rest are passed through to the wrapped method.
            **kwargs: Passed through to the wrapped method.

        Returns:
            object: Whatever the wrapped method returns.
        """

        (rec, args, kwargs) = _fix_args(*args, **kwargs)
        return getattr(rec, funcname)(*args, **kwargs)

    # functools.wraps copies the name, docstring and module; __signature__ is what
    # inspect and help() read, so setting it makes the wrapper report the signature of
    # the method it stands in for. This replaces an earlier exec()-built definition,
    # which achieved the same visible signature but was invisible to any static tool.
    functools.update_wrapper(wrapper, func)
    wrapper.__name__ = funcname[1:]
    wrapper.__qualname__ = 'Recipe.' + funcname[1:]
    wrapper.__signature__ = inspect.signature(func)

    setattr(Recipe, funcname[1:], wrapper)


##########################################################################################
# Recipe class
##########################################################################################


class Recipe:
    """Class to manage the furnishing of Kernel objects."""

    _RECIPES = {}                       # every defined Recipe, keyed by name
    _SELECTION = 'default'              # name of the currently selected Recipe

    # We use the _attribute_desc descriptor class, defined above, instead of individual
    # @property definitions. This allows each attribute "name", "reference", etc. to be
    # referenced as a read-only property. It also allows any of these attributes to be
    # applied to the Recipe class, in which case that attribute of the currently selected
    # Recipe is returned.

    name = _attribute_desc('_name')
    reference = _attribute_desc('_reference')
    kernels = _attribute_desc('_kernels')

    # The _tkdict attribute might need to be updated prior to returning it.
    tkdict = _tkdict_desc()

    # Note: The properties for individual ktypes are defined at the end.

    ####################################################
    # Constructors
    ####################################################

    def __init__(self, name, kernels=[], reference=None, select=False):
        """Constructor for a Kernel Recipe.

        Parameters:
            name (str): Name of this Recipe, which must be unique. Trailing blanks are
                stripped.
            kernels (list, optional): Kernels to include, equivalent to calling
                append() on the new Recipe.
            reference (Recipe, str, optional): An alternative Recipe, or the name of one.
                Where this Recipe contains no Kernels of a particular ktype, the
                referenced Recipe's Kernels of that ktype are used instead.
            select (bool, optional): True to make this the currently selected Recipe.

        Raises:
            ValueError: If a Recipe of this name already exists.
        """

        name = Recipe._clean_name(name)
        if name in Recipe._RECIPES:
            raise ValueError(f'Recipe named "{name}" already exists"')

        self._name = name
        self._change_count = 0          # incremented for each modification
        self._tkdict_count = -1         # the index for the latest text kernels
        self._tkdict = None

        if isinstance(reference, str):
            reference = Recipe._RECIPES[reference]
        self._reference = reference

        self._kernels = []
        for ktype in _KTYPES:           # define an attribute for each ktype
            setattr(self, '_' + ktype, [])
        self._append(*kernels)

        if select:
            Recipe._SELECTION = name

        Recipe._RECIPES[name] = self

    def __copy__(self):
        """A deep copy of this Recipe.

        The name has a trailing digit appended or incremented to keep it unique:
        "recipe" becomes "recipe 2", "recipe 2" becomes "recipe 3", and so on.

        Returns:
            Recipe: The new Recipe.
        """

        dup = Recipe(Recipe._unused_name(self._name), reference=self._reference)
        dup._append(*self._kernels)
        return dup

    def _copy(self=None):
        """A deep copy of this Recipe.

        The name has a trailing digit appended or incremented to keep it unique:
        "recipe" becomes "recipe 2", "recipe 2" becomes "recipe 3", and so on.

        This method supports several syntax options:
            rec.copy()          a copy of `rec`, which is an instance of Recipe
            Recipe.copy(rec)    same as above
            Recipe.copy(name)   a copy of the Recipe having the given name
            Recipe.copy()       a copy of the currently selected Recipe
            Recipe.copy(None)   same as above

        Returns:
            Recipe: The new Recipe.
        """

        if self is None:
            self = Recipe._RECIPES[Recipe._SELECTION]

        return self.__copy__()

    @staticmethod
    def _clean_name(name):
        """Name with trailing blanks stripped.

        Where the name ends with a blank followed by digits, duplicate blanks before the
        digits are collapsed into one and leading zeros are removed from the digits.

        Parameters:
            name (str): The name to clean up.

        Returns:
            str: The cleaned-up name.

        Raises:
            TypeError: If the name is not a string.
        """

        if not isinstance(name, str):
            raise TypeError('invalid type for Recipe name: ' + repr(name))

        name = name.rstrip()
        match = _NUMBERED_NAME.fullmatch(name)
        if match:
            name = match.group(1).rstrip() + ' ' + str(int(match.group(2)))

        return name

    @staticmethod
    def _unused_name(name):
        """Name with an optional integer appended to make it unique.

        Trailing blanks are stripped, duplicate blanks before the digits are collapsed
        into one, and leading zeros are removed from the digits.

        Parameters:
            name (str): The name to make unique.

        Returns:
            str: A name not currently in use by any Recipe.
        """

        name = Recipe._clean_name(name)
        if name not in Recipe._RECIPES:
            return name

        match = _NUMBERED_NAME.fullmatch(name)
        if match:
            rootname_ = match.group(1).rstrip() + ' '
        else:
            rootname_ = name + ' '

        k = 2
        while (name := rootname_ + str(k)) in Recipe._RECIPES:
            k += 1

        return name

    def __str__(self):
        """A brief string representation of this Recipe.

        Returns:
            str: The word "Recipe" followed by this Recipe's name in quotes.
        """

        return 'Recipe("' + self.name + '")'

    def __repr__(self):
        """A brief string representation of this Recipe.

        Returns:
            str: The word "Recipe" followed by this Recipe's name in quotes.
        """

        return self.__str__()

    def __getstate__(self):

        # Strip any trailing digits from the name
        """The state of this Recipe, for pickling.

        Any trailing digits are stripped from the name, so that a restored Recipe is
        numbered afresh rather than colliding with an existing name.

        Returns:
            (str, list, Recipe): The Recipe's name, its kernels, and its reference
                Recipe.
        """

        match = _NUMBERED_NAME.fullmatch(self._name)
        if match:
            name = match.group(1).rstrip()
        else:
            name = self._name

        return (name, self._kernels, self._reference)

    def __setstate__(self, state):
        """Restore a Recipe from its pickled state.

        The protocol restores in place and returns nothing, so this rebuilds the instance
        rather than constructing a new Recipe.

        Parameters:
            state ((str, list, Recipe)): The name, kernels, and reference Recipe produced
                by __getstate__().
        """

        (name, kernels, reference) = state
        self._name = Recipe._unused_name(name)
        self._change_count = 0
        self._tkdict_count = -1
        self._tkdict = None
        self._reference = reference

        self._kernels = []
        for ktype in _KTYPES:
            setattr(self, '_' + ktype, [])

        self._append_or_prepend(kernels, prepend=False)
        Recipe._RECIPES[self._name] = self

    ####################################################
    # Operations on Recipes
    ####################################################

    def _rename(self=None, name=None):
        """Change the name of this Recipe.

        This method supports several syntax options:
            rec.rename(newname)             rename rec, an instance of Recipe
            Recipe.rename(rec, newname)     same as above
            Recipe.rename(name, newname)    rename the Recipe having the given name
            Recipe.rename(newname)          rename the currently selected Recipe
            Recipe.rename(None, newname)    same as above

        Parameters:
            name (str, optional): The new name.

        Raises:
            ValueError: If a Recipe of the new name already exists.
        """

        name = Recipe._clean_name(name)
        if name in Recipe._RECIPES:
            raise ValueError(f'Recipe "{name}" already exists')

        Recipe._RECIPES[name] = Recipe._RECIPES[self._name]
        del Recipe._RECIPES[self._name]

        if Recipe._SELECTION == self._name:
            Recipe._SELECTION = name

        self._name = name

    def _append(self, *kernels):
        """Append one or more Kernel objects to this Recipe.

        Appended kernels are furnished at higher precedence than those already present.

        This method supports several syntax options:
            rec.append(kernel, ...)         append to rec, an instance of Recipe
            Recipe.append(rec, kernel...)   same as above
            Recipe.append(name, kernel...)  append to the Recipe having the given name
            Recipe.append(kernel...)        append to the currently selected Recipe
            Recipe.append(None, kernel...)  same as above

        Parameters:
            *kernels (Kernel, str): The Kernel objects or kernel file basenames to
                append.
        """

        self._append_or_prepend(kernels, prepend=False)

    def _prepend(self, *kernels):
        """Pre-pend one or more Kernel objects to this Recipe.

        Prepended kernels are furnished at lower precedence than those already present.

        This method supports several syntax options:
            rec.prepend(kernel, ...)        prepend to rec, an instance of Recipe
            Recipe.prepend(rec, kernel...)  same as above
            Recipe.prepend(name, kernel...) prepend to the Recipe having the given name
            Recipe.prepend(kernel...)       prepend to the currently selected Recipe
            Recipe.prepend(None, kernel...) same as above

        Parameters:
            *kernels (Kernel, str): The Kernel objects or kernel file basenames to
                prepend.
        """

        self._append_or_prepend(kernels, prepend=True)

    def _append_or_prepend(self, kernels, prepend=False):
        """Internal method to append or prepend one or more Kernel objects to this
        Recipe.

        A kernel already present is removed from its old position first, so that it ends
        up with the precedence its new position implies. A metakernel is unpacked and its
        constituent kernels are added individually.

        Parameters:
            kernels (Kernel, str, list, tuple, set): The Kernel objects or kernel file
                basenames to add.
            prepend (bool, optional): True to prepend the kernels, furnishing them at
                lower precedence; False to append them, furnishing them at higher
                precedence.

        Raises:
            ValueError: If the Recipe would end up with more than one metakernel.
        """

        # Convert to a list of kernels
        if isinstance(kernels, (list, tuple, set)):
            kernels = list(kernels)     # a copy: reversed in place below when prepending
        else:
            kernels = [kernels]

        # This is needed to preserve the precedence among the new kernels if they are
        # being prepended rather than appended.
        if prepend:
            kernels.reverse()

        # Identify the ktype of each kernel and append or prepend
        for kernel in kernels:
            if isinstance(kernel, str):
                kernel = KernelFile(kernel)

            ktype = kernel.ktype
            if ktype == 'META':                 # handle metakernels recursively
                if self._META:
                    raise ValueError('no more than one metakernel per Recipe')
                if isinstance(kernel, KernelFile):
                    kernel = Metakernel(kernel)
                for subkernel in kernel.subkernels:
                    self._append_or_prepend(subkernel, prepend=prepend)
                self._META.append(kernel)
            else:
                attr = '_' + ktype
                ktype_list = getattr(self, attr)

                if kernel in ktype_list:        # disallow duplicates
                    ktype_list.remove(kernel)
                    self._kernels.remove(kernel)

                if prepend:
                    setattr(self, attr, [kernel] + ktype_list)
                    self._kernels = [kernel] + self._kernels
                else:
                    ktype_list.append(kernel)
                    self._kernels.append(kernel)

        self._change_count += 1

    def __iadd__(self, kernels):
        """Append one or more kernels to this Recipe.

        The syntax is "recipe += kernel" or "recipe += [kernel, kernel, ...]".

        Parameters:
            kernels (Kernel, str, list, tuple, set): The Kernel objects or kernel file
                basenames to append.

        Returns:
            Recipe: This Recipe, with the kernels appended.
        """

        self._append_or_prepend(kernels, prepend=False)
        return self

    ####################################################
    # Support for alternative Recipes
    ####################################################

    def select(rec=None):
        """Define the selected Recipe and return it.

        This method supports several syntax options:
            rec.select()            select rec, an instance of Recipe
            Recipe.select(rec)      same as above
            Recipe.select(name)     select the Recipe having the given name

        Parameters:
            rec (Recipe, str, optional): The Recipe to select, or its name; None to
                return the currently selected Recipe without changing it.

        Returns:
            Recipe: The Recipe now selected.
        """

        if rec is None:
            rec = Recipe._RECIPES[Recipe._SELECTION]
        elif isinstance(rec, str):
            rec = Recipe._RECIPES[rec]

        Recipe._SELECTION = rec._name
        return rec

    @_class_property
    def SELECTED(cls):
        """The currently selected Recipe.

        Returns:
            Recipe: The Recipe that class-level attribute access resolves against.
        """
        return Recipe._RECIPES[Recipe._SELECTION]

    @_class_property
    def SEL(cls):
        """Short name for the currently selected Recipe.

        Returns:
            Recipe: The Recipe that class-level attribute access resolves against.
        """
        return Recipe._RECIPES[Recipe._SELECTION]

    @_class_property
    def DEFAULT(cls):
        """The default Recipe.

        Returns:
            Recipe: The Recipe named "default".
        """
        return Recipe._RECIPES['default']

    @_class_property
    def DEF(cls):
        """Short name for the default Recipe.

        Returns:
            Recipe: The Recipe named "default".
        """
        return Recipe._RECIPES['default']

    @staticmethod
    def lookup(key):
        """Return the Recipe object with the specified name.

        Parameters:
            key (Recipe, str): The name of a Recipe, or a Recipe object, which is
                returned unchanged.

        Returns:
            Recipe: The Recipe having this name.

        Raises:
            KeyError: If no Recipe of this name exists.
        """

        if isinstance(key, Recipe):
            return key

        return Recipe._RECIPES[key]

    ####################################################
    # Support for furnishing kernels
    ####################################################

    def _furnish(self=None, tmin=None, tmax=None, ids=None):
        """Furnish the Kernels of this Recipe for the given range of times or NAIF IDs.

        Each ktype is furnished in turn, in the order that respects the dependencies
        between them.

        This method supports several syntax options:
            rec.furnish(...)            furnish rec, an instance of Recipe
            Recipe.furnish(rec, ...)    same as above
            Recipe.furnish(name, ...)   furnish the Recipe having the given name
            Recipe.furnish(...)         furnish the currently selected Recipe
            Recipe.furnish(None, ...)   same as above

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.
        """

        for ktype in _KTYPES:
            kernels = getattr(self, ktype)
            if not kernels:     # most Recipes carry kernels for only a few ktypes
                continue

            kstack = KernelStack(kernels, name=self._name + '_' + ktype)
            kstack.furnish(tmin=tmin, tmax=tmax, ids=ids)

    def _used(self=None, tmin=None, tmax=None, ids=None):
        """An ordered list of kernel basenames that are, or would be, used for a given
        range of times and/or a set of NAIF IDs.

        This method supports several syntax options:
            rec.used(...)               basenames used by rec, an instance of Recipe
            Recipe.used(rec, ...)       same as above
            Recipe.used(name, ...)      basenames used by the Recipe having the given
                                        name
            Recipe.used(...)            basenames used by the currently selected Recipe
            Recipe.used(None, ...)      same as above

        Parameters:
            tmin (float, str, optional): Lower time limit in seconds TDB or as a
                date-time string; None for all times.
            tmax (float, str, optional): Upper time limit in seconds TDB or as a
                date-time string; None for all times.
            ids (int, set[int], optional): A NAIF ID or set of NAIF IDs; None to ignore
                NAIF IDs.

        Returns:
            list[str]: The basenames that would be furnished, ordered by ktype and then
                by increasing precedence within each ktype.
        """

        basenames = []
        for ktype in _KTYPES:
            kernels = getattr(self, ktype)
            if not kernels:     # most Recipes carry kernels for only a few ktypes
                continue

            kstack = KernelStack(kernels, name=self._name + '_' + ktype)
            basenames += kstack.used(tmin=tmin, tmax=tmax, ids=ids)

        return basenames


# Define each ktype as a property
for ktype in _KTYPES:
    # Using the ktype as a property by itself does a recursive check of the reference
    # object if this Recipe does not contain any kernels of the ktype.
    setattr(Recipe, ktype, _recursive_attribute_desc('_' + ktype))

    # To get the Kernels of this ktype without recursion, put "local_" in front, e.g.,
    # "local_ck", "local_spk", etc.
    setattr(Recipe, 'local_' + ktype, _attribute_desc('_' + ktype))

# Define the general, underscore-free versions of key methods
_wrap_func('_append')
_wrap_func('_copy')
_wrap_func('_furnish')
_wrap_func('_prepend')
_wrap_func('_rename')
_wrap_func('_used')

# Always initialize with an empty Recipe named "default"
default = Recipe('default', [])
default += General.lsk(), General.pck()

##########################################################################################
