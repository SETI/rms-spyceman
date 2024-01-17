##########################################################################################
# spyceman/summarizer.py
##########################################################################################
"""\
Print a Python "KTuple" definition for one or more SPICE kernel files.

Usage:
    python summarizer.py [options] <directory_or_file> [...]

Options are:
    --pattern <pattern>     file match pattern to use for filtering file names.
    --ktype <ktype>         kernel type to select: one of "PCK", "SPK", etc.
    --furnish               path(s) to one or more kernels to furnish beforehand. Note
                            that it is necessary to furnish a spacecraft clock kernel
                            before summarizing C kernels.
"""

import argparse
import fnmatch
import os
import sys
import textwrap
import traceback
import warnings

import cspyce
import julian

from spyceman             import Kernel, KernelFile
from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS


def format_time(tdb):
    """A printable string to represent this TDB time value.

    Usually Y-M-D-H-M-S format, but uses floating-point seconds TDB for dates outside the
    range of four-digit years. Also, "None" if the time is None.
    """

    if tdb is None:
        return 'None'

    tai = julian.tai_from_tdb(tdb)
    date = julian.ymdhms_format_from_tai(tai, digits=3)
    if date[4] != '-':      # if not a four-digit year
        time = str(tdb)
        if time.endswith('.000'):
            time = time[:-3]
    else:
        if date.endswith('.000'):
            date = date[:-4]
        time = "'" + date + "'"

    return time


def print_ktuple(basename):
    """Print the "KTuple" info for one KernelFile object."""

    try:
        kernel = KernelFile(basename)
        print(f"KTuple('{basename}',")

        (tdb0, tdb1) = kernel.time
        time0 = format_time(tdb0)
        time1 = format_time(tdb1)
        print(f'    {time0}, {time1},')

        naif_ids = list(kernel.naif_ids_as_found)
        if naif_ids:
            naif_ids.sort()
            textlist = [str(k) + ',' for k in naif_ids[:-1]]
            textlist.append(str(naif_ids[-1]) + '},')
            text = ' '.join(textlist)
            wrapped = textwrap.wrap(text, width=75)
            print('    {' + wrapped[0])
            for text in wrapped[1:]:
                print('     ' + text)
        else:
            print('    None,')

        release_date = kernel.release_date
        if not release_date:
            print('    None),')
        else:
            print("    '" + release_date + "'),")

    except Exception as e:
        print('Error in ' + _KernelInfo.ABSPATHS[basename] + ': ' + str(e))
        traceback.print_exc()


def summarize_kernels(paths, pattern=None, ktype=None):
    """Print "KTuple" info for each file or directory path."""

    for path in paths:
        if os.path.isdir(path):
            basenames = []
            _KernelInfo.ABSPATHS.clear()
            KernelFile.walk(path)

            if pattern is None:
                abspaths = _KernelInfo.ABSPATHS.values()
                abspaths = list(abspaths)
            else:
                keys = _KernelInfo.ABSPATHS.keys()
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
                abspaths = [_KernelInfo.ABSPATHS[k] for k in keys]

            abspaths.sort()
            for abspath in abspaths:
                (_, basename) = os.path.split(abspath)
                ext = '.' + basename.rpartition('.')[-1].lower()
                if ktype and _EXTENSIONS.get(ext, '') != ktype:
                    continue
                if ext in ('.txt', '.TXT'):
                    with open(abspath, 'r') as f:
                        text = f.read().upper()
                        if 'KERNELS_TO_LOAD' not in text:
                            continue

                basenames.append(basename)

            # Sort basenames ignoring case, putting un-suffixed names last
            basenames.sort(key=lambda name: name.upper().replace('.', '~.'))
            print('\n')
            for basename in basenames:
                print_ktuple(basename)

        else:
            KernelFile.use_path(path)
            (_, basename) = os.path.split(path)
            print_kernel(basename)

########################################

if __name__ == '__main__':

    _KernelInfo._USE_RULES           = False
    _KernelInfo._USE_DEFAULT_RULES   = False
    _KernelInfo._USE_INTERNAL_DATES  = True
    _KernelInfo._USE_TIMESTAMP_DATES = True

    # Ignore warnings
    warnings.simplefilter('ignore')

    # Define parser...
    parser = argparse.ArgumentParser(description="""\
                summarizer.py: Program to print out "KTuple" summaries containing the
                time limits, NAIF IDs, and release dates of SPICE kernel files.""")

    parser.add_argument('paths', type=str, nargs='*', default=None,
                        help='File or directory path(s).')
    parser.add_argument('-p', '--pattern', type=str, default=None,
                        help="""Optional file match pattern to use for filtering the file
                                basenames.""")
    parser.add_argument('-t', '--ktype', type=str, default=None,
                        help="""Optional ktype to select; one of "PCK", "SPK", etc.""")
    parser.add_argument('-f', '--furnish', type=str, nargs='*', default=[],
                        help="""One or more kernels to furnish beforehand; for example, a
                                spacecraft clock kernel that is needed for determining the
                                time limits of C kernels.""")

    args = parser.parse_args()

    for path in args.furnish:
        cspyce.furnsh(path)

    summarize_kernels(args.paths, pattern=args.pattern, ktype=args.ktype)

##########################################################################################

