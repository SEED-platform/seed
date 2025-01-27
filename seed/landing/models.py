"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import base64
import hmac
import re
import uuid
from urllib.parse import quote

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from seed.lib.superperms.orgs.models import Organization

# sha1 used for api_key creation, but may vary by python version
try:
    from hashlib import sha1
except ImportError:
    import sha

    sha1 = sha.sha


class SEEDUser(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username, password and email are required. Other fields are optional.
    """

    username = models.EmailField(_("username (email)"), unique=True, help_text=_("User's email address.  Used for auth as well."))
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=30, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"), default=False, help_text=_("Designates whether the user can log into this admin site.")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    default_custom_columns = models.JSONField(default=dict)
    default_building_detail_custom_columns = models.JSONField(default=dict)
    show_shared_buildings = models.BooleanField(_("active"), default=False, help_text=_("shows shared buildings within search results"))
    default_organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True, related_name="default_users")
    api_key = models.CharField(_("api key"), max_length=128, blank=True, default="", db_index=True)
    prompt_2fa = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    @classmethod
    def process_header_request(cls, request):
        """
        Process the header string to return the user if it is a valid user.

        :param request: object, request object with HTTP Authorization
        :return: User object
        """
        auth_header = request.META.get("Authorization")

        if not auth_header:
            auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not auth_header:
            return None

        try:
            if auth_header.startswith("Basic"):
                auth_header = auth_header.split()[1]
                auth_header = base64.urlsafe_b64decode(auth_header).decode("utf-8")
                username, api_key = auth_header.split(":")

                valid_api_key = re.search("^[a-f0-9]{40}$", api_key)
                if not valid_api_key:
                    raise exceptions.AuthenticationFailed("Invalid API key")

                user = SEEDUser.objects.get(api_key=api_key, username=username)
                return user
            elif auth_header.startswith("Bearer"):
                at = AccessToken(auth_header.removeprefix("Bearer "))
                user = SEEDUser.objects.get(pk=at["user_id"])
                return user
            else:
                raise exceptions.AuthenticationFailed("Only Basic HTTP_AUTHORIZATION or BEARER Tokens are supported")
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid HTTP_AUTHORIZATION Header")
        except TokenError:
            raise exceptions.AuthenticationFailed("Invalid Bearer Token")
        except SEEDUser.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key or Bearer Token")

    def get_absolute_url(self):
        return f"/users/{quote(self.username)}/"

    def deactivate_user(self):
        self.is_active = False
        self.save()

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """
        Returns the short name for the user.
        """
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

        https://github.com/toastdriven/django-tastypie/blob/master/tastypie/models.py#L47
        """
        new_uuid = uuid.uuid4()
        api_key = hmac.new(new_uuid.bytes, digestmod=sha1).hexdigest()
        self.api_key = api_key
        self.save()

    def save(self, *args, **kwargs):
        """
        Ensure that email and username are synced.
        """

        # NL: Why are we setting the email to the username, don't we need the
        # email? It seems that the username is then supposed to be the email,
        # correct? Regardless, this code seems problematic
        if self.email.lower() != self.username:
            self.email = self.username
        return super().save(*args, **kwargs)
