# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from seed.models import PropertyState, TaxLotState


class UbidModel(models.Model):
    ubid = models.CharField(max_length=255, null=False, blank=False)
    property = models.ForeignKey(PropertyState, on_delete=models.CASCADE, null=True)
    taxlot = models.ForeignKey(TaxLotState, on_delete=models.CASCADE, null=True)
    preferred = models.BooleanField(default=False)


@receiver(post_save, sender=UbidModel)
def post_save_ubid_model(sender, **kwargs):
    """
    update State.ubid for the preferred ubid
    """
    instance = kwargs.get('instance')
    if not instance or not instance.preferred:
        return

    if getattr(instance, 'property'):
        property = instance.property
        property.ubid = instance.ubid
        property.save()

    elif getattr(instance, 'taxlot'):
        taxlot = instance.taxlot
        taxlot.ubid = instance.ubid
        taxlot.save()


@receiver(pre_delete, sender=UbidModel)
def pre_delete_ubid_model(sender, **kwargs):
    """
    If a preferred ubid is deleted, remove the state.ubid
    """
    instance = kwargs.get('instance')
    if not instance or not instance.preferred:
        return

    if getattr(instance, 'property'):
        property = instance.property
        property.ubid = None
        property.save()

    elif getattr(instance, 'taxlot'):
        taxlot = instance.taxlot
        taxlot.ubid = None
        taxlot.save()
