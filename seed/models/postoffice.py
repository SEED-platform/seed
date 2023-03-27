"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models
from post_office.models import Email, EmailTemplate

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization

# We create our own models replicating EmailTemplate and Email from post_office
# and adding columns for organization id and user id


class PostOfficeEmail(Email):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return 'PostOfficeEmail - %s' % self.pk


class PostOfficeEmailTemplate(EmailTemplate):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return 'PostOfficeEmailTemplate - %s' % self.pk
