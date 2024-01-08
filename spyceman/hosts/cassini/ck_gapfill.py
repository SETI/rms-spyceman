##########################################################################################
# spyceman/cassini/CK_GAPFILL.py
##########################################################################################

basenames = [
    '03001_04001pa_gapfill_v01.bc',
    '04001_05001pa_gapfill_v14.bc',
    '05001_06001pa_gapfill_v14.bc',
    '06001_07001pa_gapfill_v14.bc',
    '07001_08001pa_gapfill_v14.bc',
    '08001_09001pa_gapfill_v14.bc',
    '09001_10001pa_gapfill_v14.bc',
    '10001_11001pa_gapfill_v14.bc',
    '11001_12001pa_gapfill_v14.bc',
    '12001_13001pa_gapfill_v14.bc',
    '13001_14001pa_gapfill_v14.bc',
    '14001_15001pa_gapfill_v14.bc',
    '15001_16001pa_gapfill_v14.bc',
    '16001_17001pa_gapfill_v14.bc',
    '17001_18001pa_gapfill_v14.bc',
]

CK_GAPFILL_PATTERN = r'[01]\d001_[01]\d001pa_gapfill_v(\d\d)\.bc'

# This rule assigns a version number to the gapfill cks.
_ = VersionRule(CK_GAPFILL_PATTERN, family='YYDOY_YYDOYpa_gapfill_vNN.bc')

notes = """\
        The Cassini "gapfill" CKs should always be furnished at a lower precedence than
        any other selected CKs.

"""

ck_gapfill = make_func('ck_gapfill', pattern=CK_GAPFILL_PATTERN,
                       title='Cassini "gapfill" CKs', notes=notes,
                       exclusive=False, reduce=True, ordered=False,
                       basenames=basenames, use_others=True, missing='warn',
                       properties={'mission': 'Cassini', 'planet': 'Saturn'})

##########################################################################################
