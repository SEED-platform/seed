"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author Fable Turas <fable@raintechpdx.com>

FilterSet classes to provide advanced filtering API endpoints.
"""

from django.db.models import Q
from django_filters import CharFilter, DateFilter, NumberFilter
from django_filters.rest_framework import FilterSet

from seed.models import GreenAssessment, GreenAssessmentProperty, PropertyView

# Oops! we override a builtin in some of the models
property_decorator = property


class GreenAssessmentFilterSet(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="exact")
    award_body = CharFilter(field_name="award_body", lookup_expr="exact")
    name_icontains = CharFilter(field_name="name", lookup_expr="icontains")
    award_body_icontains = CharFilter(field_name="name", lookup_expr="icontains")
    recognition_type = CharFilter(field_name="recognition_type", lookup_expr="iexact")

    class Meta:
        model = GreenAssessment
        fields = ["name", "award_body", "recognition_type"]


class GAPropertyFilterSet(FilterSet):
    assessment = CharFilter(field_name="assessment__name", lookup_expr="iexact")
    rating = CharFilter(field_name="_rating", lookup_expr="iexact")
    year = NumberFilter(field_name="date", lookup_expr="year")

    class Meta:
        model = GreenAssessmentProperty
        fields = ("year", "assessment", "rating", "view")


class PropertyViewFilterSet(FilterSet):
    """Provide advanced filtering for PropertyView

    Filter options for propertyviews by cycle (id), property (id),
    cycle_start (lte), and cycle_end (gte)
    """

    cycle_start = DateFilter(field_name="cycle__start", lookup_expr="lte")
    cycle_end = DateFilter(field_name="cycle__end", lookup_expr="gte")
    address_line_1 = CharFilter(field_name="state__address_line_1", lookup_expr="iexact")
    address_line_2 = CharFilter(field_name="state__address_line_2", lookup_expr="iexact")
    city = CharFilter(field_name="state__city", lookup_expr="iexact")
    state = CharFilter(field_name="state__state", lookup_expr="iexact")
    postal_code = CharFilter(field_name="state__postal_code", lookup_expr="iexact")
    property_identifier = CharFilter(method="identifier_filter")

    class Meta:
        model = PropertyView
        fields = ["cycle", "property", "cycle_start", "cycle_end", "property_identifier"]

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
        query = jurisdiction_property_id | custom_id_1 | pm_property_id | home_energy_score_id | ubid
        return queryset.filter(query)
