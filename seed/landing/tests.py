# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase
from django.core.urlresolvers import reverse

from tos.models import TermsOfService

from seed.landing.models import SEEDUser as User


class UserLoginTest(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'email': 'test_user@demo.com',
            'password': 'test_password'
        }
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse('landing:login')
        self.tos_url = reverse('tos_check_tos')

    def test_simple_login(self):
        """
        Happy path login with no ToS.
        """
        self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_tos_login(self):
        """
        Happy path login when there is a ToS.
        """
        tos = "Agree to these terms"
        TermsOfService.objects.create(active=True,
                                      content=tos)
        res = self.client.post(self.login_url, self.user_details, secure=True)

        # expect to see the tos, in a form with an action to confirm
        self.assertContains(res, tos)
        expected_action = 'action="%s"' % self.tos_url
        self.assertContains(res, expected_action)

        # django-tos doesn't log the user in yet
        self.assertFalse('_auth_user_id' in self.client.session)

        # and submitting 'accept=accept' to the confirm url logs you in
        self.client.post(self.tos_url, {'accept': 'accept'})

        # now we're logged in
        self.assertTrue('_auth_user_id' in self.client.session)
