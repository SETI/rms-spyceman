################################################################################
# spyceman/solarsystem/_DE_SPKS.py
################################################################################
"""Managed list of NAIF "DE" SPK files, complete as of 2/1/24."""

from spyceman.kernelfile import KTuple

_DE_SPKS = [

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
KTuple('de413.bsp',
    '1899-12-03T23:59:27.817', '2050-03-06T23:58:50.815',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399, 499},
    '2004-11-17'),
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
KTuple('de440.bsp',
    '1549-12-20T23:59:27.816', '2650-01-24T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
KTuple('de440s.bsp',
    '1849-12-25T23:59:27.816', '2150-01-21T23:58:50.816',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
KTuple('de441_part-1.bsp',                                  # extended duration
    -479654827200.0, '1969-07-29T23:59:27.817',
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
KTuple('de441_part-2.bsp',                                  # extended duration
    '1969-06-27T23:59:27.816', 479387937600.0,
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 199, 299, 301, 399},
    '2020-06-25'),
]

################################################################################