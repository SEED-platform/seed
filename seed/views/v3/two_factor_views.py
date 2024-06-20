import base64
import binascii

import pyotp
from django.http import JsonResponse
from django_otp import devices_for_user
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.decorators import action

from seed.landing.models import SEEDUser
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import api_endpoint_class
from seed.utils.two_factor import generate_qr_code, send_token_email
from seed.utils.viewsets import ModelViewSetWithoutPatch


class TwoFactorViewSet(ModelViewSetWithoutPatch):
    @api_endpoint_class
    @has_perm_class("can_modify_data")
    @action(detail=False, methods=["POST"])
    def set_method(self, request):
        """
        Sets the 2 Factor Authentication method for a user. The options are 'disabled', 'email', or 'token'.
        If any organization associated with the user requires 2 Factor Authentication the 'disabled' option will be disabled.
        If 'email' is set a test email will be sent to the user
        If 'token' is set a QR code will be presented to the user for verification before setting the method
        """
        user_email = request.data.get("user_email")
        methods = request.data.get("methods")
        if all(method is False for method in methods.values()):
            return JsonResponse({"status": "error", "message": "Unexpected Error"})

        user = User.objects.get(email=user_email)
        require_2fa = bool(user.orgs.filter(require_2fa__isnull=False).count)
        if methods.get("disabled") and require_2fa:
            return JsonResponse({"message": "2 Factor Authentication is required for your organization"})

        devices = list(devices_for_user(user))
        email_active = bool(devices and type(devices[0]) == EmailDevice)
        token_active = bool(devices and type(devices[0]) == TOTPDevice)
        qr_code_img = None
        # token_active = type(devices[0]) == Token?
        if methods.get("email") and not email_active:
            email_device = EmailDevice.objects.create(user=user, name="default", email=user.username)
            if email_device:
                [device.delete() for device in devices]
                # just for user confirmation
                send_token_email(email_device)

        elif methods.get("token") and not token_active:
            # generate qr code
            secret_key = pyotp.random_base32()
            request.session["otp_secret_key"] = secret_key

            issuer_name = "SEED-Platform"
            otp_url = f"otpauth://totp/{issuer_name}:{user_email}?secret={secret_key}&issuer={issuer_name}"
            qr_code_img = generate_qr_code(otp_url)

        elif methods.get("disabled"):
            [device.delete() for device in devices]

        device = next(iter(devices_for_user(user)))
        response = {
            "methods": {
                "disabled": bool(not device),
                "email": bool(device and type(device) == EmailDevice),
                "token": bool(device and type(device) == TOTPDevice),
            }
        }
        if qr_code_img:
            response["qr_code"] = qr_code_img

        return JsonResponse(response)

    @api_endpoint_class
    @action(detail=False, methods=["POST"])
    def resend_token_email(self, request):
        """
        Resends the token email to the user
        """
        user_email = request.data.get("user_email")
        user = User.objects.get(email=user_email)
        device = next(iter(devices_for_user(user)))
        if not device or type(device) != EmailDevice:
            return JsonResponse({"message": "Email two factor authentication not configured"})

        send_token_email(device)
        return JsonResponse({"message": "Token email sent"})

    @api_endpoint_class
    @action(detail=False, methods=["POST"])
    def generate_qr_code(self, request):
        """
        Generates a QR code to be verified before setting the 2 factor method.
        """
        user_email = request.data.get("user_email")

        secret_key = pyotp.random_base32()
        request.session["otp_secret_key"] = secret_key

        issuer_name = "SEED-Platform"
        otp_url = f"otpauth://totp/{issuer_name}:{user_email}?secret={secret_key}&issuer={issuer_name}"
        qr_code_img = generate_qr_code(otp_url)

        return JsonResponse({"qr_code": qr_code_img})

    @api_endpoint_class
    @action(detail=False, methods=["POST"])
    def verify_code(self, request):
        """
        Verifies an authenticator app code. A session secret key is required to validate the device
        """
        secret_key = request.session["otp_secret_key"]
        if not secret_key:
            return JsonResponse({"message": "Invalid request. Missing secret key"})

        # secret key needs to be converted to hex
        key_bytes = base64.b32decode(secret_key, casefold=True)
        hex_key = binascii.hexlify(key_bytes).decode("utf-8")

        user_email = request.data.get("user_email")
        code = request.data.get("code")
        user = SEEDUser.objects.get(email=user_email)

        totp = pyotp.TOTP(secret_key)
        device = None
        if totp.verify(code):
            devices = list(devices_for_user(user))
            device = TOTPDevice.objects.create(user=user, name="default", confirmed=True, key=hex_key)
            if device:
                [device.delete() for device in devices]

                return JsonResponse({"success": True})
            return JsonResponse({"error": "Unexpected Error"})
        else:
            return JsonResponse({"error": "Unexpected Error"})
