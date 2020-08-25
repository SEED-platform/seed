from django.db import models
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from post_office.models import EmailTemplate, Email

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