# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
from django.test import TestCase

from seed.views.portfoliomanager import PortfolioManagerImport
# from seed.views.portfoliomanager import PortfolioManagerViewSet


class PortfolioManagerImportTest(TestCase):

    def test_unsuccessful_login(self):
        # To test a successful login, we'd have to include valid PM credentials, which we don't want to do
        # so I will at least test an unsuccessful login attempt here
        pmi = PortfolioManagerImport('bad_username', 'bad_password')
        with self.assertRaises(Exception):
            pmi.login_and_set_cookie_header()
