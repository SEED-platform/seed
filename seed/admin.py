"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.contrib import admin

from seed.models import (
    Column,
    Cycle,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotProperty,
    TaxLotState,
    TaxLotView
)

admin.site.register(Column)
admin.site.register(Property)
admin.site.register(PropertyView)
admin.site.register(PropertyState)
admin.site.register(Cycle)
admin.site.register(TaxLot)
admin.site.register(TaxLotView)
admin.site.register(TaxLotState)
admin.site.register(TaxLotProperty)
