"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models
from model_utils.managers import InheritanceManager

from seed.models import InventoryGroup


class System(models.Model):
    name = models.CharField(max_length=255)
    group = models.ForeignKey(InventoryGroup, on_delete=models.CASCADE, related_name="systems")
    objects = InheritanceManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["group", "name"], name="unique_name_for_group"),
        ]


class DESSystem(System):
    BOILER = 0
    CHILLER = 1
    CHP = 2

    DES_TYPES = (
        (BOILER, "Boiler"),
        (CHILLER, "Chiller"),
        (CHP, "CHP"),
    )
    type = models.IntegerField(choices=DES_TYPES, null=False)
    capacity = models.IntegerField(null=False)
    count = models.IntegerField(default=1, null=False)


class EVSESystem(System):
    LEVEL1 = 0
    LEVEL2 = 1
    LEVEL3 = 2

    EVSE_TYPES = (
        (LEVEL1, "Level1-120V"),
        (LEVEL2, "Level2-240V"),
        (LEVEL3, "Level3-DC Fast"),
    )
    type = models.IntegerField(choices=EVSE_TYPES, null=False)
    power = models.IntegerField(null=False)
    count = models.IntegerField(default=1, null=False)


class BatterySystem(System):
    efficiency = models.IntegerField(null=False)
    capacity = models.IntegerField(null=False)
    voltage = models.IntegerField(null=False)


class Service(models.Model):
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    emission_factor = models.IntegerField(null=True)

    objects = InheritanceManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["system", "name"], name="unique_name_for_system"),
        ]
