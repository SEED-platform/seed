# !/usr/bin/env python
# encoding: utf-8

from django.db.models import Manager
from django.db.models.query import QuerySet


class JsonQuerySet(QuerySet):
    PRIMARY = 'extra_data'
    TABLE = 'seed_buildingsnapshot'

    def _safe_cast(self, cast_fn, val):
        try:
            return cast_fn(val)
        except TypeError:
            return val

    def json_order_by(self, key, order_by, order_by_rev=False, unit=None):
        from seed.models import FLOAT, DECIMAL, STRING

        def get_field(x):
            return getattr(x, self.PRIMARY).get(order_by, None)

        unit_type = STRING
        if unit:
            unit_type = unit.unit_type

        qs = self
        qs = list(qs)

        key_fns = {
            STRING: get_field,
            FLOAT: lambda x: self._safe_cast(float, get_field(x)),
            DECIMAL: lambda x: self._safe_cast(float, get_field(x)),
        }

        qs.sort(
            key=key_fns.get(unit_type, get_field),
            reverse=order_by_rev,
        )

        return qs


class JsonManager(Manager):

    def get_queryset(self):
        return JsonQuerySet(model=self.model, using=self._db)
