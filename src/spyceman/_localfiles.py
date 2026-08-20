##########################################################################################
# spyceman/_localfiles.py
##########################################################################################
"""Functions to maintain information about kernel files in the local file system."""

import os
import pathlib
import warnings
import zlib

import textkernel

from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS

_ROOTS = set()  # The directory roots that have been walked, as Path objects


def walk(*directories, translator=None, override=False, missing='warn'):
    """Walk one or more directory trees and update the global dictionary of SPICE
    kernels.

    A directory tree that has already been walked is skipped. Files whose extensions are
    not recognized as SPICE kernels are ignored silently.

    Parameters:
        *directories (str, pathlib.Path): One or more local directory trees to walk. If
            none are given, the trees named by the SPICEPATH environment variable are
            walked instead.
        translator (function, optional): A function called as translator(root, basename)
            that returns either an empty string or a replacement basename. A replacement
            becomes the name by which the file is referenced. This makes it possible to
            register kernels whose real basenames are unrecognized or not unique.
        override (bool, optional): True for the most recently found file with a given
            basename to replace any earlier one; False to keep the earlier file and warn
            whenever two files share a basename but differ in content.
        missing (str, optional): What to do if no directories are given and SPICEPATH is
            undefined: "ignore" to return without walking anything, "warn" to issue a
            UserWarning and then return, or "error" to raise RuntimeError. Ignored if one
            or more directories are given. Default is "warn".

    Raises:
        RuntimeError: If no directories are given, SPICEPATH is undefined, and missing is
            "error".
        ValueError: If missing is not one of "ignore", "warn", or "error".
    """

    if not directories:
        directories = _get_spicepath(missing=missing)

    for directory in directories:
        directory = pathlib.Path(directory)
        resolved = directory.resolve()
        if resolved in _ROOTS:
            continue

        for root, _dirs, basenames in directory.walk(follow_symlinks=True):
            for basename in basenames:
                path = root / basename
                use_paths(path, translator=translator, override=override, ignore=True)

        _ROOTS.add(resolved)


def _get_spicepath(missing='warn'):
    """The list of directory trees to read as defined by the SPICEPATH environment
    variable.

    Parameters:
        missing (str, optional): What to do if SPICEPATH is undefined: "ignore" to return
            an empty list, "warn" to issue a UserWarning and return an empty list, or
            "error" to raise RuntimeError. Default is "warn". The warning is issued at
            most once per session.

    Returns:
        list[str]: The colon-separated directories named by SPICEPATH, in the order
            given. Empty entries, which a leading, trailing, or doubled colon would
            produce, are dropped rather than being read as the working directory. The
            list is empty if SPICEPATH is undefined and missing is not "error".

    Raises:
        RuntimeError: If SPICEPATH is undefined and missing is "error".
        ValueError: If missing is not one of "ignore", "warn", or "error".
    """

    if missing not in ('ignore', 'warn', 'error'):
        raise ValueError('invalid missing option: ' + repr(missing))

    if 'SPICEPATH' in os.environ:
        return [root for root in os.environ['SPICEPATH'].split(':') if root]

    if missing == 'error':
        raise RuntimeError('missing environment variable "SPICEPATH"')

    if missing == 'warn' and not _get_spicepath.warned:
        _get_spicepath.warned = True
        warnings.warn('missing environment variable "SPICEPATH"; no kernel files were '
                      'found', stacklevel=3)

    return []

_get_spicepath.warned = False   # so the "warn" option warns at most once per session


def use_path(path, newname=None, override=False, ignore=False):
    """Add this file path to the global dictionary of SPICE kernels.

    A ".txt" file is examined for a KERNELS_TO_LOAD assignment and rejected if it does
    not contain one, because that extension is not reserved for metakernels.

    Parameters:
        path (str, pathlib.Path): Path to a SPICE kernel file.
        newname (str, optional): Basename by which this file is to be referenced, in
            place of its actual name. This makes it possible to use kernels whose
            basenames would not otherwise be recognized, and to reference two different
            files that happen to share a basename.
        override (bool, optional): True for this file to replace any previously found
            file with the same basename; False to keep the earlier file and warn if the
            two differ in content.
        ignore (bool, optional): True to return silently for a file that is not
            recognized as a SPICE kernel; False to raise ValueError.

    Raises:
        FileNotFoundError: If the given path does not exist.
        ValueError: If the file is not a recognized SPICE kernel and ignore is False.
    """

    path = pathlib.Path(path)

    if not path.exists():
        raise FileNotFoundError(f'SPICE file path not found: "{path}"')

    if newname is None:
        basename = path.name
    else:
        basename = newname

    # Check the extension
    ext = '.' + basename.rpartition('.')[-1].lower()
    if ext not in _EXTENSIONS:
        if ignore:
            return
        raise ValueError(f'unrecognized SPICE kernel file extension: "{basename}"')

    # Check for a duplicated basename with different content
    abspath = str(path.resolve())
    if basename in _KernelInfo.ABSPATHS:
        old_abspath = _KernelInfo.ABSPATHS[basename]
        if old_abspath == abspath:
            return

        if override:
            _KernelInfo.replace(basename, abspath)

        else:
            # Compare checksums
            old_checksum = _file_checksum(old_abspath)
            new_checksum = _file_checksum(abspath)
            if old_checksum == new_checksum:
                return

            # Checksum mismatch might be due text kernel labeling or comments
            if ext[1] == 't':
                if _compare_tks(old_abspath, abspath):
                    return

            warnings.warn(f'duplicate basename, different content:\n'
                          f'    {path}\n'
                          f'    {old_abspath}', stacklevel=2)

        return

    # A file whose extension implies a metakernel is checked for the KERNELS_TO_LOAD
    # assignment that defines one. ".txt" is not reserved for metakernels at all, and
    # ".tm", though conventional, does not guarantee the content either.
    if _EXTENSIONS[ext] == 'META' and not _is_metakernel(abspath):

        # It's possible to create a ".txt" _KernelInfo object before it exists. If we now
        # know it's not actually a metakernel, remove it!
        defined = basename in _KernelInfo.KERNELINFO
        if defined:
            del _KernelInfo.KERNELINFO[basename]
            _KernelInfo.BASENAMES_BY_KTYPE['META'].discard(basename)

        if ignore and not defined:
            return

        raise ValueError(f'not a SPICE kernel file: "{path}"')

    # Any other file with a valid extension is a kernel
    _KernelInfo.register(basename, abspath)


def use_paths(*paths, translator=None, override=False, ignore=False):
    """Add these file paths to the global dictionary of SPICE kernels.

    Parameters:
        *paths (str, pathlib.Path): One or more paths to SPICE kernel files.
        translator (function, optional): A function called as translator(root, basename)
            that returns either an empty string or a replacement basename. A replacement
            becomes the name by which that file is referenced.
        override (bool, optional): True for each file to replace any previously found
            file with the same basename; False to keep the earlier file and warn if the
            two differ in content.
        ignore (bool, optional): True to skip files that are not recognized as SPICE
            kernels; False to raise ValueError.

    Raises:
        FileNotFoundError: If one of the given paths does not exist.
        ValueError: If a file is not a recognized SPICE kernel and ignore is False.
    """

    for path in paths:
        path = pathlib.Path(path)
        basename = None

        # Apply translator if any
        if translator:
            test = translator(path.parent, path.name)
            if test:
                basename = test

        use_path(path, newname=basename, override=override, ignore=ignore)


def _file_checksum(filepath):
    """Adler 32 checksum of a file.

    The file is read in 64 KB blocks, so its size does not constrain memory use.

    Parameters:
        filepath (str, pathlib.Path): Path to the file to be checksummed.

    Returns:
        int: The Adler 32 checksum of the file's content.
    """

    filepath = pathlib.Path(filepath)

    BLOCKSIZE = 65536
    value = 0
    with filepath.open('rb') as f:
        buffer = f.read(BLOCKSIZE)
        while buffer:
            value = zlib.adler32(buffer, value)
            buffer = f.read(BLOCKSIZE)

    return value


def _compare_tks(old_filepath, new_filepath):
    """Compare the data content of two text kernels. Can be slow.

    Only the parsed data content is compared, so two kernels that differ solely in their
    labels or comments compare as equal.

    Parameters:
        old_filepath (str, pathlib.Path): Path to the first text kernel.
        new_filepath (str, pathlib.Path): Path to the second text kernel.

    Returns:
        bool: True if the two kernels define identical data.
    """

    old_tkdict = textkernel.from_file(old_filepath)
    new_tkdict = textkernel.from_file(new_filepath)
    return old_tkdict == new_tkdict


def _is_metakernel(filepath):
    """True if this file is a metakernel.

    The test is the presence of a KERNELS_TO_LOAD assignment anywhere in the file.

    Parameters:
        filepath (str, pathlib.Path): Path to the file to examine.

    Returns:
        bool: True if the file contains a KERNELS_TO_LOAD assignment.
    """

    is_metakernel = False

    filepath = pathlib.Path(filepath)
    with filepath.open('r', encoding='latin1') as f:
        for rec in f:
            if 'KERNELS_TO_LOAD' in rec.upper():
                is_metakernel = True
                break

    return is_metakernel

##########################################################################################
