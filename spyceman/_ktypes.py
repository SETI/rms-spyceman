##########################################################################################
# spyceman/_ktypes.py
##########################################################################################

# This is the order used in metakernels
_KTYPES = ['META', 'LSK', 'FK', 'IK', 'PCK', 'DSK', 'SCLK', 'CK', 'SPK', 'STAR']

_EXTENSIONS = {
    '.bc' : 'CK',
    '.bdb': 'STAR',
    '.bds': 'DSK',
    '.bpc': 'PCK',
    '.bsp': 'SPK',
    '.tf' : 'FK',
    '.ti' : 'IK',
    '.tls': 'LSK',
    '.tm' : 'META',
    '.tpc': 'PCK',
    '.tsc': 'SCLK',
    '.txt': 'META',     # maybe; these files require a closer look
}

##########################################################################################
