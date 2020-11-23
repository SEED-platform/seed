from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import AnalysisTypes


class Analysis(models.Model):

    service = models.IntegerField(choices=AnalysisTypes.SERVICES)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=AnalysisTypes.STATUS)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    configuration = JSONField(default=dict, blank=True)
    parsed_results = JSONField(default=dict, blank=True)
