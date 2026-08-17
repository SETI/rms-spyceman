##########################################################################################
# spyceman/_ktypes.py
##########################################################################################

# This is the order used in metakernels; in general, each ktype appears later in the list
# than the other ktypes on which it might depend.
_KTYPES = ['META', 'LSK', 'STAR', 'PCK', 'DSK', 'FK', 'IK', 'SCLK', 'CK', 'SPK']

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
