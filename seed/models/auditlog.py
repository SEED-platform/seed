from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from seed.models import Property
from seed.models import PropertyView
from seed.models import PropertyState

from seed.models import TaxLot
from seed.models import TaxLotView
from seed.models import TaxLotState


class PropertyAuditLog(models.Model):
    parent1 = models.ForeignKey('PropertyState', blank=True, null=True, related_name='propertyauditlog__parent1')
    parent2 = models.ForeignKey('PropertyState', blank=True, null=True, related_name='propertyauditlog__parent2')
    child = models.ForeignKey('PropertyState', related_name='propertyauditlog__child')
    creation_date = models.DateTimeField()
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)


class TaxLotAuditLog(models.Model):
    parent1 = models.ForeignKey('TaxLotState', blank=True, null=True, related_name='taxlotauditlog__parent1')
    parent2 = models.ForeignKey('TaxLotState', blank=True, null=True, related_name='taxlotauditlog__parent2')
    child = models.ForeignKey('TaxLotState', related_name='taxlotauditlog__child')
    creation_date = models.DateTimeField()
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
