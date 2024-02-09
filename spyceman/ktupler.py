##########################################################################################
# spyceman/ktupler.py
##########################################################################################
"""\
Print a Python "KTuple" definition for one or more SPICE kernel files.

Usage:
    python ktupler.py [options] <directory_or_file> [...]

Use "-h" or "--help" for a complete list of options.

Enter:
    python ktupler.py --output OUTPUT_PATH
to write a Python file OUTPUT_PATH.py containing the definition of a list of KTuple
objects. The basename of the path (excluding ".py") will be the name of the structure. If
this file already exists, it will be updated without changing any pre-existing
definitions.
"""

import argparse
import datetime
import fnmatch
import os
import pathlib
import sys
import textwrap
import traceback
import warnings

import julian

from spyceman.kernelfile  import KernelFile
from spyceman._cspyce     import CSPYCE
from spyceman._kernelinfo import _KernelInfo
from spyceman._ktypes     import _EXTENSIONS

julian.set_ut_model('SPICE')

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


def print_ktuple(basename, out=None):
    """Print the "KTuple" info for one KernelFile object."""

    out = out or sys.stdout

    try:
        kernel = KernelFile(basename)
        out.write(f"KTuple('{basename}',\n")

        (tdb0, tdb1) = kernel.time
        time0 = format_time(tdb0)
        time1 = format_time(tdb1)
        out.write(f'    {time0}, {time1},\n')

        naif_ids = list(kernel.naif_ids_as_found)
        if naif_ids:
            naif_ids.sort()
            textlist = [str(k) + ',' for k in naif_ids[:-1]]
            textlist.append(str(naif_ids[-1]) + '},')
            text = ' '.join(textlist)
            wrapped = textwrap.wrap(text, width=75)
            out.write('    {' + wrapped[0] + '\n')
            for text in wrapped[1:]:
                out.write('     ' + text + '\n')
        else:
            out.write('    None,\n')

        release_date = kernel.release_date
        if not release_date:
            out.write('    None),\n')
        else:
            out.write("    '" + release_date + "'),\n")

    except Exception as e:
        sys.stderr.write('Error in ' + _KernelInfo.ABSPATHS[basename] + ': ' + str(e)
                         + '\n')
        traceback.print_exc(file=sys.stderr)


def summarize_kernels(paths, pattern=None, ktype=None, out=None, known=set()):
    """Print "KTuple" info for each file or directory path."""

    out = out or sys.stdout

    basenames = []
    for path in paths:
        path = pathlib.Path(path)
        if path.is_dir():
            dir_basenames = []
            _KernelInfo.ABSPATHS.clear()
            KernelFile.walk(path)

            if pattern is None:
                abspaths = _KernelInfo.ABSPATHS.values()
                abspaths = set(abspaths)
            else:
                keys = _KernelInfo.ABSPATHS.keys()
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
                abspaths = {_KernelInfo.ABSPATHS[k] for k in keys}

            abspaths = [a for a in abspaths if os.path.basename(a) not in known]
            abspaths.sort()
            for abspath in abspaths:
                abspath = pathlib.Path(abspath)
                basename = abspath.name
                ext = '.' + basename.rpartition('.')[-1].lower()
                if ktype and _EXTENSIONS.get(ext, '') != ktype:
                    continue
                if ext in ('.txt', '.TXT'):
                    text = abspath.read_text()
                    if 'KERNELS_TO_LOAD' not in text:
                        continue

                dir_basenames.append(basename)

            # Sort basenames ignoring case, putting un-suffixed names last
            dir_basenames.sort(key=lambda name: name.upper().replace('.', '~.'))
            out.write('\n')
            for basename in dir_basenames:
                print_ktuple(basename, out=out)

            basenames += dir_basenames

        else:
            KernelFile.use_path(path)
            (_, basename) = os.path.split(path)
            print_ktuple(basename, out=out)
            basenames.append(basename)

    return basenames


def new_version(path):
    """The given path with an unused version number appended."""

    version_root = path.name[:-3] + '_v'
    versions = list(v for v in path.parent.iterdir() if v.name.startswith(version_root))
    if not versions:
        return path.parent / (version_root + '1.py')

    versions.sort()
    iversion = int(versions[-1].name[len(version_root):-3])
    return path.parent / (version_root + str(iversion+1) + '.py')

##########################################################################################

if __name__ == '__main__':

    # Ignore warnings
    warnings.simplefilter('ignore')

    # Define parser...
    p = argparse.ArgumentParser(description="""\
                summarizer.py: Program to print out "KTuple" summaries containing the
                time limits, NAIF IDs, and release dates of SPICE kernel files.""")

    p.add_argument('paths', type=str, nargs='*', default=None,
                   help='File or directory path(s).')
    p.add_argument('-p', '--pattern', type=str, default=None,
                   help="""Optional file match pattern to use for filtering the file
                           basenames.""")
    p.add_argument('-t', '--ktype', type=str, default=None,
                   help='Optional ktype to select; one of "PCK", "SPK", etc.')
    p.add_argument('-f', '--furnish', type=str, nargs='*', default=[],
                   help="""One or more kernels to furnish beforehand; for example, a
                           spacecraft clock kernel that is needed for determining the
                           time limits of C kernels.""")
    p.add_argument('-r', '--rules', default=False, action='store_true',
                   help="Use release dates and time ranges derived from file names.")
    p.add_argument('--timestamps', default=False, action='store_true',
                   help='As a last resort, infer release dates from file timestamps.')
    p.add_argument('-o', '--output', type=str, default=None,
                   help='Optional path to a Python file, which will be written or '
                        'updated with the new content. The file will contain a '
                        'definition of a list object whose name will match the basename '
                        'of the file with ".py" stripped.')

    args = p.parse_args()

    for path in args.furnish:
        CSPYCE.furnsh(path)

    _KernelInfo._USE_RULES           = args.rules
    _KernelInfo._USE_DEFAULT_RULES   = args.rules
    _KernelInfo._USE_INTERNAL_DATES  = True
    _KernelInfo._USE_TIMESTAMP_DATES = args.timestamps

    if args.output:
        if not args.output.endswith('.py'):
            args.output += '.py'
        path = pathlib.Path(args.output)
        listname = path.name[:-3].upper()
        if path.exists():
            text = path.read_text()
            saved_path = new_version(path)
            path.rename(saved_path)
            parts = text.partition('\n]\n\n')
            before = parts[0] + '\n'
            after = ']\n\n' + parts[-1]
            exec(text)
            known = {b.basename for b in globals()[listname]}
        else:
            saved_path = ''
            banner = 80 * '#' + '\n'
            before = (banner + f'# {path}\n' + banner
                      + f'\nfrom spyceman.kernelfile import KTuple\n\n{listname} = [\n')
            after = ']\n\n' + banner
            known = set()

        out = path.open('w')
        out.write(before)
        if known:
            out.write('# Inserted '
                      + datetime.datetime.now().isoformat().partition('.')[0])
    else:
        out = None
        known = []

    try:
        basenames = summarize_kernels(args.paths, pattern=args.pattern, ktype=args.ktype,
                                      out=out, known=known)
    except Exception:
        if out:
            out.close()
            if saved_path:
                saved_path.rename(path)
            else:
                path.unlink()
        raise

    if out:
        if basenames:
            out.write(after)
            out.close()
        else:
            out.close()
            if saved_path:
                saved_path.rename(path)
            else:
                path.unlink()
            print('No new kernel files found')

##########################################################################################

