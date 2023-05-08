"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import PropertyState, TaxLotState 

class Ubid(models.Model):
    ubid = models.CharField(max_length=255, null=False)
    property = models.ForeignKey(PropertyState, on_delete=models.CASCADE, null=True, related_name="ubid_set")
    taxlot = models.ForeignKey(TaxLotState, on_delete=models.CASCADE, null=True, related_name="ubid_set")
    preferred = models.BooleanField(default=False)
