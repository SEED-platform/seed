from django.contrib import admin

from seed.models import (
    Column,
    Property, 
    PropertyView, 
    PropertyState,
    Cycle,
    TaxLot,
    TaxLotView,
    TaxLotState,
    TaxLotProperty,
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
