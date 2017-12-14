# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import copy
import os

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django_filters import CharFilter, DateFilter
from django_filters.rest_framework import FilterSet
from rest_framework import status
from rest_framework.decorators import detail_route

from seed.building_sync.building_sync import BuildingSync
from seed.hpxml.hpxml import HPXML
from seed.models import (
    PropertyAuditLog,
    PropertyMeasure,
    Simulation,
    PropertyView,
    PropertyState,
    BuildingFile,
    Cycle,
    AUDIT_USER_EDIT
)
from seed.serializers.properties import (
    PropertyStateSerializer,
    PropertyViewSerializer,
    PropertyViewAsStateSerializer,
)
from seed.utils.properties import get_changed_fields
from seed.utils.viewsets import (
    SEEDOrgReadOnlyModelViewSet
)


class PropertyViewFilterSet(FilterSet):
    """
    Advanced filtering for PropertyView sets version 2.1.
    """
    address_line_1 = CharFilter(name="state__address_line_1", lookup_expr='contains')
    analysis_state = CharFilter(method='analysis_state_filter')
    identifier = CharFilter(method='identifier_filter')
    cycle_start = DateFilter(name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(name='cycle__end', lookup_expr='gte')

    class Meta:
        model = PropertyView
        fields = ['identifier', 'address_line_1', 'cycle', 'property', 'cycle_start', 'cycle_end',
                  'analysis_state']

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

    @detail_route(methods=['GET'])
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
            - name: cycle_id
              type: integer
              required: true
              paramType: query
        """
        # organization_id = request.data['organization_id']
        cycle_id = request.query_params.get('cycle_id', None)

        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is not defined"
            })
        else:
            cycle = Cycle.objects.get(pk=cycle_id)

        try:
            # TODO: not checking organization? Is that right?
            property_view = PropertyView.objects.select_related('state').get(pk=pk, cycle=cycle)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s; cycle_id=%s' % (pk, cycle_id)
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

    @detail_route(methods=['GET'])
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
            - name: cycle_id
              type: integer
              required: true
              paramType: query
        """
        cycle_id = request.query_params.get('cycle_id', None)

        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is not defined"
            })
        else:
            cycle = Cycle.objects.get(pk=cycle_id)

        try:
            # TODO: not checking organization? Is that right?
            property_view = PropertyView.objects.select_related('state').get(pk=pk, cycle=cycle)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s; cycle_id=%s' % (pk, cycle_id)
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

    @detail_route(methods=['PUT'])
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
              enum: ["Unknown", "BuildingSync", "GeoJSON"]
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
        organization_id = request.data['organization_id']
        cycle_id = request.data.get('cycle_id', None)

        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is not defined"
            })
        else:
            cycle = Cycle.objects.get(pk=cycle_id)

        building_file = BuildingFile.objects.create(
            file=the_file,
            filename=the_file.name,
            file_type=file_type,
        )

        try:
            property_view = PropertyView.objects.get(pk=pk, cycle=cycle)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s; cycle_id=%s' % (pk, cycle_id)
            })

        # get some items off of this property view
        property_id_for_this_view = property_view.property.id
        scenario_ids_for_this_pv = [x.id for x in property_view.state.scenarios]
        buildingfile_ids_for_this_pv = [x.id for x in property_view.state.building_files]
        simulation_ids_for_this_pv = [x.id for x in Simulation.objects.filter(property_state=property_view.state)]
        measure_ids_for_this_pv = [x.id for x in PropertyMeasure.objects.filter(property_state=property_view.state)]

        # make a new property view copied from the old one so that most things are persisted automatically
        pv_copy = copy.deepcopy(property_view)

        # passing in the existing property state allows it to process the buildingsync without creating a new state
        p_status, new_pv_state, messages = building_file.process(organization_id, cycle,
                                                                 property_state=pv_copy.state,
                                                                 property_id=property_id_for_this_view)

        # persist the ids that were saved earlier
        [new_pv_state.scenarios.add(x) for x in scenario_ids_for_this_pv]
        [new_pv_state.building_files.add(x) for x in buildingfile_ids_for_this_pv]
        for x in simulation_ids_for_this_pv:
            Simulation.objects.get(id=x).property_state = new_pv_state
        for x in measure_ids_for_this_pv:
            PropertyMeasure.objects.get(id=x).property_state = new_pv_state

        # now save and return
        pv_copy.save()

        if p_status:
            return JsonResponse({
                "status": "success",
                "message": "successfully imported file",
                "data": {
                    "property_view": PropertyViewSerializer(pv_copy).data,
                },
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": "Could not process building file with messages {}".format(messages)
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        Update a property
        - looks up the property view
        - casts it as a PropertyState
        - builds a hash with all the same keys as the original property state
        - checks if any fields have changed
        - if nothing has changed, return 422 - Really?  Not sure how I feel about that one, it *is* processable
        - get the property audit log for this property state
        - if the new property state has extra_data, the original extra_data is update'd
        - and then whoa stuff about the audit log?
        - I'm going to assume 'Import Creation' is the key I'm looking for
        - create a serializer for the new property state
        - if it's valid, save this new serialized data to the db
        -  *** NEW: capture the original scenarios, etc
        - assign it to the original property view and save the property view
        -  *** NEW: assign the saved scenarios, etc., to the new state and save it
        - create a new property audit log for this change
        - return a 201
        ---
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the property view
              required: true
              paramType: query
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        data = request.data
        result = self._get_property_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            property_state_data = PropertyStateSerializer(property_view.state).data
            new_property_state_data = data['state']

            changed = True
            for key, val in new_property_state_data.iteritems():
                if val == '':
                    new_property_state_data[key] = None
            changed_fields = get_changed_fields(
                property_state_data, new_property_state_data
            )
            if not changed_fields:
                changed = False
            if not changed:
                result.update(
                    {'status': 'error', 'message': 'Nothing to update'}
                )
                status_code = 422  # status.HTTP_422_UNPROCESSABLE_ENTITY
            else:
                log = PropertyAuditLog.objects.select_related().filter(
                    state=property_view.state
                ).order_by('-id').first()

                if 'extra_data' in new_property_state_data.keys():
                    property_state_data['extra_data'].update(
                        new_property_state_data.pop('extra_data'))
                property_state_data.update(new_property_state_data)

                if log.name == 'Import Creation':
                    # Add new state
                    property_state_data.pop('id')
                    new_property_state_serializer = PropertyStateSerializer(
                        data=property_state_data
                    )
                    if new_property_state_serializer.is_valid():

                        # get some items off of this property view
                        scenario_ids_for_this_pv = [x.id for x in property_state_data.scenarios]
                        buildingfile_ids_for_this_pv = [x.id for x in property_state_data.building_files]
                        simulation_ids_for_this_pv = [x.id for x in
                                                      Simulation.objects.filter(property_state=property_state_data)]
                        measure_ids_for_this_pv = [x.id for x in
                                                   PropertyMeasure.objects.filter(property_state=property_state_data)]

                        # create the new property state, and perform an initial save
                        new_state = new_property_state_serializer.save()

                        # persist the ids that were saved earlier
                        [new_state.scenarios.add(x) for x in scenario_ids_for_this_pv]
                        [new_state.building_files.add(x) for x in buildingfile_ids_for_this_pv]
                        for x in simulation_ids_for_this_pv:
                            Simulation.objects.get(id=x).property_state = new_state
                        for x in measure_ids_for_this_pv:
                            PropertyMeasure.objects.get(id=x).property_state = new_state

                        # save it again for good measure?
                        new_state.save()

                        # then assign this state to the property view and save the whole view
                        property_view.state = new_state
                        property_view.save()

                        PropertyAuditLog.objects.create(organization=log.organization,
                                                        parent1=log,
                                                        parent2=None,
                                                        parent_state1=log.state,
                                                        parent_state2=None,
                                                        state=new_state,
                                                        name='Manual Edit',
                                                        description=None,
                                                        import_filename=log.import_filename,
                                                        record_type=AUDIT_USER_EDIT)

                        result.update(
                            {'state': new_property_state_serializer.validated_data}
                        )
                        # Removing organization key AND import_file key because they're not JSON-serializable
                        # TODO find better solution
                        if 'organization' in result['state']:
                            result['state'].pop('organization')
                        if 'import_file' in result['state']:
                            result['state'].pop('import_file')

                        # Not sure why we have 201 here. Should be 200 or 204 because there is
                        # no new content created.
                        status_code = status.HTTP_201_CREATED
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_property_state_serializer.errors)}
                        )
                        status_code = 422  # status.HTTP_422_UNPROCESSABLE_ENTITY
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match',
                                  'Merge current state in migration']:
                    # Override previous edit state or merge state
                    state = property_view.state
                    for key, value in new_property_state_data.iteritems():
                        setattr(state, key, value)
                    state.save()

                    result.update(
                        {'state': PropertyStateSerializer(state).data}
                    )
                    # Removing organization key AND import_file key because they're not JSON-serializable
                    # TODO find better solution
                    result['state'].pop('organization')
                    result['state'].pop('import_file')

                    status_code = status.HTTP_201_CREATED
                else:
                    result = {'status': 'error',
                              'message': 'Unrecognized audit log name: ' + log.name}
                    status_code = 422
                    return JsonResponse(result, status=status_code)

        else:
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)
