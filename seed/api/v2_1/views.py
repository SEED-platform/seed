# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import os

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django_filters import CharFilter, DateFilter
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import action
from seed.building_sync.building_sync import BuildingSync
from seed.hpxml.hpxml import HPXML
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    PropertyView,
    PropertyState,
    BuildingFile,
    Cycle,
)
from seed.serializers.properties import (
    PropertyViewAsStateSerializer,
)
from seed.utils.api import OrgMixin
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)


class PropertyViewFilterSet(FilterSet, OrgMixin):
    """
    Advanced filtering for PropertyView sets version 2.1.
    """
    address_line_1 = CharFilter(field_name="state__address_line_1", lookup_expr='contains')
    analysis_state = CharFilter(method='analysis_state_filter')
    identifier = CharFilter(method='identifier_filter')
    cycle_start = DateFilter(field_name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(field_name='cycle__end', lookup_expr='gte')

    class Meta:
        model = PropertyView
        fields = ['identifier', 'address_line_1', 'cycle', 'property', 'cycle_start', 'cycle_end', 'analysis_state']

    def identifier_filter(self, queryset, name, value):
        address_line_1 = Q(state__address_line_1__icontains=value)
        jurisdiction_property_id = Q(state__jurisdiction_property_id__icontains=value)
        custom_id_1 = Q(state__custom_id_1__icontains=value)
        pm_property_id = Q(state__pm_property_id__icontains=value)
        ubid = Q(state__ubid__icontains=value)

        query = (
            address_line_1 |
            jurisdiction_property_id |
            custom_id_1 |
            pm_property_id |
            ubid
        )
        return queryset.filter(query).order_by('-state__id')

    def analysis_state_filter(self, queryset, name, value):
        # For some reason a ChoiceFilter doesn't work on this object. I wanted to have it
        # magically look up the map from the analysis_state string to the analysis_state ID, but
        # it isn't working. Forcing it manually.

        # If the user puts in a bogus filter, then it will return All, for now

        state_id = None
        for state in PropertyState.ANALYSIS_STATE_TYPES:
            if state[1].upper() == value.upper():
                state_id = state[0]
                break

        if state_id is not None:
            return queryset.filter(Q(state__analysis_state__exact=state_id)).order_by('-state__id')
        else:
            return queryset.order_by('-state__id')


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

    def _get_property_view(self, pk, cycle_pk):
        """
        Return a property view based on the property id and cycle
        :param pk: ID of property (not property view)
        :param cycle_pk: ID of the cycle
        :return: dict, propety view and status
        """
        try:
            property_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                property_id=pk,
                cycle_id=cycle_pk,
                property__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success',
                'property_view': property_view
            }
        except PropertyView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'property view with property id {} does not exist'.format(pk)
            }
        except PropertyView.MultipleObjectsReturned:
            result = {
                'status': 'error',
                'message': 'Multiple property views with id {}'.format(pk)
            }
        return result

    @action(detail=True, methods=['GET'])
    def building_sync(self, request, pk):
        """
        Return BuildingSync representation of the property

        ---
        parameters:
            - name: pk
              description: The PropertyView to return the BuildingSync file
              type: path
              required: true
            - name: organization_id
              type: integer
              required: true
              paramType: query
        """
        try:
            # TODO: not checking organization? Is that right?
            # TODO: this needs to call _get_property_view and use the property pk, not the property_view pk.
            #   or we need to state the v2.1 of API uses property views instead of property
            property_view = PropertyView.objects.select_related('state').get(pk=pk)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s' % pk
            })

        bs = BuildingSync()
        # Check if there is an existing BuildingSync XML file to merge
        bs_file = property_view.state.building_files.last()
        if bs_file is not None and os.path.exists(bs_file.file.path):
            bs.import_file(bs_file.file.path)
            xml = bs.export(property_view.state, BuildingSync.BRICR_STRUCT)
            return HttpResponse(xml, content_type='application/xml')
        else:
            # create a new XML from the record, do not import existing XML
            xml = bs.export(property_view.state, BuildingSync.BRICR_STRUCT)
            return HttpResponse(xml, content_type='application/xml')

    @action(detail=True, methods=['GET'])
    def hpxml(self, request, pk):
        """
        Return HPXML representation of the property

        ---
        parameters:
            - name: pk
              description: The PropertyView to return the HPXML file
              type: path
              required: true
            - name: organization_id
              type: integer
              required: true
              paramType: query
        """
        # Organization is checked in the orgfilter of the ViewSet
        try:
            property_view = PropertyView.objects.select_related('state').get(pk=pk)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s' % pk
            })

        hpxml = HPXML()
        # Check if there is an existing BuildingSync XML file to merge
        hpxml_file = property_view.state.building_files.last()
        if hpxml_file is not None and os.path.exists(hpxml_file.file.path):
            hpxml.import_file(hpxml_file.file.path)
            xml = hpxml.export(property_view.state)
            return HttpResponse(xml, content_type='application/xml')
        else:
            # create a new XML from the record, do not import existing XML
            xml = hpxml.export(property_view.state)
            return HttpResponse(xml, content_type='application/xml')

    def _merge_relationships(self, old_state, new_state):
        """
        Merge the relationships between the old state and the new state. This is different than the version
        in views/properties.py because if this is a buildingsync update, then the buildingsync file may
        contain new or removed items that we want to merge.

        :param old_state: PropertyState
        :param new_state: PropertyState
        :return: PropertyState, updated new_state
        """
        # for s in old_state.scenarios.all():
        #     s.property_state = new_state
        #     s.save()
        #
        # # Move the measures to the new state
        # for m in PropertyMeasure.objects.filter(property_state=old_state):
        #     m.property_state = new_state
        #     m.save()
        #
        # # Move the old building file to the new state to preserve the history
        # for b in old_state.building_files.all():
        #     b.property_state = new_state
        #     b.save()
        #
        # for s in Simulation.objects.filter(property_state=old_state):
        #     s.property_state = new_state
        #     s.save()

        return new_state

    @action(detail=True, methods=['PUT'])
    @has_perm_class('can_modify_data')
    def update_with_building_sync(self, request, pk):
        """
        Does not work in Swagger!

        Update an existing PropertyView with a building file. Currently only supports BuildingSync.
        ---
        consumes:
            - multipart/form-data
        parameters:
            - name: pk
              description: The PropertyView to update with this buildingsync file
              type: path
              required: true
            - name: organization_id
              type: integer
              required: true
            - name: cycle_id
              type: integer
              required: true
            - name: file_type
              type: string
              enum: ["Unknown", "BuildingSync"]
              required: true
            - name: file
              description: In-memory file object
              required: true
              type: file
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        the_file = request.data['file']
        file_type = BuildingFile.str_to_file_type(request.data.get('file_type', 'Unknown'))
        organization_id = request.query_params.get('organization_id', None)
        cycle_pk = request.query_params.get('cycle_id', None)

        if not cycle_pk:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is not defined"
            })
        else:
            cycle = Cycle.objects.get(pk=cycle_pk)

        result = self._get_property_view(pk, cycle_pk)
        p_status = False
        new_pv_state = None
        if result.get('status', None) != 'error':
            building_file = BuildingFile.objects.create(
                file=the_file,
                filename=the_file.name,
                file_type=file_type,
            )

            property_view = result.pop('property_view')
            previous_state = property_view.state
            # passing in the existing propertyview allows it to process the buildingsync file and attach it to the
            # existing propertyview.
            p_status, new_pv_state, new_pv_view, messages = building_file.process(
                organization_id, cycle, property_view=property_view
            )

            # merge the relationships from the old property state
            self._merge_relationships(previous_state, new_pv_state)

        else:
            messages = ['Cannot match a PropertyView with property_id=%s; cycle_id=%s' % (pk, cycle_pk)]

        if p_status and new_pv_state:
            return JsonResponse({
                'success': True,
                'status': 'success',
                'message': 'successfully imported file',
                'data': {
                    'property_view': PropertyViewAsStateSerializer(new_pv_view).data,
                },
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': "Could not process building file with messages {}".format(messages)
            }, status=status.HTTP_400_BAD_REQUEST)
