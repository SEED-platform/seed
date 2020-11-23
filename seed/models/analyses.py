from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import AnalysisTypes


class Analysis(models.Model):
    """
    The Analysis represents an analysis performed on one or more properties.
    """
    service = models.IntegerField(choices=AnalysisTypes.SERVICES)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=AnalysisTypes.STATUS)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    configuration = JSONField(default=dict, blank=True)
    # parsed_results can contain any results gathered from the resulting file(s)
    # that are applicable to the entire analysis (ie all properties involved).
    # For property-specific results, use the AnalysisPropertyView's parsed_results
    parsed_results = JSONField(default=dict, blank=True)
