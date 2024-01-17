##########################################################################################
# spyceman/recipe.py
##########################################################################################

import inspect
import textkernel

from spyceman.kernelfile  import KernelFile
from spyceman.kernelstack import KernelStack
from spyceman.metakernel  import Metakernel
from spyceman._ktypes     import _KTYPES

import re
_NUMBERED_NAME = re.compile(r'(.*) (\d+)')

##########################################################################################
# Hacks to allow some convenient syntax
##########################################################################################

class _class_property(property):
    """This decorator allows us to define properties of the class rather than those of an
    instance."""

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)

class _attribute_desc(property):
    """This "descriptor" class enables a Recipe attribute to be referenced as a property.

    In addition, if the attribute name is applied to the class itself, it returns the
    corresponding attribute of the currently selected Recipe.
    """

    def __init__(self, name):
        self.private_name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            obj = Recipe.RECIPES[Recipe._SELECTION]
        return getattr(obj, self.private_name)

class _recursive_attribute_desc(property):
    """This "descriptor" class works like _attribute_desc, but if a referenced attribute
    is an empty list, it returns the corresponding property of the reference object, if
    any, instead.
    """

    def __init__(self, name):
        self.private_name = name

    def __get__(self, obj, objtype=None):
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
        if obj is None:
            obj = Recipe._RECIPES[Recipe._SELECTION]

        if obj._tkdict_count != obj._change_count:
            tkdict = {}
            for ktype in _KTYPES:
                kernels = getattr(self, ktype)
                for kernel in kernels:
                    for basename in kernel.get_basenames():
                        kfile = KernelFile(basename)
                        if kfile.is_text:
                            tkdict = textkernel.from_file(kfile.abspath, tkdict=tkdict)

            obj._tkdict = tkdict
            obj._tkdict_count = obj._change_count

        return obj._tkdict

def _fix_args(rec=None, *args, **kwargs):
    """Internal function to munge input arguments depending on whether the first argument
    is a Recipe or the name of a Recipe.
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
    """Create a version of the named function without an underscore, which can apply to
    the Recipe class overall or to the name of a Recipe in addition to an instance of
    Recipe. If the function is applied to the name of a Recipe, via
        Recipe.funcname(name, ...)
    it is applied to the Recipe having that name. If the name or instance is missing
    entirely, it applies to to the currently selected Recipe.
    """

    def fix_signature(sig):
        """Signature suitable for input to _fix_args.

        "(self, *, name=None)" -> "(self, name=name)"
        "(self, name=None)" -> "(self, name)"
        """

        args = []
        before, _, after = sig.partition('*,')

        before = before.split(',')
        for arg in before:
            arg = arg.strip()
            if arg:
                name = arg.partition('=')[0].strip()
                args.append(name)

        after = after.split(',')
        for arg in after:
            arg = arg.strip()
            if arg:
                name = arg.partition('=')[0].strip()
                args.append(name + '=' + name)

        return ', '.join(args).rstrip(')') + ')'

    # Define the function via exec(). This is the only way to ensure that the call
    # signature appearing in
    #   help(name)
    # will be correct.
    func = getattr(Recipe, funcname)
    sig = str(inspect.signature(func))
    code = ('def ' + funcname[1:] + sig + ': \n'
            + '    (rec, args, kwargs) = _fix_args' + fix_signature(sig) + '\n'
            + '    return rec.' + funcname + '(*args, **kwargs)\n')
    exec(code)
    exec('Recipe.' + funcname[1:] + ' = ' + funcname[1:] + '\n')

    wrapped = getattr(Recipe, funcname[1:])
    wrapped.__doc__ = func.__doc__
    wrapped.__defaults__ = func.__defaults__
    wrapped.__kwdefaults__ = func.__kwdefaults__
    wrapped.__annotations__ = func.__annotations__

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

        Inputs:
            name        name of this Recipe, which must be unique. Trailing blanks are
                        stripped.
            kernels     optional list of kernels to include, equivalent to:
                            Kernel(name).append(*kernels)
            reference   optional alternative Recipe or Recipe name. When this Recipe
                        does not contain any Kernels of a particular ktype, the
                        corresponding Kernels of the referenced Recipe's ktype are used
                        instead.
            select      True to make this the currently selected Recipe.
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

        The name will have a trailing digit appended or incremented to make it unique:
            "recipe"   -> "recipe 2"
            "recipe 2" -> "recipe 3"
            etc.
        """

        dup = Recipe(Recipe._unused_name(self._name), reference=self._reference)
        dup._append(list(self._kernels))
        return dup

    def _copy(self=None):
        """A deep copy of this Recipe.

        The name will have a trailing digit appended or incremented to make it unique:
            "recipe"   -> "recipe 2"
            "recipe 2" -> "recipe 3"
            etc.

        This method supports a variety of syntax options:
            rec.copy()          # a copy of rec, which is an instance of Recipe
            Recipe.copy(rec)    # same as above
            Recipe.copy(name)   # a copy of the Recipe having the given name
            Recipe.copy()       # a copy of the currently selected Recipe
            Recipe.copy(None)   # same as above
        """

        return self.__copy__()

    @staticmethod
    def _clean_name(name):
        """Name with trailing blanks stripped. If it ends with a blank followed by digits,
        duplicate blanks before the digits are collapsed into one and leading zeros are
        removed from the digits.
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
        """Name with optional integer appended to make it unique.

        Trailing blanks are stripped. Duplicate blanks before the digits are collapsed
        into one. Leading zeros are removed from the digits.
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
        while rootname_ + str(k) in Recipe._RECIPES:
            k += 1

        return rootname_ + str(k)

    def __str__(self):
        return 'Recipe("' + self.name + '")'

    def __repr__(self):
        return self.__str__()

    def __getstate__(self):

        # Strip any trailing digits from the name
        match = _NUMBERED_NAME.fullmatch(self._name)
        if match:
            name = match.group(1).rstrip()
        else:
            name = self._name

        return (name, self._kernels, self._reference)

    def __setstate__(state):
        (name, kernels, reference) = state
        return Recipe(Recipe._unused_name(name), kernels=kernels, reference=reference)

    ####################################################
    # Operations on Recipes
    ####################################################

    def _rename(self=None, name=None):
        """Change the name of this Recipe.

        This method supports a variety of syntax options:
            rec.rename(newname)             # change the name of rec, which is an instance
                                            # of Recipe, to newname
            Recipe.rename(rec, newname)     # same as above
            Recipe.rename(name, newname)    # rename the Recipe having name to newname
            Recipe.rename(newname)          # rename the currently selected Recipe
            Recipe.rename(None, newname)    # same as above
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

        This method supports a variety of syntax options:
            rec.append(kernel, ...)         # append kernel(s) to rec, which is an
                                            # instance of Recipe
            Recipe.append(rec, kernel...)   # same as above
            Recipe.append(name, kernel...)  # append kernel(s) to the Recipe having name
            Recipe.append(kernel...)        # append kernel(s) to the selected Recipe
            Recipe.append(None, kernel...)  # same as above
        """

        self._append_or_prepend(kernels, prepend=False)

    def _prepend(self, *kernels):
        """Pre-pend one or more Kernel objects to this Recipe.

        This method supports a variety of syntax options:
            rec.prepend(kernel, ...)        # prepend kernel(s) to rec, which is an
                                            # instance of Recipe
            Recipe.prepend(rec, kernel...)  # same as above
            Recipe.prepend(name, kernel...) # prepend kernel(s) to the Recipe with name
            Recipe.prepend(kernel...)       # prepend kernel(s) to the selected Recipe
            Recipe.prepend(None, kernel...) # same as above
        """

        self._append_or_prepend(kernels, prepend=True)

    def _append_or_prepend(self, kernels, prepend=False):
        """Internal method to append or prepend a list containing one or more Kernel
        objects to this Recipe.

        If prepend is True, the kernels will be prepended, meaning that they will be
        furnished at a lower precedence. If False, they will be furnished at a higher
        precedence.
        """

        # Convert to a list of kernels
        if isinstance(kernels, (tuple, set)):
            kernels = list(kernels)
        elif not isinstance(kernels, list):
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
                if len(self._local_meta) > 0:
                    raise ValueError('no more than one metakernel per Recipe')
                if isinstance(kernel, KernelFile):
                    kernel = Metakernel(kernel)
                for subkernel in kernel.subkernels:
                    Recipe._append_or_prepend(subkernel, prepend=prepend)
                self._meta.append(kernel)
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
        """Append one or more kernels to this kernel.

        Syntax is:
                recipe += kernel
        or
                recipe += [kernel, kernel, ...]
        """

        self._append(kernels)
        return self

    ####################################################
    # Support for alternative Recipes
    ####################################################

    def select(rec=None):
        """Define the selected Recipe and return it.

        This method supports a variety of syntax options:
            rec.select()            # select rec, which is an instance of Recipe
            Recipe.select(rec)      # same as above
            Recipe.select(name)     # select the Recipe having the given name
        """

        if rec is None:
            rec = Recipe._RECIPES[Recipe._SELECTION]
        elif isinstance(rec, str):
            rec = Recipe._RECIPES[rec]

        Recipe._SELECTION = rec._name
        return rec

    @_class_property
    def SELECTED(cls):
        """The currently selected Recipe."""
        return Recipe._RECIPES[Recipe._SELECTION]

    @_class_property
    def SEL(cls):
        """Short name for the currently selected Recipe."""
        return Recipe._RECIPES[Recipe._SELECTION]

    @_class_property
    def DEFAULT(cls):
        """The default Recipe."""
        return Recipe._RECIPES['default']

    @_class_property
    def DEF(cls):
        """Short name for the default Recipe."""
        return Recipe._RECIPES['default']

    @staticmethod
    def lookup(key):
        """Return the Recipe object with the specified name.

        If the input argument is already a Recipe object, it is returned.
        """

        if isinstance(key, Recipe):
            return key

        return Recipe._RECIPES[key]

    ####################################################
    # Support for furnishing kernels
    ####################################################

    def _furnish(self, tmin=None, tmax=None, ids=None):
        """Furnish the Kernels of this Recipe for the given range of times or NAIF IDs.

        This method supports a variety of syntax options:
            rec.furnish(...)            # furnish rec, which is an instance of Recipe
            Recipe.furnish(rec, ...)    # same as above
            Recipe.furnish(name, ...)   # furnish the Recipe having the given name
            Recipe.furnish(...)         # furnish the currently selected Recipe
            Recipe.furnish(None, ...)   # same as above

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            time        alternative time input as a tuple (tmin,tmax).
            ids         NAIF ID or set of NAIF IDs.
        """

        for ktype in _KTYPES:
            kernels = getattr(self, ktype)
            kstack = KernelStack(self._name + '_' + ktype, *kernels)
            kstack.furnish(tmin=tmin, tmax=tmax, ids=ids)

    def _used(self, tmin=None, tmax=None, ids=None):
        """An ordered list of kernel basenames that are, or would be, used for a given
        range of times and/or a set of NAIF IDs.

        This method supports a variety of syntax options:
            rec.used(...)               # basenames used by rec, which is an instance of
                                        # Recipe
            Recipe.used(rec, ...)       # same as above
            Recipe.used(name, ...)      # basenames used by the Recipe having the given
                                        # name
            Recipe.used(...)            # basenames used by the currently selected Recipe
            Recipe.used(None, ...)      # same as above

        Input:
            tmin        lower time limit in seconds TDB; None for all times.
            tmax        upper time limit in seconds TDB; None for all times.
            time        alternative time input as a tuple (tmin,tmax).
            ids         NAIF ID or set of NAIF IDs.
        """

        basenames = []
        for ktype in _KTYPES:
            kernels = getattr(self, ktype)
            kstack = KernelStack(self._name + '_' + ktype, *kernels)
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
_ = Recipe('default', [])

##########################################################################################
