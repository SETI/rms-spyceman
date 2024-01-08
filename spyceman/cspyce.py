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
    CSPYCE = import_cspyce(CSPYCE_NAME)

else:
    for name in ('cspyce', 'spicepy'):
        try:
            CSPYCE_NAME = name
            CSPYCE = import_cspyce(name)
        except ModuleNotFoundError:
            pass

if CSPYCE is None:
    raise ImportError('unable to import cspyce or spicepy')

##########################################################################################
# Either define cspyce aliases or fake them for spicepy
##########################################################################################

def _fake_get_body_aliases(item):

    if isinstance(item, str):
        item = CSPYCE.bodn2c(item)

    return ([item], [CSPYCE.bodc2n(item)])

def _fake_get_frame_aliases(item):

    if isinstance(item, str):
        item = CSPYCE.namfrm(item)

    return ([item], [CSPYCE.frmnam(item)])

CSPYCE_ALIASES = (CSPYCE_NAME == 'cspyce')

if CSPYCE_ALIASES:
    import cspyce.aliases
else:
    CSPYCE.use_aliases = lambda *args: None
    CSPYCE.use_noaliases = lambda *args: None
    CSPYCE.get_body_aliases = _fake_get_body_aliases
    CSPYCE.get_frame_aliases = _fake_get_frame_aliases
    CSPYCE.define_body_aliases = lambda *args: None
    CSPYCE.define_frame_aliases = lambda *args: None

##########################################################################################
