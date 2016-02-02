# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from unittest import TestCase

from seed.lib.mcm import matchers


US_STATES = [
    'federated states of micronesia',
    'colorado',
    'guam',
    'washington',
    'rhode island',
    'tennessee',
    'nevada',
    'maine',
    'mississippi',
    'south dakota',
    'new jersey',
    'wyoming',
    'minnesota',
    'north carolina',
    'new york',
    'puerto rico',
    'indiana',
    'maryland',
    'louisiana',
    'texas',
    'iowa',
    'virgin islands',
    'west virginia',
    'michigan',
    'utah',
    'virginia',
    'oregon',
    'connecticut',
    'georgia',
    'american samoa',
    'kentucky',
    'nebraska',
    'new hampshire',
    'south carolina',
    'ohio',
    'north dakota',
    'hawaii',
    'palau',
    'oklahoma',
    'delaware',
    'illinois',
    'district of columbia',
    'arkansas',
    'idaho',
    'arizona',
    'wisconsin',
    'kansas',
    'montana',
    'california',
    'massachusetts',
    'vermont',
    'northern mariana islands',
    'pennsylvania',
    'florida',
    'alaska',
    'marshall islands',
    'missouri',
    'alabama',
    'new mexico'
]


class TestMatchers(TestCase):

    def test_case_insensitivity(self):
        """Make sure we disregard case when doing comparisons."""
        fake_comp = 'TeST'
        fake_categories = ['test', 'thing', 'face']
        match, percent = matchers.best_match(
            fake_comp, fake_categories, top_n=1
        )[0]

        self.assertEqual(match, 'test')
        self.assertEqual(percent, 100)

    def test_multiple_matches(self):
        """tests that multiple matches come back"""
        state = 'Ilinois'
        matches = matchers.best_match(state, US_STATES, top_n=6)
        self.assertEqual(len(matches), 6)
        first_match = matches[0]
        second_match = matches[1]
        self.assertEqual(first_match[0], 'illinois')
        self.assertGreater(first_match[1], 90)
        self.assertLess(second_match[1], 90)
