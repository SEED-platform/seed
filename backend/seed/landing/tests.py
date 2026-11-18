"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import Client, TestCase
from django.urls import reverse
from django_otp.plugins.otp_email.models import EmailDevice

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

    def test_two_factor_login_template_has_expected_username_field(self):
        response = self.client.get(reverse("login"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_auth-username"')
        self.assertNotContains(response, 'name="username"')

    def test_two_factor_login_state_is_per_browser(self):
        """Concurrent two factor logins must not see each other's email (it used to be stored in the shared cache)"""
        users = []
        for name in ("user_a", "user_b"):
            details = {"username": f"{name}@demo.com", "email": f"{name}@demo.com", "password": "test_password"}
            EmailDevice.objects.create(user=User.objects.create_user(**details), name="default")
            users.append(details)

        login_url = reverse("login")
        clients = [Client(), Client()]
        for client, details in zip(clients, users, strict=True):
            response = client.post(
                login_url,
                {"custom_login_view-current_step": "auth", "auth-username": details["username"], "auth-password": details["password"]},
                secure=True,
            )
            self.assertEqual(response.status_code, 200)

        for client, details in zip(clients, users, strict=True):
            self.assertEqual(client.session["user_email"], details["email"])
            self.assertEqual(client.session["method_2fa"], "email")

        # the first browser's token step still offers to resend the token to its own user
        response = clients[0].post(login_url, {"custom_login_view-current_step": "token", "token-otp_token": "000000"}, secure=True)
        self.assertContains(response, f'Resend Email Token to "{users[0]["email"]}"')
        self.assertNotContains(response, users[1]["email"])
