# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

from django.db.models import Q
from django.http import JsonResponse
from django_filters import CharFilter, DateFilter
from django_filters.rest_framework import FilterSet
from rest_framework.decorators import detail_route

from seed.models import (
    PropertyView,
)
from seed.serializers.properties import (
    PropertyViewAsStateSerializer,
)
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)


class PropertyViewFilterSet(FilterSet):
    """
    Advanced filtering for PropertyView sets version 2.1.
    """
    address_line_1 = CharFilter(name="state__address_line_1", lookup_expr='contains')
    identifier = CharFilter(method='identifier_filter')
    cycle_start = DateFilter(name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(name='cycle__end', lookup_expr='gte')

    class Meta:
        model = PropertyView
        fields = ['identifier', 'address_line_1', 'cycle', 'property', 'cycle_start', 'cycle_end']

    def identifier_filter(self, queryset, name, value):
        address_line_1 = Q(state__address_line_1__icontains=value)
        jurisdiction_property_id = Q(state__jurisdiction_property_id__icontains=value)
        custom_id_1 = Q(state__custom_id_1__icontains=value)
        pm_property_id = Q(state__pm_property_id__icontains=value)
        query = (
            address_line_1 |
            jurisdiction_property_id |
            custom_id_1 |
            pm_property_id
        )
        return queryset.filter(query).order_by('-state__id')


class PropertyViewSetV21(SEEDOrgReadOnlyModelViewSet):
    """
    Properties API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': Property primary key,
                        'campus': property is a campus,
                        'parent_property': dict of associated parent property
                        'labels': list of associated label ids
                    }
                ]
            }


    retrieve:
        Return a Property instance by pk if it is within specified org.

    list:
        Return all Properties available to user through specified org.
    """
    serializer_class = PropertyViewAsStateSerializer
    model = PropertyView
    data_name = "properties"
    filter_class = PropertyViewFilterSet
    orgfilter = 'property__organization_id'

    # Can't figure out how to do the ordering filter, so brute forcing it now with get_queryset
    # filter_backends = (DjangoFilterBackend, OrderingFilter,)
    # queryset = PropertyView.objects.all()
    # ordering = ('-id', '-state__id',)

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        return PropertyView.objects.filter(property__organization_id=org_id).order_by('-state__id')

    @detail_route(methods=['GET'])
    def building_sync(self, request, pk):
        """
        Return BuildingSync representation of the property
        ---

        """
        return JsonResponse(
            {"status": "error", "message": "Not yet implemented. PK was {}".format(pk)})
