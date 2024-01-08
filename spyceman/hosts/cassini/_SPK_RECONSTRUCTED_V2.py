##########################################################################################
# hosts/cassini/_SPK_RECONSTRUCTED_V2.py
##########################################################################################

from kernels import KernelFile, KernelSet

KernelFile.set_global_prerequisites('180628RU_SCPSE_04183_17258.bsp',
                                    '180927AP_RE_90165_18018.bsp')

basenames = [
    '180927AP_RE_90165_18018.bsp',
    '180628RU_SCPSE_04183_17258.bsp',
]

for b in basenames:
    KernelFile(b).version = 2
    KernelFile(b).family = 'YYMMDDr_scpse_YYMMDD_YYMMDD.bsp'

_SPK_RECONSTRUCTED_V2 = KernelSet(basenames, ordered=True)
_SPK_RECONSTRUCTED_V2.version = 2

##########################################################################################
