##########################################################################################
# hosts/cassini/ck_jupiter.py
##########################################################################################

from spyceman import make_func

# When two basenames appear on the same line, the second covers a subset of the time
# limits of the first, but was released later and therefore should take precedence.
basenames = [
    '001001_001004ra.bc',
    '001004_001006ra.bc',
    '001006_001009ra.bc',
    '001009_001011ra.bc',
    '001011_001014ra.bc',
    '001014_001016ra.bc',
    '001016_001019ra.bc',
    '001019_001021ra.bc',
    '001021_001024ra.bc',
    '001024_001026ra.bc',
    '001026_001029ra.bc',
    '001029_001031ra.bc',
    '001031_001103ra.bc',
    '001103_001105ra.bc',
    '001105_001108.bc',
    '001108_001113rc.bc',
    '001113_001118ra.bc', '001113_001116ra.bc',
    '001118_001123ra.bc',
    '001123_001130ra.bc', '001129_001130ra.bc',
    '001130_001206ra.bc',
    '001206_001213ra.bc', '001213_001213ra.bc',
    '001213_001215ra.bc',
    '001215_001219ra.bc',
    '001228_001228ra.bc',
    '001229_010103ra.bc',
    '010103_010104ra.bc',
    '010104_010104ra.bc',
    '010104_010109ra.bc',
    '010109_010114rb.bc',
    '010114_010121ra.bc',
    '010121_010123ra.bc', '010121_010122ra.bc',
    '010123_010128ra.bc', '010123_010124ra.bc',
    '010128_010129rb.bc',
    '010129_010201rb.bc',
    '010201_010203ra.bc',
    '010203_010205ra.bc',
    '010205_010208rb.bc',
    '010208_010210rb.bc',
    '010210_010212rb.bc',
    '010212_010215rb.bc',
    '010215_010217rb.bc',
    '010217_010222rb.bc',
    '010222_010225rb.bc',
    '010225_010227rb.bc',
    '010227_010301rb.bc',
    '010301_010302rb.bc',
    '010302_010304rb.bc',
    '010304_010307rb.bc',
    '010307_010309rb.bc',
    '010309_010312rb.bc',
    '010312_010316rb.bc',
    '010316_010320ra.bc',
    '010320_010322ra.bc',
    '010322_010323ra.bc',
    '010323_010325rb.bc',
    '010325_010329rb.bc',
    '010329_010330ra.bc',
    '010330_010331ra.bc',
    '010331_010402ra.bc',
]

CK_JUPITER_PATTERN = r'0[01][01][0-3][0-3]\d_\d{5}(r?[ab]?)\.bc'

ck_jupiter = make_func('ck_jupiter', pattern=CK_JUPITER_PATTERN,
                       title='Cassini Jupiter CKs',
                       exclusive=False, ordered=True, reduce=True,
                       basenames=basenames, use_others=True, missing='warn',
                       properties={'mission': 'Cassini', 'planet': 'JUPITER'})

##########################################################################################

