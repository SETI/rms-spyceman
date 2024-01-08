################################################################################
# planets/summarize_kernels.py
#
# Print a Python "KTuple" definition for one or more SPICE kernel files.
#
# Usage:
#  python summarize_kernels.py [options] <directory_or_file> [...]
################################################################################

import argparse
import fnmatch
import os
import sys
import textwrap
import traceback
import warnings

import cspyce
import julian
from kernel import Kernel, KernelFile


def format_time(tdb):
    """A printable string to represent this TDB time value."""

    if tdb is None or tdb in Kernel.ALL_TIME:
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


def print_kernel(basename):
    """Print the "KTuple" info for KernelFile object."""

    try:
        kernel = KernelFile(basename)
        print(f"KTuple('{basename}',")

        (tdb0, tdb1) = kernel.time
        time0 = format_time(tdb0)
        time1 = format_time(tdb1)
        print(f'    {time0}, {time1},')

        naif_ids = list(kernel.naif_ids_without_aliases)
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
        print('Error in ' + KernelFile.ABSPATHS[basename] + ': ' + str(e))
        traceback.print_exc()


def summarize_kernels(paths, pattern=None, ktype=None):
    """Print "KTuple" info for each file or directory path."""

    for path in paths:
        if os.path.isdir(path):
            basenames = []
            KernelFile.ABSPATHS.clear()
            KernelFile.walk(path)

            if pattern is None:
                abspaths = KernelFile.ABSPATHS.values()
                abspaths = list(abspaths)
            else:
                keys = KernelFile.ABSPATHS.keys()
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
                abspaths = [KernelFile.ABSPATHS[k] for k in keys]

            abspaths.sort()
            for abspath in abspaths:
                (_, basename) = os.path.split(abspath)
                kernel = KernelFile(basename)
                if ktype and kernel.ktype != ktype:
                    continue
                basenames.append(basename)

            # Sort basenames, putting un-suffixed names last
            basenames.sort(key=lambda name: name.replace('.', '~.'))
            for basename in basenames:
                print_kernel(basename)

        else:
            KernelFile.use_path(path)
            (_, basename) = os.path.split(path)
            print_kernel(basename)

########################################

if __name__ == '__main__':

    KernelFile.FILENAME_RELEASE_DATES = False
    KernelFile.FILEDATE_RELEASE_DATES = False

    # Ignore warnings
    warnings.simplefilter("ignore")

    # Define parser...
    parser = argparse.ArgumentParser(description='''summarize_kernels.py.''')

    parser.add_argument('paths', type=str, nargs='*', default=None,
                        help='File or directory path(s).')
    parser.add_argument('--pattern', type=str, default=None,
                        help='''Optional file match pattern to use for filtering
                                the file basenames.''')
    parser.add_argument('--ktype', type=str, default=None,
                        help='''Optional ktype to select; one of "PCK", "SPK",
                                'etc.''')
    parser.add_argument('--furnish', type=str, nargs='*', default=[],
                        help='''One or more kernels to furnish beforehand;
                                for example, a spacecraft clock kernel that is
                                needed prior to determining the time limits of C
                                kernels.''')

    args = parser.parse_args()

    for path in args.furnish:
        cspyce.furnsh(path)

    summarize_kernels(args.paths, pattern=args.pattern, ktype=args.ktype)

################################################################################

