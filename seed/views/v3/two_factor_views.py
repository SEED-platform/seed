import logging
from rest_framework.decorators import action
from django.http import JsonResponse
from django_otp import devices_for_user
from django_otp.plugins.otp_email.models import EmailDevice

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.viewsets import ModelViewSetWithoutPatch
from seed.utils.two_factor import send_token_email


class TwoFactorViewSet(ModelViewSetWithoutPatch):

    @api_endpoint_class
    @has_perm_class("can_modify_data")
    @action(detail=False, methods=["POST"])
    def set_method(self, request):
        user_email = request.data.get("user_email")
        methods = request.data.get("methods")

        user = User.objects.get(email=user_email)

        devices = list(devices_for_user(user))
        email_active = bool(devices and type(devices[0]) == EmailDevice)
        # token_active = type(devices[0]) == Token?

        if methods["email"] and not email_active:
            email_device = EmailDevice.objects.create(
                user=user,
                name='default',
                email=user.username
            )
            # not totally necessary here
            send_token_email(email_device)

        elif not methods["email"] and email_active:
            devices[0].delete()

        # temporary return for debugging
        devices = list(devices_for_user(user))
        if devices:
            email_active = type(devices[0]) == EmailDevice
        else:
            email_active = False

        return JsonResponse({"email_active": email_active})
    
    # @api_endpoint_class
    # @action(detail=False, methods=["POST"])
    # def resend_email_token(self, request):
    #     import remote_pdb; remote_pdb.set_trace()
    #     return