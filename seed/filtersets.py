#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Fable Turas <fable@raintechpdx.com>

FilterSet classes to provide advanced filtering API endpoints.
"""

from datetime import datetime

import pytz
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils.timezone import make_aware
from django_filters import BaseInFilter, NumberFilter, CharFilter, DateFilter
from django_filters.rest_framework import FilterSet

from seed.models import (
    Cycle,
    GreenAssessment,
    GreenAssessmentProperty,
    PropertyState,
    PropertyView,
    StatusLabel as Label
)

# Oops! we override a builtin in some of the models
property_decorator = property


# Public Classes and Functions
class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class GreenAssessmentFilterSet(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='exact')
    award_body = CharFilter(field_name='award_body', lookup_expr='exact')
    name_icontains = CharFilter(field_name='name', lookup_expr='icontains')
    award_body_icontains = CharFilter(field_name='name', lookup_expr='icontains')
    recognition_type = CharFilter(
        field_name='recognition_type', lookup_expr='iexact'
    )

    class Meta:
        model = GreenAssessment
        fields = ['name', 'award_body', 'recognition_type']


class GAPropertyFilterSet(FilterSet):
    assessment = CharFilter(field_name='assessment__name', lookup_expr='iexact')
    rating = CharFilter(field_name='_rating', lookup_expr='iexact')
    year = NumberFilter(field_name='date', lookup_expr='year')

    class Meta:
        model = GreenAssessmentProperty
        fields = ('year', 'assessment', 'rating', 'view')


class LabelFilterSet(FilterSet):
    """Provide filtering for Label by property id, taxlot id, name or color."""
    property = NumberInFilter(field_name='property__pk', lookup_expr='in')
    taxlot = NumberInFilter(field_name='taxlot__pk', lookup_expr='in')

    class Meta:
        model = Label
        fields = ['name', 'color', 'property', 'taxlot']


class CycleFilterSet(FilterSet):
    """Provide filtering for Cycle by name, start date, end date or
    calendar year."""
    start_lte = DateFilter(field_name='start', lookup_expr='lte')
    end_gte = DateFilter(field_name='end', lookup_expr='gte')
    year = CharFilter(method='year_filter')

    class Meta:
        model = Cycle
        fields = ['name', 'start_lte', 'end_gte', 'year']

    def year_filter(self, queryset, name, value):
        """
        Provide close enough filtering for Cycle spanning the single calendar
        year supplied to the filter.
        """
        max_time_diff = 26
        name = "{} Calendar Year".format(value)
        cycles = queryset.filter(name__icontains=name)
        if not cycles:
            start = make_aware(datetime(int(value), 1, 1), pytz.UTC)
            end = start + relativedelta(years=1) - relativedelta(seconds=1)

            # to eliminate the question of timezone saved in vs timezone
            # queried from, start and end dates are nudge1d in by the max
            # possible time difference between 2 servers
            start = start + relativedelta(hours=max_time_diff)
            end = end - relativedelta(hours=max_time_diff)
            cycles = queryset.filter(start__lte=start, end__gte=end)
        return cycles


class PropertyViewFilterSet(FilterSet):
    """Provide advanced filtering for PropertyView

    Filter options for propertyviews by cycle (id), property (id),
    cycle_start (lte), and cycle_end (gte)
    """
    cycle_start = DateFilter(field_name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(field_name='cycle__end', lookup_expr='gte')
    address_line_1 = CharFilter(
        field_name='state__address_line_1', lookup_expr='iexact'
    )
    address_line_2 = CharFilter(
        field_name='state__address_line_2', lookup_expr='iexact'
    )
    city = CharFilter(
        field_name='state__city', lookup_expr='iexact'
    )
    state = CharFilter(
        field_name='state__state', lookup_expr='iexact'
    )
    postal_code = CharFilter(
        field_name='state__postal_code', lookup_expr='iexact'
    )
    property_identifier = CharFilter(method='identifier_filter')

    class Meta:
        model = PropertyView
        fields = [
            'cycle', 'property',
            'cycle_start', 'cycle_end',
            'property_identifier'
        ]

    def identifier_filter(self, queryset, name, value):
        """
        Filter queryset for case-insensitive value matching
        jurisdiction_property_id OR custom_id_1 OR pm_property_id
        OR home_energy_score_id.
        """
        jurisdiction_property_id = Q(state__jurisdiction_property_id__iexact=value)
        custom_id_1 = Q(state__custom_id_1__iexact=value)
        pm_property_id = Q(state__pm_property_id=value)
        ubid = Q(state__ubid__iexact=value)
        home_energy_score_id = Q(state__home_energy_score_id=value)
        query = (
            jurisdiction_property_id
            | custom_id_1
            | pm_property_id
            | home_energy_score_id
            | ubid
        )
        return queryset.filter(query)


class PropertyStateFilterSet(FilterSet):
    """Provide advanced filtering for PropertyState

    Filter options for propertystate by energy_score (gte), city,
    pm_parent_property_id, and property_identifier.

    The property_identifier filter provides a single query parameter key for
    filtering against any of the property ID type fields.
    (jurisdiction_property_id, custom_id_1, pm_property_id or
    home_energy_score_id)
    """
    energy_score = NumberFilter(field_name='energy_score', lookup_expr='gte')
    property_identifier = CharFilter(method='identifier_filter')

    class Meta:
        model = PropertyState
        fields = [
            'energy_score',
            'city',
            'pm_parent_property_id',
            'property_identifier'
        ]

    def identifier_filter(self, queryset, name, value):
        """
        Filter queryset for case-insensitive value matching
        jurisdiction_property_id OR custom_id_1 OR pm_property_id
        OR home_energy_score_id.
        """
        jurisdiction_property_id = Q(jurisdiction_property_id__iexact=value)
        custom_id_1 = Q(custom_id_1__iexact=value)
        pm_property_id = Q(pm_property_id=value)
        ubid = Q(ubid__iexact=value)
        home_energy_score_id = Q(home_energy_score_id=value)
        query = (
            jurisdiction_property_id
            | custom_id_1
            | pm_property_id
            | home_energy_score_id
            | ubid
        )
        return queryset.filter(query)
