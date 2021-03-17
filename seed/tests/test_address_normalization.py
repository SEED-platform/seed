# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed.utils.address import normalize_address_str


class TestColumnListProfile(TestCase):

    def test_adding_columns(self):
        cases = [
            # case, test str, expected resulting string, actual response
            ('simple', '123 Test St.', '123 test st'),
            ('none input', None, None),
            ('empty input', '', None),
            ('missing number', 'Test St.', 'test st'),
            ('missing street', '123', '123'),
            ('integer address', 123, '123'),
            ('strip leading zeros', '0000123', '123'),
            ('street 1', 'STREET', 'st'),
            ('street 2', 'Street', 'st'),
            ('boulevard', 'Boulevard', 'blvd'),
            ('avenue', 'avenue', 'ave'),
            ('trailing direction', '123 Test St. NE', '123 test st ne'),
            ('prefix direction', '123 South Test St.', '123 s test st'),
            ('verbose direction', '123 Test St. Northeast', '123 test st ne'),
            ('two directions', '111 S West Main', '111 s west main'),
            ('numeric street and direction', '555 11th St. NW', '555 11th st nw'),
            ('direction 1', '100 Main S', '100 main s'),
            ('direction 2', '100 Main South', '100 main s'),
            ('direction 3', '100 Main S.', '100 main s'),
            ('direction 4', '100 Main', '100 main'),
            # Found edge cases
            # https://github.com/SEED-platform/seed/issues/378
            ('regression 1', '100 Peach Ave. East', '100 peach ave e'),
            ('regression 2', '100 Peach Avenue E.', '100 peach ave e'),
            ('multiple addresses', 'M St., N St., 4th St., Delaware St., SW',
             'm st., n st., 4th st., delaware st., sw'),
            # House numbers declared as ranges
            ('no range separator', '300 322 S Green St', '300-322 s green st'),
            ('- as separator no whitespace', '300-322 S Green St', '300-322 s green st'),
            ('/ as separator no whitespace', '300/322 S Green St', '300-322 s green st'),
            ('\\ as separator no whitespace', '300\\322 S Green St', '300-322 s green st'),
            ('- as separator whitespace', '300 - 322 S Green St', '300-322 s green st'),
            ('/ as separator whitespace', '300 / 322 S Green St', '300-322 s green st'),
            ('\\ as separator whitespace', '300 \\ 322 S Green St', '300-322 s green st'),
            # Ranges which leave off common prefix.
            ('end of range leaves off common prefix', '300-22 S Green St', '300-322 s green st'),
            # Odd characters
            ('unicode characters', '123 Main St\uFFFD', '123 main st'),
            # Straight numbers
            ('straight numbers', 56195600100, '56195600100'),
            # bytestrings
            ('bytestring', b'123456 Main St', '123456 main st'),
            # Suites / building ids
            ('suite 1', '2655   SEELY AV Suite 9', '2655 seely av suite 9'),
            ('suite 2', '2655   SEELY AV Ste 9', '2655 seely av suite 9'),
            ('bldg 1', '2655   SEELY AV BLDG 9', '2655 seely av building 9'),
            ('bldg 2', '2655   SEELY AV BUILDING 9', '2655 seely av building 9'),
            ('b+s 1', '2655   SEELY AV BUILDING 9a ste 50', '2655 seely av building 9a suite 50'),
            ('b+s 2', '2655   SEELY AV BUILDING 9 suite 50', '2655 seely av building 9 suite 50'),
        ]

        results = []
        expected_results = [c[2] for c in cases]

        for case in cases:
            results.append(normalize_address_str(case[1]))

        # print(results)
        # print(expected_results)
        self.assertListEqual(results, expected_results)
