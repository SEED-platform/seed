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
from seed.models import GreenAssessmentProperty
# Constants

# Data Structure Definitions

# Private Functions


# Public Classes and Functions
class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class GAPropertyFilterSet(FilterSet):
    assessment = CharFilter(name='assessment__name')

    class Meta:
        model = GreenAssessmentProperty
        fields = ('year', 'assessment', 'rating')
