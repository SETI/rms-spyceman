##########################################################################################
# spyceman/cspyce.py
##########################################################################################
"""Defines CSPYCE as either the cspyce or the spicepy module.

To use:
    from spyceman.cspyce import CSPYCE
Elsewhere, use "CSPYCE" where you would normally type "cspyce" or "spicepy".

If the environment variable "SPICEMODULE" is defined, this is interpreted as the name of
the module. Otherwise, CSPYCE is defined as the cspyce module if it is installed, and
otherwise the spicepy module.

Note that the spicepy module does not support aliases or array operations.

This module also defines two additional variables that are available for import:
    CSPYCE_NAME     the name of the module, either "cspyce" or "spicepy".
    CSPYCE_ALIASES  True if alias support is available; False otherwise.
"""

import importlib
import os

##########################################################################################
# Define CSPYCE and CSPYCE_NAME
##########################################################################################

CSPYCE = None
CSPYCE_NAME = ''

if 'SPICEMODULE' in os.environ:
    CSPYCE_NAME = os.environ['SPICEMODULE']
    CSPYCE = importlib.import_module(CSPYCE_NAME)

else:
    for name in ('cspyce', 'spicepy'):
        try:
            CSPYCE_NAME = name
            CSPYCE = importlib.import_module(name)
            break
        except ModuleNotFoundError:
            pass

if CSPYCE is None:
    raise ImportError('unable to import cspyce or spicepy')

##########################################################################################
# Either define cspyce aliases or fake them for spicepy
##########################################################################################

def _fake_get_body_aliases(item):
    if isinstance(item, str):
        code, found = CSPYCE.bodn2c(item)
    else:
        code, found = (item, True)
    if found:
        name, found = CSPYCE.bodc2n(code)
    if not found:
        return ([], [])
    return ([code], [name])

def _fake_get_frame_aliases(item):
    if isinstance(item, str):
        code, found = CSPYCE.namfrm(item)
    else:
        code, found = (item, True)
    if found:
        name, found = CSPYCE.frmnam(code)
    if not found:
        return ([], [])
    return ([code], [name])

def _fake_define_body_aliases(*items):
    code = [i for i in items if isinstance(i, numbers.Integral)][0]
    name = [i for i in items if isinstance(i, str)][0]
    test_name, found = CSPYCE.bodc2n(code)
    if found:
        if test_name.upper() != name.upper():   # don't repeat existing boddef's
            CSPYCE.boddef(name, code)
    else:
        CSPYCE.boddef(name, code)

CSPYCE_ALIASES = (CSPYCE_NAME == 'cspyce')

if CSPYCE_ALIASES:
    import cspyce.aliases

    # Disable Python errors for a few core functions
    CSPYCE.bodn2c = cspyce.bodn2c.flag
    CSPYCE.bodc2n = cspyce.bodc2n.flag
    CSPYCE.cidfrm = cspyce.cidfrm.flag
    CSPYCE.namfrm = cspyce.namfrm.flag
    CSPYCE.frmnam = cspyce.frmnam.flag

else:
    CSPYCE.use_aliases = lambda *args: None
    CSPYCE.use_noaliases = lambda *args: None
    CSPYCE.get_body_aliases = _fake_get_body_aliases
    CSPYCE.get_frame_aliases = _fake_get_frame_aliases
    CSPYCE.define_body_aliases = _fake_define_body_aliases
    CSPYCE.define_frame_aliases = lambda *args: None

##########################################################################################
