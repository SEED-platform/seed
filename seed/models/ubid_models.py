# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from seed.models import PropertyState, TaxLotState
from seed.utils.ubid import decode_unique_ids


class UbidModel(models.Model):
    ubid = models.CharField(max_length=255, null=False, blank=False)
    property = models.ForeignKey(PropertyState, on_delete=models.CASCADE, null=True)
    taxlot = models.ForeignKey(TaxLotState, on_delete=models.CASCADE, null=True)
    preferred = models.BooleanField(default=False)

    class Meta:
        # Two partial indexes to handle uniqueness with null values
        constraints = [
            models.UniqueConstraint(
                fields=['ubid', 'property_id'],
                name='unique_ubid_for_property',
                condition=Q(taxlot_id__isnull=True)
            ),
            models.UniqueConstraint(
                fields=['ubid', 'taxlot_id'],
                name='unique_ubid_for_taxlot',
                condition=Q(property_id__isnull=True)
            ),
        ]


@receiver(post_save, sender=UbidModel)
def post_save_ubid_model(sender, **kwargs):
    """
    Update state.ubid for the preferred UBID
    """
    ubid_model: UbidModel = kwargs.get('instance')
    state = ubid_model.property or ubid_model.taxlot
    if ubid_model.preferred and state.ubid != ubid_model.ubid:
        state.ubid = ubid_model.ubid
        state.save()
        decode_unique_ids(state)
    elif not ubid_model.preferred and state.ubid == ubid_model.ubid:
        state.ubid = None
        state.save()


@receiver(pre_delete, sender=UbidModel)
def pre_delete_ubid_model(sender, **kwargs):
    """
    If a preferred ubid is deleted, remove the state.ubid
    """
    ubid_model: UbidModel = kwargs.get('instance')
    if ubid_model.preferred:
        state = ubid_model.property or ubid_model.taxlot
        state.ubid = None
        state.save()
