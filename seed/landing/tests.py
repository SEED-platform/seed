"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User


class UserLoginTest(TestCase):
    def setUp(self):
        self.user_details = {"username": "test_user@demo.com", "email": "test_user@demo.com", "password": "test_password"}
        self.user = User.objects.create_user(**self.user_details)
        self.login_url = reverse("landing:login")

    def test_simple_login(self):
        """
        Happy path login
        """
        response = self.client.post(self.login_url, self.user_details, secure=True)
        self.assertTrue(response.status_code == 302)
        self.assertTrue(response.url == "/account/login/")
