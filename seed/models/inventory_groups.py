# encoding: utf-8

from __future__ import unicode_literals

from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models.properties import Property
from seed.models.tax_lots import TaxLot

VIEW_LIST_PROPERTY = 0
VIEW_LIST_TAXLOT = 1
VIEW_LIST_INVENTORY_TYPE = [
    (VIEW_LIST_PROPERTY, 'Property'),
    (VIEW_LIST_TAXLOT, 'Tax Lot'),
]


class InventoryGroup(models.Model):
    name = models.CharField(max_length=255)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ['name']


class InventoryGroupMapping(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, blank=True, null=True)
    tax_lot = models.ForeignKey(TaxLot, on_delete=models.CASCADE, blank=True, null=True)
    group = models.ForeignKey(InventoryGroup, on_delete=models.CASCADE)
