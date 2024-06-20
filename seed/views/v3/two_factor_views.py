import logging
from seed.landing.models import SEEDUser
from rest_framework.decorators import action
from django.http import JsonResponse
from django_otp import devices_for_user
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.viewsets import ModelViewSetWithoutPatch
from seed.utils.two_factor import send_token_email, generate_qr_code


class TwoFactorViewSet(ModelViewSetWithoutPatch):

    @api_endpoint_class
    @has_perm_class("can_modify_data")
    @action(detail=False, methods=["POST"])
    def set_method(self, request):
        logging.error(">>> A")
        user_email = request.data.get("user_email")
        methods = request.data.get("methods")
        if all(method is False for method in methods.values()):
            return JsonResponse({
                "status": "error",
                "message": "Unexpected Error"
            })

        user = User.objects.get(email=user_email)

        devices = list(devices_for_user(user))
        email_active = bool(devices and type(devices[0]) == EmailDevice)
        token_active = bool(devices and type(devices[0]) == TOTPDevice)
        qr_code = None
        # token_active = type(devices[0]) == Token?
        if methods.get("email") and not email_active:
            email_device = EmailDevice.objects.create(
                user=user,
                name='default',
                email=user.username
            )
            if email_device:
                [device.delete() for device in devices]
                # just for user confirmation
                send_token_email(email_device)

        elif methods.get("token") and not token_active:
                qr_code = generate_qr_code(user, devices)

        elif methods.get("disabled"):
            logging.error('disabled')
            [device.delete() for device in devices]

        # temporary return for debugging
        devices = list(devices_for_user(user))
        logging.error('>>> devices %s', devices)

        response = {
            "methods": {
                "disabled": bool(not devices),
                "email": bool(devices and type(devices[0]) == EmailDevice),
                "token": bool(devices and type(devices[0]) == TOTPDevice)
            }
        }
        if qr_code:
            response["qr_code"] = qr_code

        logging.error(">>> B")

        return JsonResponse(response)    
    
    @api_endpoint_class
    @action(detail=False, methods=["POST"])
    def resend_token_email(self, request):
        user_email = request.data.get("user_email")
        user = User.objects.get(email=user_email)
        devices = list(devices_for_user(user))
        if not devices or type(devices[0]) != EmailDevice:
            return JsonResponse({"Message": "Email two factor authentication not configured"})
        
        send_token_email(devices[0])
        return JsonResponse({"Message": "Token email sent"})
        
    @api_endpoint_class
    @action(detail=False, methods=["POST"])
    def generate_qr_code(self, request):
        user_email = request.data.get("user_email")
        user = User.objects.get(email=user_email)
        devices = list(devices_for_user(user))
        if not devices or type(devices[0]) != TOTPDevice:
            return JsonResponse({"Message": "Token Generator two factor authentication not configured"})
        
        qr_code = generate_qr_code(user, devices)
        return JsonResponse({"qr_code": qr_code})   
