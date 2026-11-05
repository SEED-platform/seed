"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

import pyotp
from django.urls import reverse
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from seed.tests.util import AccessLevelBaseTestCase

NO_SUCH_RESOURCE = {"status": "error", "message": "No such resource."}
DISABLED = {"disabled": True, "email": False, "token": False}


class TwoFactorViewsTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.child_member_user.email = "child_member@demo.com"
        self.child_member_user.save()
        self.owner_device = EmailDevice.objects.create(user=self.root_owner_user, name="default")

    def _post(self, url_name, data):
        return self.client.post(
            reverse(f"api:v3:two_factor-{url_name}") + f"?organization_id={self.org.id}",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_set_method_for_self(self):
        self.login_as_root_owner()
        response = self._post("set-method", {"user_email": self.root_owner_user.email, "methods": DISABLED})

        self.assertEqual(response.json(), {"methods": DISABLED})
        self.assertFalse(EmailDevice.objects.filter(user=self.root_owner_user).exists())

    def test_set_method_for_another_user_is_denied(self):
        self.login_as_child_member()
        response = self._post("set-method", {"user_email": self.root_owner_user.email, "methods": DISABLED})

        self.assertEqual(response.json(), NO_SUCH_RESOURCE)
        self.assertTrue(EmailDevice.objects.filter(pk=self.owner_device.pk).exists())

    def test_token_device_for_another_user_is_denied(self):
        self.login_as_child_member()
        response = self._post("generate-qr-code", {"user_email": self.root_owner_user.email})
        self.assertEqual(response.json(), NO_SUCH_RESOURCE)

        # a secret key generated for the requester cannot be used to set another user's device
        response = self._post("generate-qr-code", {"user_email": self.child_member_user.email})
        self.assertIn("qr_code", response.json())
        totp = pyotp.TOTP(self.client.session["otp_secret_key"])

        response = self._post("verify-code", {"user_email": self.root_owner_user.email, "code": totp.now()})
        self.assertEqual(response.json(), NO_SUCH_RESOURCE)
        self.assertFalse(TOTPDevice.objects.filter(user=self.root_owner_user).exists())
        self.assertTrue(EmailDevice.objects.filter(pk=self.owner_device.pk).exists())

        response = self._post("verify-code", {"user_email": self.child_member_user.email, "code": totp.now()})
        self.assertEqual(response.json(), {"success": True})
        self.assertTrue(TOTPDevice.objects.filter(user=self.child_member_user).exists())

    def test_resend_token_email_for_another_user_is_denied(self):
        self.login_as_child_member()
        response = self._post("resend-token-email", {"user_email": self.root_owner_user.email})

        self.assertEqual(response.json(), NO_SUCH_RESOURCE)

    def test_resend_token_email_without_device(self):
        self.login_as_child_member()
        response = self._post("resend-token-email", {"user_email": self.child_member_user.email})
        self.assertEqual(response.json(), {"message": "Email two factor authentication not configured"})

        self.login_as_root_owner()
        response = self._post("resend-token-email", {"user_email": self.root_owner_user.email})
        self.assertEqual(response.json(), {"message": "Token email sent"})

    def test_verify_code_without_secret_key(self):
        self.login_as_child_member()
        response = self._post("verify-code", {"user_email": self.child_member_user.email, "code": "123456"})

        self.assertEqual(response.json(), {"message": "Invalid request. Missing secret key"})
        self.assertFalse(TOTPDevice.objects.filter(user=self.child_member_user).exists())
