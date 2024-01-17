##########################################################################################
# spyceman/planets/__init__.py
##########################################################################################

__all__ = []

from spyceman import CSPYCE, KTuple, Rule, spicefunc

##########################################################################################
# Managed list of known LSK kernels
##########################################################################################

_LSK_INFO = [
    KTuple('naif0007.tls', None, None, set(), '1998-07-17'),
    KTuple('naif0008.tls', None, None, set(), '2005-08-03'),
    KTuple('naif0009.tls', None, None, set(), '2008-07-07'),
    KTuple('naif0010.tls', None, None, set(), '2012-01-05'),
    KTuple('naif0011.tls', None, None, set(), '2015-01-05'),
    KTuple('naif0012.tls', None, None, set(), '2016-07-14'),
]

Rule(r'naif(NNNN).*\.tls')

lsk = spicefunc('lsk', pattern=r'naif\d\d\d\d.*\.tls', title='NAIF LSKs',
                known=_LSK_INFO, exclusive=True)

##########################################################################################
# Managed list of known PCK kernels
##########################################################################################

_PCK_INFO = [

KTuple('pck00003.tpc',
    None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713,
     714, 715, 799, 801, 802, 899, 901, 999},
    '1990-06-25'),
KTuple('pck00005.tpc',
    None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712,
     713, 714, 715, 799, 801, 802, 803, 804, 805, 806, 807, 808, 899, 901, 999,
     2431010, 9511010},
    '1995-06-25'),
KTuple('pck00006.tpc', None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712,
     713, 714, 715, 799, 801, 802, 803, 804, 805, 806, 807, 808, 899, 901, 999,
     2431010, 9511010},
    '1997-11-19'),
KTuple('pck00007.tpc', None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712,
     713, 714, 715, 799, 801, 802, 803, 804, 805, 806, 807, 808, 899, 901, 999,
     2431010, 9511010},
    '2000-04-24'),
KTuple('pck00008.tpc', None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712,
     713, 714, 715, 799, 801, 802, 803, 804, 805, 806, 807, 808, 899, 901, 999,
     2000004, 2000216, 2000433, 2431010, 9511010},
    '2004-09-21'),
KTuple('pck00009.tpc', None, None,
    {3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 699, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712,
     713, 714, 715, 799, 801, 802, 803, 804, 805, 806, 807, 808, 899, 901, 999,
     1000005, 1000036, 1000093, 1000107, 2000001, 2000004, 2000253, 2000433,
     2004179, 2025143, 2431010, 9511010},
    '2010-03-03'),
KTuple('pck00010.tpc', None, None,
    {1, 3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 632, 633, 634, 635, 649, 699, 701, 702, 703, 704, 705, 706, 707,
     708, 709, 710, 711, 712, 713, 714, 715, 799, 801, 802, 803, 804, 805, 806,
     807, 808, 899, 901, 999, 1000005, 1000036, 1000093, 1000107, 2000001,
     2000002, 2000004, 2000021, 2000253, 2000433, 2000511, 2002867, 2004179,
     2025143, 2431010, 9511010},
    '2011-10-21'),
KTuple('pck00011_n0066.tpc', None, None,
    {1, 3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
     504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
     602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
     617, 618, 632, 633, 634, 635, 649, 699, 701, 702, 703, 704, 705, 706, 707,
     708, 709, 710, 711, 712, 713, 714, 715, 799, 801, 802, 803, 804, 805, 806,
     807, 808, 899, 901, 999, 1000005, 1000036, 1000093, 1000107, 2000001,
     2000002, 2000004, 2000021, 2000253, 2000433, 2000511, 2002867, 2004179,
     2025143, 2431010, 9511010},
    '2022-12-27'),
KTuple('pck00011.tpc', None, None,
    {1, 3, 4, 5, 6, 7, 8, 10, 199, 299, 301, 399, 401, 402, 499, 501, 502, 503,
    504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 599, 601,
    602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616,
    617, 618, 632, 633, 634, 635, 649, 653, 699, 701, 702, 703, 704, 705, 706,
    707, 708, 709, 710, 711, 712, 713, 714, 715, 799, 801, 802, 803, 804, 805,
    806, 807, 808, 899, 901, 999, 1000005, 1000012, 1000036, 1000093, 1000107,
    2000001, 2000002, 2000004, 2000016, 2000021, 2000052, 2000253, 2000433,
    2000511, 2002867, 2004179, 2025143, 2431010, 9511010},
    '2022-12-27'),
]

Rule(r'pck(NNNNN).*\.tpc')

# pck00011.tpc is a special case!
_version = CSPYCE.tkvrsn('toolkit')
if _version >= 'CSPICE_N0067':
    _PCK_INFO = [i for i in _PCK_INFO if i.basename != 'pck00011_n0066.tpc']
    _PCK_PATTERN = r'pck(000\d\d)\.tpc'
else:
    _PCK_INFO = [i for i in _PCK_INFO if i.basename != 'pck00011.tpc']
    _PCK_PATTERN = r'pck(0000\d|00010|00011(?=_n0066)).*\.tpc'

pck = spicefunc('pck', pattern=_PCK_PATTERN, title='general NAIF PCKs',
                known=_PCK_INFO, exclusive=True)

##########################################################################################
# 'Dynamical Ephemeris ('DE') SPK support
##########################################################################################

_SPK_INFO = [

KTuple('de118.bsp',
    '1599-12-08T23:59:27.817', '2200-01-31T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2005-11-21'),
KTuple('de125.bsp',
    '1899-08-29T23:59:27.817', '2050-02-02T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2005-11-21'),
KTuple('de130.bsp',
    '1899-12-03T23:59:27.817', '2050-01-01T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2005-11-21'),
KTuple('de200.bsp',
    '1599-12-08T23:59:27.817', '2169-05-01T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2005-11-21'),
KTuple('de245_1960_1980.bsp',
    '1960-01-01T00:00:09', '1981-01-01T00:00:00',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '1997-03-01'),
KTuple('de245_1990_2010.bsp',
    '1990-01-01T00:00:00', '2009-12-31T23:59:55',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '1998-05-26'),
KTuple('de403_2000-2020.bsp',
    '1999-12-23T23:58:55.816', '2021-01-01T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2004-10-05'),
KTuple('de403s.bsp',
    '1979-11-30T23:59:09.817', '2011-01-06T23:58:53.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '1995-06-01'),
KTuple('de403.bsp',
    '1996-01-01T00:00:00', '2111-01-01T23:59:53',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '1995-05-08'),
KTuple('de405s.bsp',
    '1997-01-01T00:00:00', '2010-01-01T23:59:57',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2000-08-16'),
KTuple('de405.bsp',
    '1950-01-01T00:00:09', '2049-12-31T23:59:55',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '1998-08-26'),
KTuple('de406s.bsp',
    '1900-01-01T00:00:09', '2199-12-31T23:59:53',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2002-03-03'),
KTuple('de408.bsp',                                        # extended duration
    -379270468800.0, 252751752000.0,
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2005-07-07'),
KTuple('de414.bsp',
    '1599-12-08T23:59:27.817', '2201-02-19T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2006-04-25'),
KTuple('de418.bsp',
    '1899-12-03T23:59:27.817', '2051-01-20T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2007-08-03'),
KTuple('de421.bsp',
    '1899-07-28T23:59:27.817', '2053-10-08T23:58:50.818',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2008-02-12'),
KTuple('de422.bsp',                                         # extended duration
    -157757457600.0, '3000-01-29T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2011-05-26'),
KTuple('de430.bsp',
    '1549-12-20T23:59:27.816', '2650-01-24T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2013-09-03'),
KTuple('de432s.bsp',
    '1949-12-13T23:59:27.817', '2050-01-01T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2014-04-30'),
KTuple('de435.bsp',
    '1549-12-20T23:59:27.816', '2650-01-24T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2016-03-04'),
KTuple('de438.bsp',
    '1549-12-20T23:59:27.816', '2650-01-24T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2018-03-30'),
KTuple('de441_part-1.bsp',                                  # extended duration
    -479654827200.0, '1969-07-29T23:59:27.817',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
KTuple('de441_part-2.bsp',                                  # extended duration
    '1969-06-27T23:59:27.816', 479387937600.0,
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
# Let DE440 take precedence over DE441, because DE441 is just the same kernel with
# extended time coverage.
KTuple('de440.bsp',
    '1549-12-20T23:59:27.816', '2650-01-24T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
KTuple('de440s.bsp',
    '1849-12-25T23:59:27.816', '2150-01-21T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
]

# These are special-purpose DE files, available but not used by default

_SPK_EXTRAS = [

# The latest JPL Planetary Ephemeris, DE410, has been created especially
# for the MER arrival at Mars in January 2004 and for the Cassini
# arrival at Saturn in July 2004.

KTuple('de410mini.bsp',
    '2004-01-01T00:00:00', '2004-07-01T00:00:00',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2003-11-18'),
KTuple('de410s.bsp',
    '1995-01-01T00:00:00', '2017-12-31T23:59:55',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2003-05-03'),
KTuple('de410.bsp',
    '1900-02-05T23:59:27.815', '2019-12-14T23:58:50.817',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2003-04-24'),

# The JPL Planetary Ephemeris, DE413, has been created expressly for an updated
# ephemeris of Pluto, in view of the upcoming possible occultation of a star by
# Pluto's satellite, Charon, on 11 July 2005 around 03:39 UT.

KTuple('de413.bsp',
    '1899-12-03T23:59:27.817', '2050-03-06T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2004-11-17'),
]

# Rule for version numbers of standard planetary ephemerides
Rule(r'(de|mar|jup|sat|ura|nep|plu)(NNN).*\.bsp')

_SPK_BODY_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399}
    # These SPKs no longer include 499, Mars center

basenames = [k.basename for k in _SPK_EXTRAS + _SPK_INFO]

spk = spicefunc('spk', pattern=r'de(\d\d\d).*\.bsp', title='"DE" Solar System SPKs',
                known=_SPK_INFO, extras=_SPK_EXTRAS, default_naif_ids=_SPK_BODY_IDS,
                exclusive=False, ordered=True, reduce=True)

##########################################################################################