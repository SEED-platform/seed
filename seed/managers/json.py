# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

Query JSON data from Postgres JsonFields.

::

    BuildingSnapshot.objects.json_query(key='something')
    BuildingSnapshot.objects.json_query(
        key='thing', cond=">", value="2342", key_cast=int
    )

    BuildingSnapshot.objects.json_query(
        key='Natural Gas Use (kBtu)', excludes=['Not Available']
    )

    BuildingSnapshot.objects.json_query(
        key='Natural Gas Use (kBtu)', excluder='IS NOT', excludes=['NULL'],
    )

    # Here's an example using `LIKE` condition and chaining with other filters:
    BuildingSnapshot.objects.json_query(
        'Property Type', cond='LIKE', value='CONDO'
    ).filter(id__gt=1).count()

"""

from django.db.models import Manager
from django.db.models.query import QuerySet

FIELD_TEMPL = "({0}->>{1}"
KEY_CAST_TO_TYPE = {
    'text': str,
    'float': float,
    'int': int,
}


def _key_cast_to_type(key_cast):
    """Return type reference for casting during sorting."""
    if key_cast in KEY_CAST_TO_TYPE:
        return KEY_CAST_TO_TYPE[key_cast]


class JsonQuerySet(QuerySet):
    def __init__(self, primary=None, *args, **kwargs):
        self.primary = primary or 'extra_data'
        self.table = kwargs.get('table', 'seed_buildingsnapshot')
        return super(JsonQuerySet, self).__init__(*args, **kwargs)

    def _build_extra(self, key, cond, value, key_cast, excludes, **kwargs):
        """Builds the parameters for Django Obj Manager's extra func.

        :param key: str, the name of the json key we want.
        :param cond: str, the SQL-syntax condition (optional).
        :param value: str, the value we're comparing against.
        :param key_cast: type, expects that the  ``__name__``
            is the same as PostgreSQL's Json type names.
        :param excludes: list of str, all of the values that you
            wish to exclude from the query.
        :returns: dict, like {'where': ['<str of query>'], params: ['val']}
        """
        excluder = kwargs.get('excluder', '!=')
        case_insensitive = kwargs.get('case_insensitive', False)
        cast = ''
        where = []
        params = []
        if key_cast:
            cast = '::{0}'.format(key_cast)

        for exclude in excludes:
            where.append(FIELD_TEMPL.format(
                self.primary, "'{0}' {1} %s)".format(key, excluder)
            ))
            params.append(exclude)

        if cond:
            if case_insensitive:
                where.append('LOWER({0}) {1} %s'.format(
                    FIELD_TEMPL.format(
                        self.primary, "'{0}'){1}".format(key, cast),
                    ),
                    cond)
                )
                value = value.lower()
            else:
                where.append(FIELD_TEMPL.format(
                    self.primary, "'{0}'){1} {2} %s".format(key, cast, cond)
                ))

            params.append(value)

        return {'where': where, 'params': params}

    def json_query(self, key, value=None, cond=None,
                   key_cast='text', unit=None, **kw):
        """Query JsonField data using simplified syntax.

        See ``build_extra`` for parameter definitions.
        optional parameters pulled from kwargs:
        :param excludes: list of str, value conditions to avoid, applied first.
        :param field: str, if you'd like to override the ``self.primary``.
        :param order_by: str (optional), name of a key you want to order_by.
        :param order_by_rev: boolean (optional), whether to reverse or not.
        """
        from seed.models import (
            FLOAT, DECIMAL, STRING
        )

        unit_type = STRING
        if unit:
            unit_type = unit.unit_type

        qs = self
        excludes = kw.get('excludes', [])
        field = kw.get('field', self.primary)
        # Order_by_rev=True means order descending.
        if not key:
            return qs.none()
        if value and not cond:
            cond = '='
        if excludes:
            del(kw['excludes'])

        order_by = kw.get('order_by', None)
        order_by_rev = kw.get('order_by_rev', False)

        if any([cond, excludes, key_cast, value]):
            qs = qs.extra(
                **self._build_extra(
                    key, cond, value, key_cast, excludes, **kw
                )
            )

        # Sub-optimal implementation detected: Warning:
        # We're going to materialize all of these rows to do sorting.'
        # Obviously this is terrible, but there's no way to do an
        # order_by on a  non-field (i.e. non-named column) in Django.
        # "ORDER BY NULLIF({primary}->>%s, '')::{key_cast}" is the SQL
        # we'd use if Django allowed it.

        # Perhaps in Django 1.7 and its custom field definitions,
        # this will be easily doable.
        if not cond or not excludes:
            # Restrict the number of rows we materialize
            qs = qs.filter(**{'{0}__contains'.format(field): key})

        if order_by:
            qs = list(qs)

            def safe_cast(cast_fn, val):
                try:
                    return cast_fn(val)
                except TypeError:
                    return val

            def get_field(x):
                return getattr(x, self.primary).get(order_by, None)

            key_fns = {
                STRING: get_field,
                FLOAT: lambda x: safe_cast(float, get_field(x)),
                DECIMAL: lambda x: safe_cast(float, get_field(x)),
            }

            qs.sort(
                key=key_fns.get(unit_type, get_field),
                reverse=order_by_rev,
            )

        return qs


class JsonManager(Manager):
    def get_queryset(self):
        return JsonQuerySet(model=self.model, using=self._db)
