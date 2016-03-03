# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nlong
"""
from seed.functional.tests.base import LoggedInFunctionalTestCase, LoggedOutFunctionalTestCase


class LoginTests(LoggedOutFunctionalTestCase):

    def test_login(self):
        self.browser.get(self.live_server_url)
        username_input = self.browser.find_element_by_id("id_email")
        username_input.send_keys('test@example.com')
        password_input = self.browser.find_element_by_id("id_password")
        password_input.send_keys('password')
        self.browser.find_element_by_css_selector('input[value="Log In"]').click()
        self.wait_for_element_by_css('.menu')


class FunctionalTests(LoggedInFunctionalTestCase):
    pass
