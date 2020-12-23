"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

"""
from django.db import models
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from post_office.models import EmailTemplate, Email

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
