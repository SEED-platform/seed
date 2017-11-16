# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import SetPasswordForm
from django.core.urlresolvers import reverse
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import render
# from django.template.context import RequestContext
# from tos.models import (
#     has_user_agreed_latest_tos, TermsOfService, NoActiveTermsOfService
# )

from forms import LoginForm

logger = logging.getLogger(__name__)


def landing_page(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('seed:home'))
    login_form = LoginForm()
    return render(request, 'landing/home.html', locals())


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
                # TODO: the ToS haven't worked for awhile, reneable?
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
    else:
        form = LoginForm()

    return render(request, 'landing/login.html', locals())


def password_set(request, uidb64=None, token=None):
    return auth.views.password_reset_confirm(
        request,
        uidb64=uidb64,
        token=token,
        template_name='landing/password_set.html',
        post_reset_redirect=reverse('landing:password_set_complete')
    )


def password_reset(request):
    return auth.views.password_reset(
        request, template_name='landing/password_reset.html',
        subject_template_name='landing/password_reset_subject.txt',
        email_template_name='landing/password_reset_email.html',
        post_reset_redirect=reverse('landing:password_reset_done'),
        from_email=settings.PASSWORD_RESET_EMAIL,
    )


def password_reset_done(request):
    return auth.views.password_reset_done(
        request,
        template_name='landing/password_reset_done.html'
    )


def password_reset_confirm(request, uidb64=None, token=None):
    return auth.views.password_reset_confirm(
        request,
        uidb64=uidb64,
        token=token,
        template_name='landing/password_reset_confirm.html',
        set_password_form=SetPasswordForm,
        post_reset_redirect=reverse('landing:password_reset_complete')
    )


def password_reset_complete(request):
    return render(request, 'landing/password_reset_complete.html', {})


def signup(request, uidb64=None, token=None):
    return auth.views.password_reset_confirm(
        request,
        uidb64=uidb64,
        token=token,
        template_name='landing/signup.html',
        set_password_form=SetPasswordForm,
        post_reset_redirect=reverse('landing:landing_page') + "?setup_complete"
    )
