"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models


class Uniformat(models.Model):
    code = models.CharField(max_length=7, unique=True, help_text="The code representing the current Uniformat category")
    category = models.CharField(
        max_length=100,
        help_text="Represents the broad classification of the building element, indicating its general type or function within the construction process",
    )
    definition = models.CharField(
        max_length=1024, null=True, help_text="A detailed explanation of the category, outlining its components, functions, and scope"
    )
    imperial_units = models.CharField(
        max_length=10, null=True, help_text="Specifies the unit of measurement used for quantifying the item in the Imperial system"
    )
    metric_units = models.CharField(
        max_length=10, null=True, help_text="Specifies the unit of measurement used for quantifying the item in the Metric system"
    )
    quantity_definition = models.CharField(
        max_length=100,
        null=True,
        help_text="Defines how the quantity of the item is measured and expressed, providing context for interpreting the units",
    )
    parent = models.ForeignKey(
        "self", null=True, on_delete=models.CASCADE, help_text="The higher-level Uniformat category that the current category is a child of"
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code
