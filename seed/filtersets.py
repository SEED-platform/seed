#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author

provides filterset classes for advanced filtering of DRF viewsets
"""

# Imports from Standard Library
from datetime import datetime

# Imports from Third Party Modules
from dateutil.relativedelta import relativedelta

# Imports from Django
from django_filters.rest_framework import FilterSet
from django_filters import BaseInFilter, NumberFilter, CharFilter, DateFilter

# Local Imports
from seed.models import GreenAssessment, GreenAssessmentProperty
from seed.models import Cycle, StatusLabel as Label
# Constants

# Data Structure Definitions

# Private Functions

# Oops! we override a builtin in some of the models
property_decorator = property


# Public Classes and Functions
class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class GreenAssessmentFilterSet(FilterSet):
    name = CharFilter(name='name', lookup_expr='exact')
    award_body = CharFilter(name='award_body', lookup_expr='exact')
    name_icontains = CharFilter(name='name', lookup_expr='icontains')
    award_body_icontains = CharFilter(name='name', lookup_expr='icontains')
    recognition_type = CharFilter(
        name='recognition_type', lookup_expr='iexact'
    )

    class Meta:
        model = GreenAssessment
        fields = ['name', 'award_body', 'recognition_type']


class GAPropertyFilterSet(FilterSet):
    assessment = CharFilter(name='assessment__name', lookup_expr='iexact')
    rating = CharFilter(name='_rating', lookup_expr='iexact')
    year = NumberFilter(name='date', lookup_expr='year')

    class Meta:
        model = GreenAssessmentProperty
        fields = ('year', 'assessment', 'rating')


class LabelFilterSet(FilterSet):
    """Provide filtering for Label by property id, taxlot id, name or color."""
    property = NumberInFilter(name='property__pk', lookup_expr='in')
    taxlot = NumberInFilter(name='taxlot__pk', lookup_expr='in')

    class Meta:
        model = Label
        fields = ['name', 'color', 'property', 'taxlot']


class CycleFilterSet(FilterSet):
    """Provide filtering for Cycle by name, start date, end date or
    calendar year."""
    start_lte = DateFilter(name='start', lookup_expr='lte')
    end_gte = DateFilter(name='end', lookup_expr='gte')
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
        cycles = queryset.filter(name__contains=name)
        if not cycles:
            start = datetime(int(value), 1, 1)
            end = start + relativedelta(years=1) - relativedelta(seconds=1)

            # to eliminate the question of timezone saved in vs timezone
            # queried from, start and end dates are nudged in by the max
            # possible time difference between 2 servers
            start = start + relativedelta(hours=max_time_diff)
            end = end - relativedelta(hours=max_time_diff)
            cycles = queryset.filter(start__lte=start, end__gte=end)
        return cycles
