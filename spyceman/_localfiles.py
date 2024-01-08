##########################################################################################
# spyceman/_localfiles.py
##########################################################################################
"""Set of functions to maintain information about kernel files in the local file system.
"""

import os
import warnings
import zlib

import textkernel

from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS

_ROOTS = set()          # the set of directory roots that have been walked


def walk(*directories, translator=None, override=False):
    """Walk one or more directory trees and update the global dictionary of SPICE
    kernels.

    If a translator function is provided, it takes the directory path and basename as
    inputs and returns either blank or a new basename. If a new basename is provided,
    this will be the name by which the file is referenced, rather than its actual
    basename:
        new_basename = translator(root, basename)

    If override is True, then the latest file found with a given basename is the one
    used; otherwise, a warning is issued each time a kernel file is found that has
    different content but the same basename as one previously found.
    """

    for directory in directories:
        directory = os.path.abspath(os.path.realpath(directory))
        if directory in _ROOTS:
            continue

        for root, dirs, basenames in os.walk(directory, followlinks=True):
            for basename in basenames:
                path = os.path.join(root, basename)
                use_paths(path, translator=translator, override=override, ignore=True)

        _ROOTS.add(directory)


def use_path(path, newname=None, override=False, ignore=False):
    """Add this file path to the global dictionary of SPICE kernels.

    If newname is given, the _KernelInfo object will use this as its basename rather
    than the actual name. This makes it possible to use SPICE kernels with basenames
    that would not otherwise be recognized. It also makes it possible to reference
    different kernel files that happen to have the same basename.

    If override is True, then this file will override any previously found file with
    the same basename; otherwise, the previous file is used, and a a warning is issued
    if the files have different content.

    If ignore is True, then files not recognized as SPICE kernels are ignored
    silently; otherwise, a ValueError is raised.
    """

    if not os.path.exists(path):
        raise FileNotFoundError('file not found: ' + repr(path))

    abspath = os.path.abspath(os.path.realpath(path))

    if newname is None:
        basename = os.path.split(abspath)[-1]
    else:
        basename = newname

    # Check the extension
    ext = '.' + basename.rpartition('.')[-1].lower()
    if ext not in _EXTENSIONS:
        if ignore:
            return
        raise ValueError('unrecognized SPICE kernel file extension: ' + path)

    # Check for a duplicated basename with different content
    if basename in _KernelInfo.ABSPATHS:
        if not override:
            old_abspath = _KernelInfo.ABSPATHS[basename]
            if old_abspath == abspath:
                return

            # Compare checksums
            old_checksum = _file_checksum(old_abspath)
            new_checksum = _file_checksum(abspath)
            if old_checksum == new_checksum:
                return

            # Checksum mismatch might be due text kernel labeling or comments
            if ext[1] == 't':
                if _compare_tks(old_abspath, abspath):
                    return

            warnings.warn('duplicate basename, different content:\n'
                          + '    ' + path + '\n'
                          + '    ' + old_abspath)
            return

    # Check a .txt file to see if it's a metakernel
    if ext == '.txt' and not ignore and not _is_metakernel(abspath):
        raise ValueError('not a SPICE kernel file: ' + path)

    # Any other file with a valid extension is a kernel
    _KernelInfo.ABSPATHS[basename] = abspath
    ktype = _EXTENSIONS[ext]
    _KernelInfo.BASENAMES_FOR_KTYPE[ktype].add(basename)

    # If this is an override and any attributes have been defined manually, apply these
    # attributes to the new object
    if basename in _KernelInfo.KERNELINFO:
        defs = _KernelInfo.KERNELINFO[basename]._manual_defs
        del _KernelInfo.KERNELINFO[basename]
        info = _KernelInfo(basename)
        for item in defs:
            name = item[0]
            if name in info.__dict__:
                info.__dict__[name] = item[1]
            else:
                _KernelInfo.__dict__[name](info, *item[1:])


def use_paths(*paths, translator=None, override=False, ignore=False):
    """Add these file paths to the global dictionary of SPICE kernels.

    If a translator function is provided, it takes the directory path and basename as
    inputs and returns either blank or a new basename. If a new basename is returned,
    this will be the name by which the file is referenced, rather than its actual
    basename:
        alt_basename = translator(root, basename)

    If override is True, then each file will override any previously found file with
    the same basename; otherwise, the previous file is used, and a a warning is issued
    if the files have different content.

    If ignore is True, then files not recognized as SPICE kernels are ignored
    silently; otherwise, an error is raised.
    """

    for path in paths:
        abspath = os.path.abspath(path)

        # Apply translator if any
        (root, basename) = os.path.split(abspath)
        if translator:
            test = translator(root, basename)
            if test:
                basename = test

        use_path(abspath, newname=basename, override=override, ignore=ignore)


def _file_checksum(filepath):
    """Adler 32 checksum of a file."""

    BLOCKSIZE = 65536
    value = 0
    with open(filepath, 'rb') as f:
        buffer = f.read(BLOCKSIZE)
        while buffer:
            value = zlib.adler32(buffer, value)
            buffer = f.read(BLOCKSIZE)

    return value


def _compare_tks(old_filepath, new_filepath):
    """Compare the data content of two text kernels. Can be slow."""

    old_tkdict = textkernel.from_file(old_filepath)
    new_tkdict = textkernel.from_file(new_filepath)
    return old_tkdict == new_tkdict


def _is_metakernel(filepath):
    """True if this file is a metakernel."""

    is_metakernel = False
    with open(filepath, 'r', encoding='latin8') as f:
        for rec in f:
            if 'KERNELS_TO_LOAD' in rec.upper():
                is_metakernel = True
                break

    return is_metakernel

##########################################################################################
