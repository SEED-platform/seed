#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author

# TODO
"""

# Imports from Standard Library

# Imports from Third Party Modules
from django_filters.rest_framework import FilterSet
from django_filters import BaseInFilter, NumberFilter, CharFilter

# Imports from Django

# Local Imports
from seed.models import GreenAssessment, GreenAssessmentProperty
# Constants

# Data Structure Definitions

# Private Functions


# Public Classes and Functions
class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class GreenAssessmentFilterSet(FilterSet):
    name = CharFilter(name='name', lookup_expr='iexact')
    award_body = CharFilter(name='award_body', lookup_expr='iexact')
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
