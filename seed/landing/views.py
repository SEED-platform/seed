# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging
import urllib

from django.core.cache import cache
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django_otp import devices_for_user
from django_otp.plugins.otp_email.models import EmailDevice
from two_factor.views.core import LoginView, SetupView

from seed.landing.models import SEEDUser
from seed.tasks import invite_new_user_to_seed
from seed.utils.two_factor import send_token_email

from .forms import CustomCreateUserForm

logger = logging.getLogger(__name__)


def landing_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("seed:home"))
    else:
        return redirect("two_factor:login")


def password_set(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name="landing/password_set.html")(
        request, uidb64=uidb64, token=token, post_reset_redirect=reverse("landing:password_set_complete")
    )


def password_reset(request):
    return auth.views.PasswordResetView.as_view(template_name="landing/password_reset.html")(
        request,
        subject_template_name="landing/password_reset_subject.txt",
        email_template_name="landing/password_reset_email.html",
        post_reset_redirect=reverse("landing:password_reset_done"),
        from_email=settings.PASSWORD_RESET_EMAIL,
    )


def password_reset_done(request):
    return auth.views.PasswordResetDoneView.as_view(template_name="landing/password_reset_done.html")(request)


def password_reset_confirm(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name="landing/password_reset_confirm.html")(
        request, uidb64=uidb64, token=token, set_password_form=SetPasswordForm, success_url=reverse("landing:password_reset_complete")
    )


def password_reset_complete(request):
    return render(request, "landing/password_reset_complete.html", {"debug": settings.DEBUG})


def signup(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name="landing/signup.html")(
        request,
        uidb64=uidb64,
        token=token,
        set_password_form=SetPasswordForm,
        post_reset_redirect=reverse("landing:login") + "?setup_complete",
    )


def create_account(request):
    if request.method == "POST":
        redirect_to = request.POST.get("next", request.GET.get("next", False))
        if not redirect_to:
            redirect_to = reverse("seed:home")
        form = CustomCreateUserForm(request.POST)
        errors = ErrorList()
        if form.is_valid():
            """ Begin reCAPTCHA validation """
            recaptcha_response = request.POST.get("g-recaptcha-response")
            url = "https://www.google.com/recaptcha/api/siteverify"
            values = {"secret": settings.GOOGLE_RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
            data = urllib.parse.urlencode(values).encode()
            req = urllib.request.Request(url, data=data)  # noqa: S310
            response = urllib.request.urlopen(req)  # noqa: S310
            result = json.loads(response.read().decode())
            """ End reCAPTCHA validation """
            if result["success"]:
                user = form.save(commit=False)
                user.username = user.username.lower()
                user.is_active = False
                try:
                    user.save()
                    try:
                        domain = request.get_host()
                    except Exception:
                        domain = "seed-platform.org"
                    invite_new_user_to_seed(domain, user.email, default_token_generator.make_token(user), user.pk, user.email)
                    return redirect("landing:account_activation_sent")
                except Exception as e:
                    logger.error(f"Unexpected error creating new account: {e!s}")
                    errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                    errors.append("An unexpected error occurred. Please contact the site administrator.")
            else:
                errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                errors.append("Invalid reCAPTCHA, please try again")
        else:
            errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
            errors.append("Username and/or password were invalid.")

    else:
        form = CustomCreateUserForm()
    debug = settings.DEBUG
    return render(request, "landing/create_account.html", locals())


def account_activation_sent(request):
    return render(request, "landing/account_activation_sent.html", {"debug": settings.DEBUG})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = SEEDUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, SEEDUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return HttpResponseRedirect(reverse("seed:home"))
    else:
        return render(request, "account_activation_invalid.html", {"debug": settings.DEBUG})


class CustomLoginView(LoginView):

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        logging.error("POST")
        if "resend_email" in request.POST:
            try:
                user = SEEDUser.objects.get(username=cache.get('username'))
                device = list(devices_for_user(user))[0]
                if type(device) == EmailDevice:
                    send_token_email(device)
            except SEEDUser.DoesNotExist:
                pass
        if response.status_code not in [200, 302]:
            return response
        current_step = request.POST.get("custom_login_view-current_step")
        if current_step == "auth":
            return self.handle_auth(request, response)
        elif current_step == "token":
            return self.handle_token(request, response)
        return response

    def handle_auth(self, request, response):
        user = SEEDUser.objects.filter(username=request.POST["auth-username"]).first()
        cache.set("username", user.username, timeout=3000)

        if not user or list(devices_for_user(user)):
            return response  # retry or proceed to token step
        return self.handle_2fa_prompt(response, user)

    def handle_token(self, request, response):
        token = request.POST.get("token-otp_token")
        user = request.user

        if not token or not user.is_authenticated:
            return response  # retry form
        return self.handle_2fa_prompt(response, user)

    def handle_2fa_prompt(self, response, user):
        # django-two-factor-auth will always try to redirect users to the 2 factor profile.
        # override and send users home if they have already been prompted.
        if not getattr(user, "prompt_2fa", False) and isinstance(response, HttpResponseRedirect):
            return HttpResponseRedirect(reverse("seed:home"))
        else:
            user.prompt_2fa = False
            user.save()
        return response

    def get(self, request, *args, **kwargs):
        # add env var to session for conditional frontend display
        logging.error(">>> GET")
        request.session["include_acct_reg"] = settings.INCLUDE_ACCT_REG
        return super().get(request, *args, **kwargs)

# THIS DOESNT WORK.
class CustomSetupView(SetupView):

    def get(self, request, *args, **kwargs):
        logging.error('get')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logging.error('post')
        return super().post(request, *args, **kwargs)