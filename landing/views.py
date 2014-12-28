"""
:copyright: (c) 2014 Building Energy Inc
"""
from annoying.decorators import render_to
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.util import ErrorList
from django.forms.forms import NON_FIELD_ERRORS
from django.http import HttpResponseRedirect
from django.template.context import RequestContext
from django.shortcuts import render_to_response

from tos.models import (
    has_user_agreed_latest_tos, TermsOfService, NoActiveTermsOfService
)

from landing.forms import LoginForm, SetStrongPasswordForm

import logging
logger = logging.getLogger(__name__)


@render_to('landing/home.html')
def landing_page(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('seed:home'))
    login_form = LoginForm()
    return locals()


def _login_view(request):
    """
    Standard Django login, with additions:
        Lowercase the login email (username)
        Check user has accepted ToS, if any.
    """
    if request.method == "POST":
        redirect_to = request.REQUEST.get('next', False)
        if not redirect_to:
            redirect_to = reverse('seed:home')

        form = LoginForm(request.POST)
        if form.is_valid():
            new_user = authenticate(
                username=form.cleaned_data['email'].lower(),
                password=form.cleaned_data['password']
            )
            if new_user and new_user.is_active:
                #determine if user has accepted ToS, if one exists
                try:
                    user_accepted_tos = has_user_agreed_latest_tos(new_user)
                except NoActiveTermsOfService:
                    #there's no active ToS, skip interstitial
                    user_accepted_tos = True

                if user_accepted_tos:
                    login(request, new_user)
                    return HttpResponseRedirect(redirect_to)
                else:
                    # store login info for django-tos to handle
                    request.session['tos_user'] = new_user.pk
                    request.session['tos_backend'] = new_user.backend
                    context = RequestContext(request)
                    context.update({
                        'next': redirect_to,
                        'tos': TermsOfService.objects.get_current_tos()
                    })
                    return render_to_response(
                        'tos/tos_check.html',
                        context_instance=context
                    )
            else:
                errors = ErrorList()
                errors = form._errors.setdefault(NON_FIELD_ERRORS, errors)
                errors.append('Username and/or password were invalid.')
    else:
        form = LoginForm()

    return locals()
login_view = render_to('landing/login.html')(_login_view)


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
        is_admin_site=True,
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
        set_password_form=SetStrongPasswordForm,
        post_reset_redirect=reverse('landing:password_reset_complete')
    )


@render_to("landing/password_reset_complete.html")
def password_reset_complete(request):
    return locals()


def signup(request, uidb64=None, token=None):
    return auth.views.password_reset_confirm(
        request,
        uidb64=uidb64,
        token=token,
        template_name='landing/signup.html',
        set_password_form=SetStrongPasswordForm,
        post_reset_redirect=reverse('landing:landing_page') + "?setup_complete"
    )
