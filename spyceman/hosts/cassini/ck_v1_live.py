##########################################################################################
# hosts/cassini/ck_v1_live.py
##########################################################################################

from spyceman import make_func

basenames = [
    '04009_04051px.bc',
    '04051_04092ph_psiv2.bc',
    '04092_04135ph_fsiv.bc',
    '04135_04171pd_fsiv.bc',
    '04171_04212pi_fsiv.bc',
    '04212_04256pd_psiv2.bc',
    '04256_04292pe_S04.bc',
    '04292_04320pg_fsiv.bc',
    '04320_04351pf_fsiv.bc',
    '04351_05022ph_fsiv.bc',
    '05022_05058pj_fsiv.bc',
    '05058_05099pg_psiv2.bc',
    '05099_05134pg_fsiv_lmb.bc',
    '05134_05169pn_fsiv_lmb.bc',
    '05169_05212pg_fsiv_lmb.bc',
    '05212_05242pl_fsiv.bc',
    '05242_05281ph_fsiv.bc',
    '05281_05316pg.bc',
    '05316_05351pg_fsiv.bc',
    '05351_06027ph.bc',
    '06027_06070pf_fsiv.bc',
    '06070_06112ph_fsiv.bc',
    '06112_06154ph_fsiv.bc',
    '06154_06198pc_psiv2.bc',
    '06198_06231pf_fsiv.bc',
    '06231_06263pe_fsiv.bc',
    '06263_06295pe_live.bc',
    '06295_06328pg_fsiv.bc',
    '06328_07005pd_fsiv.bc',
    '07005_07048pi_fsiv.bc',
    '07048_07087ph_fsiv.bc',
    '07087_07124pf_fsiv.bc',
    '07124_07162pf_live.bc',
    '07162_07195pj_live_as_flown.bc',
    '07195_07223pe_fsiv.bc',
    '07223_07265pj_live.bc',
    '07265_07304pe_live.bc',
    '07304_07348pf_live.bc',
    '07348_08022pj_live.bc',
    '08022_08047pg_live.bc',
    '08047_08083pd_live.bc',
    '08083_08110pf_live.bc',
    '08110_08152pl_live.bc',
    '08152_08183pg_live.bc',
    '08183_08224pj_live.bc',
    '08224_08257pi_live.bc',
    '08257_08292pg_live.bc',
    '08292_08331pi_live.bc',
    '08331_09009ph_live.bc',
    '09009_09048pl_live.bc',
    '09048_09085pj_live.bc',
    '09085_09125pf_live.bc',
    '09125_09164pg_live.bc',
    '09164_09204pj_fsiv.bc',
    '09204_09237ph_live.bc',
    '09237_09278ph_live.bc',
    '09278_09317ph_live.bc',
    '09317_09356pi_live.bc',
    '09356_10023pg_live.bc',
    '10023_10060pg_live.bc',
    '10060_10095pg_live.bc',
    '10095_10137pg_live.bc',
    '10137_10176pg_live.bc',
    '10176_10211pg_live.bc',
    '10211_10249pi_live.bc',
    '10249_10284pg_live.bc',
    '10284_10328pg_live.bc',
    '10328_11017pf_live.bc',
    '11017_11066pg_live.bc',
    '11066_11115pf_live.bc',
    '11115_11184pe_live.bc',
    '11184_11250pf_live.bc',
    '11250_11320pf_live.bc',
    '11320_12024pf_live.bc',
    '12024_12097pf_live.bc',
    '12097_12170pf_live.bc',
    '12170_12238pf_live.bc',
    '12238_12307pg_as_flown.bc',
    '12307_13013pg_as_flown.bc',
    '13013_13085pf_live.bc',
    '13085_13158pf_live.bc',
    '13158_13226pf_live.bc',
    '13226_13295pf_fsiv.bc',
    '13295_13362pf_live.bc',
    '13362_14072pf_live.bc',
    '14072_14144pg_live.bc',
    '14144_14212pf_live.bc',
    '14212_14279pf_live.bc',
    '14279_14351pf_live.bc',
    '14351_15052pf_live.bc',
    '15052_15121pf_live.bc',
    '15121_15194pf_live.bc',
    '15194_15264pf_live.bc',
    '15264_15329pf_live.bc',
    '15329_16038pf_live.bc',
    '16038_16109ph_live.bc',
    '16109_16178ph_live.bc',
    '16178_16252pg_live.bc',
    '16252_16328pf_live.bc',
    '16328_17034pf_live.bc',
    '17034_17104pg_as_flown.bc',
    '17104_17145pf_as_flown.bc',
    '17145_17191ph_as_flown.bc',
    '17191_17258pf_as_flown.bc',
]

# This rule defines the version as "pa", "pb", etc. for any file version through "px" and
# makes the family name consistent. However, it will not match "...pa_gapfill".
CK_V1_PATTERN = r'[01]\d[0-3]\d\d_[01]\d[0-3]\d\d(p[a-x])_[^g].*\.bc'

_ = VersionRule(CK_V1_PATTERN, family='YYDOY_YYDOYpX_live.bc')

notes = """\
        This function returns a KernelSet containing "live" CKs that were generated as a
        part of Cassini mission planning.

        Versions of individual kernel files are identified by a two-letter code "pa"
        through "px".

"""

properties={'mission': 'Cassini', 'planet': 'Saturn', 'version': 1}

ck_v1_live = make_func('ck_v1_live', pattern=CK_V1_PATTERN, title='Saturn "live" CKs'
                       exclusive=False, ordered=False, reduce=True,
                       basenames=basenames, use_others=True, missing='warn',
                       properties=properties)

##########################################################################################