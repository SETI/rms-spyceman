##########################################################################################
# hosts/cassini/_SPK_RECONSTRUCTED_V1.py
##########################################################################################

from kernels import KernelFile, KernelSet

basenames = [
    '041014R_SCPSE_01066_04199.bsp',
    '041219R_SCPSE_04199_04247.bsp',
    '050105RB_SCPSE_04247_04336.bsp',
    '050214R_SCPSE_04336_05015.bsp',
    '050411R_SCPSE_05015_05034.bsp',
    '050414RB_SCPSE_05034_05060.bsp',
    '050504R_SCPSE_05060_05081.bsp',
    '110916R_SCPSE_05081_05097.bsp',
    '050513RB_SCPSE_05097_05114.bsp',
    '050606R_SCPSE_05114_05132.bsp',
    '050623R_SCPSE_05132_05150.bsp',
    '050708R_SCPSE_05150_05169.bsp',
    '050802R_SCPSE_05169_05186.bsp',
    '050825R_SCPSE_05186_05205.bsp',
    '050907R_SCPSE_05205_05225.bsp',
    '050922R_SCPSE_05225_05245.bsp',
    '051011R_SCPSE_05245_05257.bsp',
    '051021R_SCPSE_05257_05275.bsp',
    '051114R_SCPSE_05275_05293.bsp',
    '051213R_SCPSE_05293_05320.bsp',
    '060111R_SCPSE_05320_05348.bsp',
    '060213R_SCPSE_05348_06005.bsp',
    '060321R_SCPSE_06005_06036.bsp',
    '060417R_SCPSE_06036_06068.bsp',
    '060515R_SCPSE_06068_06099.bsp',
    '060614R_SCPSE_06099_06130.bsp',
    '060719R_SCPSE_06130_06162.bsp',
    '060810R_SCPSE_06162_06193.bsp',
    '060907R_SCPSE_06193_06217.bsp',
    '060925R_SCPSE_06217_06240.bsp',
    '061013R_SCPSE_06240_06260.bsp',
    '061108R_SCPSE_06260_06276.bsp',
    '061116R_SCPSE_06276_06292.bsp',
    '061129RB_SCPSE_06292_06308.bsp',
    '061213R_SCPSE_06308_06318.bsp',
    '070109R_SCPSE_06318_06332.bsp',
    '070117R_SCPSE_06332_06342.bsp',
    '070125R_SCPSE_06342_06356.bsp',
    '070208R_SCPSE_06356_07008.bsp',
    '070213R_SCPSE_07008_07023.bsp',
    '070312R_SCPSE_07023_07042.bsp',
    '070405R_SCPSE_07042_07062.bsp',
    '070430R_SCPSE_07062_07077.bsp',
    '070507R_SCPSE_07077_07094.bsp',
    '070517R_SCPSE_07094_07106.bsp',
    '070605R_SCPSE_07106_07125.bsp',
    '070625R_SCPSE_07125_07140.bsp',
    '070705R_SCPSE_07140_07155.bsp',
    '070727R_SCPSE_07155_07170.bsp',
    '070822R_SCPSE_07170_07191.bsp',
    '071017R_SCPSE_07191_07221.bsp',
    '071127R_SCPSE_07221_07262.bsp',
    '080117R_SCPSE_07262_07309.bsp',
    '080123R_SCPSE_07309_07329.bsp',
    '080225R_SCPSE_07329_07345.bsp',
    '080307R_SCPSE_07345_07365.bsp',
    '080327R_SCPSE_07365_08045.bsp',
    '080428R_SCPSE_08045_08067.bsp',
    '080515R_SCPSE_08067_08078.bsp',
    '080605R_SCPSE_08078_08126.bsp',
    '080618R_SCPSE_08126_08141.bsp',
    '080819R_SCPSE_08141_08206.bsp',
    '080916R_SCPSE_08206_08220.bsp',
    '081031R_SCPSE_08220_08272.bsp',
    '081126R_SCPSE_08272_08294.bsp',
    '081217R_SCPSE_08294_08319.bsp',
    '090120R_SCPSE_08319_08334.bsp',
    '090202R_SCPSE_08334_08350.bsp',
    '090225R_SCPSE_08350_09028.bsp',
    '090423R_SCPSE_09028_09075.bsp',
    '090507R_SCPSE_09075_09089.bsp',
    '090520R_SCPSE_09089_09104.bsp',
    '090609R_SCPSE_09104_09120.bsp',
    '090624R_SCPSE_09120_09136.bsp',
    '090701R_SCPSE_09136_09153.bsp',
    '090708R_SCPSE_09153_09168.bsp',
    '090806R_SCPSE_09168_09184.bsp',
    '090817R_SCPSE_09184_09200.bsp',
    '090921R_SCPSE_09200_09215.bsp',
    '090924R_SCPSE_09215_09231.bsp',
    '091116R_SCPSE_09231_09275.bsp',
    '091208R_SCPSE_09275_09296.bsp',
    '100107R_SCPSE_09296_09317.bsp',
    '100113R_SCPSE_09317_09339.bsp',
    '100114R_SCPSE_09339_09355.bsp',
    '100127R_SCPSE_09355_10003.bsp',
    '100209R_SCPSE_10003_10021.bsp',
    '100325R_SCPSE_10021_10055.bsp',
    '100420R_SCPSE_10055_10085.bsp',
    '100519R_SCPSE_10085_10110.bsp',
    '100616R_SCPSE_10110_10132.bsp',
    '100625R_SCPSE_10132_10146.bsp',
    '100706R_SCPSE_10146_10164.bsp',
    '110916R_SCPSE_10164_10178.bsp',
    '100913R_SCPSE_10178_10216.bsp',
    '101013R_SCPSE_10216_10256.bsp',
    '101210R_SCPSE_10256_10302.bsp',
    '101215R_SCPSE_10302_10326.bsp',
    '110224R_SCPSE_10326_10344.bsp',
    '110204R_SCPSE_10344_11003.bsp',
    '110308R_SCPSE_11003_11041.bsp',
    '110504R_SCPSE_11041_11093.bsp',
    '110519R_SCPSE_11093_11119.bsp',
    '110721R_SCPSE_11119_11150.bsp',
    '111010R_SCPSE_11150_11246.bsp',
    '111014R_SCPSE_11246_11267.bsp',
    '111123R_SCPSE_11267_11303.bsp',
    '120117R_SCPSE_11303_11337.bsp',
    '120119R_SCPSE_11337_11357.bsp',
    '120227R_SCPSE_11357_12016.bsp',
    '120312R_SCPSE_12016_12042.bsp',
    '120416R_SCPSE_12042_12077.bsp',
    '120426R_SCPSE_12077_12098.bsp',
    '120523R_SCPSE_12098_12116.bsp',
    '120628R_SCPSE_12116_12136.bsp',
    '120820R_SCPSE_12136_12151.bsp',
    '120829R_SCPSE_12151_12199.bsp',
    '121130R_SCPSE_12199_12257.bsp',
    '121204R_SCPSE_12257_12304.bsp',
    '130318R_SCPSE_12304_12328.bsp',
    '130319R_SCPSE_12328_13038.bsp',
    '130321R_SCPSE_13038_13063.bsp',
    '130417R_SCPSE_13063_13087.bsp',
    '130710R_SCPSE_13087_13137.bsp',
    '130805R_SCPSE_13137_13182.bsp',
    '130807R_SCPSE_13182_13200.bsp',
    '131024R_SCPSE_13200_13241.bsp',
    '131105R_SCPSE_13241_13273.bsp',
    '131212R_SCPSE_13273_13314.bsp',
    '140123R_SCPSE_13314_13352.bsp',
    '140219R_SCPSE_13352_14025.bsp',
    '140409R_SCPSE_14025_14051.bsp',
    '140730R_SCPSE_14051_14083.bsp',
    '140907R_SCPSE_14083_14118.bsp',
    '140909R_SCPSE_14118_14156.bsp',
    '141106R_SCPSE_14156_14187.bsp',
    '141107R_SCPSE_14187_14222.bsp',
    '150107R_SCPSE_14222_14251.bsp',
    '150122R_SCPSE_14251_14283.bsp',
    '150304R_SCPSE_14283_14327.bsp',
    '150430R_SCPSE_14327_14365.bsp',
    '150609R_SCPSE_14365_15033.bsp',
    '150803R_SCPSE_15033_15066.bsp',
    '150828R_SCPSE_15066_15116.bsp',
    '151009R_SCPSE_15116_15161.bsp',
    '151013R_SCPSE_15161_15180.bsp',
    '151014R_SCPSE_15180_15222.bsp',
    '151102R_SCPSE_15222_15261.bsp',
    '151112R_SCPSE_15261_15280.bsp',
    '151116R_SCPSE_15280_15295.bsp',
    '160129R_SCPSE_15295_15310.bsp',
    '160323R_SCPSE_15310_15347.bsp',
    '160330R_SCPSE_15347_16007.bsp',
    '160413R_SCPSE_16007_16025.bsp',
    '160519R_SCPSE_16025_16041.bsp',
    '160608R_SCPSE_16041_16088.bsp',
    '160718R_SCPSE_16088_16115.bsp',
    '160725R_SCPSE_16115_16146.bsp',
    '161117R_SCPSE_16146_16201.bsp',
    '161208R_SCPSE_16201_16217.bsp',
    '161214R_SCPSE_16217_16262.bsp',
    '170228R_SCPSE_16262_16282.bsp',
    '170301R_SCPSE_16282_16310.bsp',
    '170315R_SCPSE_16310_16329.bsp',
    '170323R_SCPSE_16329_16363.bsp',
    '170509R_SCPSE_16363_17061.bsp',
    '170720R_SCPSE_17061_17104.bsp',
    '170811R_SCPSE_17104_17117.bsp',
    '171017R_SCPSE_17117_17146.bsp',
    '171024R_SCPSE_17146_17177.bsp',
    '171031R_SCPSE_17177_17224.bsp',
    '171214R_SCPSE_17224_17258.bsp',
]

for b in basenames:
    KernelFile(b).version = 1
    KernelFile(b).family = 'YYMMDDr_scpse_YYMMDD_YYMMDD.bsp'

_SPK_RECONSTRUCTED_V1 = KernelSet(basenames, ordered=False)
_SPK_RECONSTRUCTED_V1.version = 1

##########################################################################################
