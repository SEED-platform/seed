# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import uuid
import hmac
# sha1 used for api_key creation, but may vary by python version
try:
    from hashlib import sha1
except ImportError:
    import sha
    sha1 = sha.sha

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    UserManager,
    # SiteProfileNotAvailable
)
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db import models
from django.utils.http import urlquote
from django.core.mail import send_mail

from django_pgjson.fields import JsonField

from seed.lib.superperms.orgs.models import Organization


class SEEDUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username, password and email are required. Other fields are optional.
    """
    username = models.EmailField(
        _('username (email)'), unique=True,
        help_text=_('User\'s email address.  Used for auth as well.'))
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(
        _('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(
        _('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    default_custom_columns = JsonField(default={})
    default_building_detail_custom_columns = JsonField(default={})
    show_shared_buildings = models.BooleanField(
        _('active'), default=False,
        help_text=_('shows shared buildings within search results'))
    default_organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        related_name='default_users'
    )
    api_key = models.CharField(
        _('api key'),
        max_length=128,
        blank=True,
        default='',
        db_index=True
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_absolute_url(self):
        return "/users/%s/" % urlquote(self.username)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])

    def generate_key(self):
        """
        Creates and sets an API key for this user.
        Adapted from tastypie:

        https://github.com/toastdriven/django-tastypie/blob/master/tastypie/models.py#L47  # noqa
        """
        new_uuid = uuid.uuid4()
        api_key = hmac.new(new_uuid.bytes, digestmod=sha1).hexdigest()
        self.api_key = api_key
        self.save()

    def save(self, *args, **kwargs):
        """
        Ensure that email and username are synced.
        """

        # NL: Why are we setting the email to the user name, don't we need the
        # email? It seems that the username is then suppose to be the email,
        # correct? Regardless, this code seems problematic
        if self.email.lower() != self.username:
            self.email = self.username
        return super(SEEDUser, self).save(*args, **kwargs)
