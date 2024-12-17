"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models
from django.db.models import Q
from model_utils.managers import InheritanceManager
from quantityfield.fields import QuantityField
from quantityfield.units import ureg

from seed.models import InventoryGroup

ureg.define("MMBtu = 1e6 * Btu")
ureg.define("Ton = 12000 * Btu / hour")


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
    heating_capacity = QuantityField("MMBtu", null=True)
    cooling_capacity = QuantityField("Ton", null=True)
    count = models.IntegerField(default=1, null=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(heating_capacity__isnull=False) | Q(cooling_capacity__isnull=False), name="heating_or_cooling_capacity_required"
            )
        ]


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
    power = QuantityField("kW", null=False)
    voltage = QuantityField("V", null=False)
    count = models.IntegerField(default=1, null=False)


class BatterySystem(System):
    efficiency = models.FloatField(null=False)
    power_capacity = QuantityField("kW", null=False)
    energy_capacity = QuantityField("kWh", null=False)
    voltage = QuantityField("V", null=False)


class Service(models.Model):
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    emission_factor = models.FloatField(null=True)

    objects = InheritanceManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["system", "name"], name="unique_name_for_system"),
        ]
