# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
import logging
import urllib

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from seed.landing.models import SEEDUser
from seed.tasks import invite_new_user_to_seed

from .forms import CustomCreateUserForm, LoginForm

logger = logging.getLogger(__name__)


def landing_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('seed:home'))
    request.user = {
        'first_name': '',
        'last_name': '',
        'email': ''
    }
    return render(request, 'landing/home.html', {
        'context': {'self_registration': settings.INCLUDE_ACCT_REG},
        'debug': settings.DEBUG,
        'initial_org_id': 0,
        'initial_org_user_role': 0,
        'initial_org_name': '',
        'login_form': LoginForm(),
        'username': ''
    })


def login_view(request):
    """
    Standard Django login, with additions:
        Lowercase the login email (username)
        Check user has accepted ToS, if any.
    """
    if request.method == "POST":
        redirect_to = request.POST.get('next', request.GET.get('next', False))
        if not redirect_to:
            redirect_to = reverse('seed:home')

        form = LoginForm(request.POST)
        if form.is_valid():
            new_user = authenticate(
                username=form.cleaned_data['email'].lower(),
                password=form.cleaned_data['password']
            )
            if new_user is not None and new_user.is_active:
                # TODO: the ToS haven't worked for awhile, renewable?
                # determine if user has accepted ToS, if one exists
                # try:
                #     user_accepted_tos = has_user_agreed_latest_tos(new_user)
                # except NoActiveTermsOfService:
                #     there's no active ToS, skip interstitial
                # user_accepted_tos = True
                #
                # if user_accepted_tos:
                login(request, new_user)
                return HttpResponseRedirect(redirect_to)
                # else:
                #     store login info for django-tos to handle
                # request.session['tos_user'] = new_user.pk
                # request.session['tos_backend'] = new_user.backend
                # context = RequestContext(request)
                # context.update({
                #     'next': redirect_to,
                #     'tos': TermsOfService.objects.get_current_tos()
                # })
                # return render(request, 'tos/tos_check.html', context)
            else:
                errors = ErrorList()
                errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                errors.append('Username and/or password were invalid.')
                logger.error(f"User login failed: {form.cleaned_data['email']}")
    else:
        form = LoginForm()

    # prepare the render request
    request.user = {
        'first_name': '',
        'last_name': '',
        'email': ''
    }
    return render(request, 'landing/login.html', {
        'context': {'self_registration': settings.INCLUDE_ACCT_REG},
        'debug': settings.DEBUG,
        'initial_org_id': 0,
        'initial_org_user_role': 0,
        'initial_org_name': '',
        'form': form,
        'username': ''
    })


def password_set(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name='landing/password_set.html')(
        request,
        uidb64=uidb64,
        token=token,
        post_reset_redirect=reverse('landing:password_set_complete')
    )


def password_reset(request):
    return auth.views.PasswordResetView.as_view(template_name='landing/password_reset.html')(
        request,
        subject_template_name='landing/password_reset_subject.txt',
        email_template_name='landing/password_reset_email.html',
        post_reset_redirect=reverse('landing:password_reset_done'),
        from_email=settings.PASSWORD_RESET_EMAIL,
    )


def password_reset_done(request):
    return auth.views.PasswordResetDoneView.as_view(
        template_name='landing/password_reset_done.html'
    )(request)


def password_reset_confirm(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name='landing/password_reset_confirm.html')(
        request,
        uidb64=uidb64,
        token=token,
        set_password_form=SetPasswordForm,
        success_url=reverse('landing:password_reset_complete')
    )


def password_reset_complete(request):
    return render(request, 'landing/password_reset_complete.html', {'debug': settings.DEBUG})


def signup(request, uidb64=None, token=None):
    return auth.views.PasswordResetConfirmView.as_view(template_name='landing/signup.html')(
        request,
        uidb64=uidb64,
        token=token,
        set_password_form=SetPasswordForm,
        post_reset_redirect=reverse('landing:landing_page') + "?setup_complete"
    )


def create_account(request):
    if request.method == "POST":
        redirect_to = request.POST.get('next', request.GET.get('next', False))
        if not redirect_to:
            redirect_to = reverse('seed:home')
        form = CustomCreateUserForm(request.POST)
        errors = ErrorList()
        if form.is_valid():
            ''' Begin reCAPTCHA validation '''
            recaptcha_response = request.POST.get('g-recaptcha-response')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            data = urllib.parse.urlencode(values).encode()
            req = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode())
            ''' End reCAPTCHA validation '''
            if result['success']:
                user = form.save(commit=False)
                user.username = user.username.lower()
                user.is_active = False
                try:
                    user.save()
                    try:
                        domain = request.get_host()
                    except Exception:
                        domain = 'seed-platform.org'
                    invite_new_user_to_seed(
                        domain, user.email, default_token_generator.make_token(user),
                        user.pk, user.email
                    )
                    return redirect('landing:account_activation_sent')
                except Exception as e:
                    logger.error(f'Unexpected error creating new account: {str(e)}')
                    errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                    errors.append('An unexpected error occurred. Please contact the site administrator.')
            else:
                errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                errors.append('Invalid reCAPTCHA, please try again')
        else:
            errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
            errors.append('Username and/or password were invalid.')

    else:
        form = CustomCreateUserForm()
    debug = settings.DEBUG
    return render(request, 'landing/create_account.html', locals())


def account_activation_sent(request):
    return render(request, 'landing/account_activation_sent.html', {'debug': settings.DEBUG})


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
        return HttpResponseRedirect(reverse('seed:home'))
    else:
        return render(request, 'account_activation_invalid.html', {'debug': settings.DEBUG})
