# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.filtersets import PropertyViewFilterSet, PropertyStateFilterSet
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    Measure,
    PropertyMeasure,
    AUDIT_USER_EDIT,
    Column,
    Cycle,
    Simulation,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLotProperty,
    TaxLotView,
)
from seed.models import Property as PropertyModel
from seed.serializers.pint import PintJSONEncoder
from seed.serializers.properties import (
    PropertySerializer,
    PropertyStateSerializer,
    PropertyViewAsStateSerializer,
    PropertyViewSerializer,
)
from seed.serializers.taxlots import (
    TaxLotViewSerializer,
)
from seed.utils.api import api_endpoint_class
from seed.utils.properties import (
    get_changed_fields,
    pair_unpair_property_taxlot,
    update_result_with_master,
)
from seed.utils.viewsets import (
    SEEDOrgCreateUpdateModelViewSet,
    SEEDOrgModelViewSet
)

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


class GBRPropertyViewSet(SEEDOrgCreateUpdateModelViewSet):
    """Properties API Endpoint

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

    create:
        Create a new Property within user`s specified org.

    delete:
        Remove an existing Property.

    update:
        Update a Property record.

    partial_update:
        Update one or more fields on an existing Property.
    """
    serializer_class = PropertySerializer
    model = PropertyModel
    data_name = "properties"


class PropertyStateViewSet(SEEDOrgCreateUpdateModelViewSet):
    """Property State API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        all PropertyState fields/values
                    }
                ]
            }


    retrieve:
        Return a PropertyState instance by pk if it is within specified org.

    list:
        Return all PropertyStates available to user through specified org.

    create:
        Create a new PropertyState within user`s specified org.

    delete:
        Remove an existing PropertyState.

    update:
        Update a PropertyState record.

    partial_update:
        Update one or more fields on an existing PropertyState."""
    serializer_class = PropertyStateSerializer
    model = PropertyState
    filter_class = PropertyStateFilterSet
    data_name = "properties"


class PropertyViewViewSet(SEEDOrgModelViewSet):
    """PropertyViews API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': PropertyView primary key,
                        'property_id': id of associated Property,
                        'state': dict of associated PropertyState values (writeable),
                        'cycle': dict of associated Cycle values,
                        'certifications': dict of associated GreenAssessmentProperties values
                    }
                ]
            }


    retrieve:
        Return a PropertyView instance by pk if it is within specified org.

    list:
        Return all PropertyViews available to user through specified org.

    create:
        Create a new PropertyView within user`s specified org.

    delete:
        Remove an existing PropertyView.

    update:
        Update a PropertyView record.

    partial_update:
        Update one or more fields on an existing PropertyView.
    """
    serializer_class = PropertyViewAsStateSerializer
    model = PropertyView
    filter_class = PropertyViewFilterSet
    orgfilter = 'property__organization_id'
    data_name = "property_views"


class PropertyViewSet(GenericViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = PropertySerializer

    def _get_filtered_results(self, request, columns):

        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = request.query_params.get('organization_id', None)
        cycle_id = request.query_params.get('cycle')
        if not org_id:
            return JsonResponse(
                {'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                status=status.HTTP_400_BAD_REQUEST)
        if cycle_id:
            cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
        else:
            cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
            if cycle:
                cycle = cycle.first()
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not locate cycle',
                    'pagination': {
                        'total': 0
                    },
                    'cycle_id': None,
                    'results': []
                })

        property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
            .filter(property__organization_id=request.query_params['organization_id'],
                    cycle=cycle).order_by('id')

        paginator = Paginator(property_views_list, per_page)

        try:
            property_views = paginator.page(page)
            page = int(page)
        except PageNotAnInteger:
            property_views = paginator.page(1)
            page = 1
        except EmptyPage:
            property_views = paginator.page(paginator.num_pages)
            page = paginator.num_pages

        response = {
            'pagination': {
                'page': page,
                'start': paginator.page(page).start_index(),
                'end': paginator.page(page).end_index(),
                'num_pages': paginator.num_pages,
                'has_next': paginator.page(page).has_next(),
                'has_previous': paginator.page(page).has_previous(),
                'total': paginator.count
            },
            'cycle_id': cycle.id,
            'results': TaxLotProperty.get_related(property_views, columns)
        }

        return JsonResponse(response, encoder=PintJSONEncoder)

    def _move_relationships(self, old_state, new_state):
        """
        In general, we move the old relationships to the new state since the old state should not be
        accessible anymore. If we ever unmerge, then we need to decide who gets the data.. both?

        :param old_state: PropertyState
        :param new_state: PropertyState
        :return: PropertyState, updated new_state
        """
        for s in old_state.scenarios.all():
            s.property_state = new_state
            s.save()

        # Move the measures to the new state
        for m in PropertyMeasure.objects.filter(property_state=old_state):
            m.property_state = new_state
            m.save()

        # Move the old building file to the new state to perserve the history
        for b in old_state.building_files.all():
            b.property_state = new_state
            b.save()

        for s in Simulation.objects.filter(property_state=old_state):
            s.property_state = new_state
            s.save()

        return new_state

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        List all the properties
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: cycle
              description: The ID of the cycle to get properties
              required: true
              paramType: query
            - name: page
              description: The current page of properties to return
              required: false
              paramType: query
            - name: per_page
              description: The number of items per page to return
              required: false
              paramType: query
        """
        return self._get_filtered_results(request, columns=[])

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['POST'])
    def filter(self, request):
        """
        List all the properties
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: cycle
              description: The ID of the cycle to get properties
              required: true
              paramType: query
            - name: page
              description: The current page of properties to return
              required: false
              paramType: query
            - name: per_page
              description: The number of items per page to return
              required: false
              paramType: query
            - name: column filter data
              description: Object containing columns to filter on, should be a JSON object with a single key "columns"
                           whose value is a list of strings, each representing a column name
              paramType: body
        """
        try:
            columns = dict(request.data.iterlists())['columns']
        except AttributeError:
            columns = request.data['columns']
        return self._get_filtered_results(request, columns=columns)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['PUT'])
    def pair(self, request, pk=None):
        """
        Pair a taxlot to this property
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: taxlot_id
              description: The taxlot id to pair up with this property
              required: true
              paramType: query
            - name: pk
              description: pk (property ID)
              required: true
              paramType: path
        """
        # TODO: Call with PUT /api/v2/properties/1/pair/?taxlot_id=1&organization_id=1
        organization_id = int(request.query_params.get('organization_id'))
        property_id = int(pk)
        taxlot_id = int(request.query_params.get('taxlot_id'))
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, True)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['PUT'])
    def unpair(self, request, pk=None):
        """
        Unpair a taxlot from this property
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: taxlot_id
              description: The taxlot id to unpair from this property
              required: true
              paramType: query
            - name: pk
              description: pk (property ID)
              required: true
              paramType: path
        """
        # TODO: Call with PUT /api/v2/properties/1/unpair/?taxlot_id=1&organization_id=1
        organization_id = int(request.query_params.get('organization_id'))
        property_id = int(pk)
        taxlot_id = int(request.query_params.get('taxlot_id'))
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, False)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def columns(self, request):
        """
        List all property columns
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        organization_id = int(request.query_params.get('organization_id'))
        columns = Column.retrieve_all(organization_id, 'property')

        return JsonResponse({'status': 'success', 'columns': columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['DELETE'])
    def delete(self, request, pk=None):
        """
        Delete a single property state from a property_viewID. Not sure why we
        are deleting only the state, but it is matching the functionality that is in
        the batch_delete request.
        ---
        parameters:
            - name: pk
              description: Primary key to delete
              require: true
        """
        num_objs, del_items = PropertyView.objects.filter(state__id=int(pk)).delete()
        if num_objs > 0:
            return JsonResponse({'status': 'success', 'message': del_items})
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No PropertyStates removed'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['DELETE'])
    def batch_delete(self, request):
        """
        Batch delete several properties
        ---
        parameters:
            - name: selected
              description: A list of property ids to delete
              many: true
              required: true
        """
        property_states = request.data.get('selected', [])
        resp = PropertyState.objects.filter(pk__in=property_states).delete()

        if resp[0] == 0:
            return JsonResponse({'status': 'warning', 'message': 'No action was taken'})

        return JsonResponse({'status': 'success', 'properties': resp[1]['seed.PropertyState']})

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

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def view(self, request, pk=None):
        """
        Get the property view
        ---
        parameters:
            - name: cycle_id
              description: The cycle ID to query on
              required: true
              paramType: query
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_property_view(pk, cycle_pk)
        return JsonResponse(result)

    def _get_taxlots(self, pk):
        lot_view_pks = TaxLotProperty.objects.filter(property_view_id=pk).values_list(
            'taxlot_view_id', flat=True)
        lot_views = TaxLotView.objects.filter(pk__in=lot_view_pks).select_related('cycle', 'state')
        lots = []
        for lot in lot_views:
            lots.append(TaxLotViewSerializer(lot).data)
        return lots

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def taxlots(self, pk):
        """
        Get related TaxLots for this property
        """
        return JsonResponse(self._get_taxlots(pk))

    def get_history(self, property_view):
        """Return history in reverse order"""

        # access the history from the property state
        history, master = property_view.state.history()

        # convert the history and master states to StateSerializers
        master['state'] = PropertyStateSerializer(master['state_data']).data
        del master['state_data']
        del master['state_id']

        for h in history:
            h['state'] = PropertyStateSerializer(h['state_data']).data
            del h['state_data']
            del h['state_id']

        return history, master

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Get property details
        ---
        parameters:
            - name: pk
              description: The primary key of the Property (not PropertyView nor PropertyState)
              required: true
              paramType: path
            - name: cycle_id
              description: The cycle id for filtering the property view
              required: true
              paramType: query
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_property_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            result.update(PropertyViewSerializer(property_view).data)
            # remove PropertyView id from result
            result.pop('id')

            result['property']['db_property_updated'] = result['property']['updated']
            result['property']['db_property_created'] = result['property']['created']
            result['state'] = PropertyStateSerializer(property_view.state).data
            result['taxlots'] = self._get_taxlots(property_view.pk)
            result['history'], master = self.get_history(property_view)
            result = update_result_with_master(result, master)
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_404_NOT_FOUND
        return Response(result, status=status_code)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk=None):
        """
        Update a property.

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
        - assign it to the original property view and save the property view
        - create a new property audit log for this change
        - return a 200 if created

        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
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

            # get the property state information from the request
            new_property_state_data = data['state']

            # set empty strings to None
            for key, val in new_property_state_data.iteritems():
                if val == '':
                    new_property_state_data[key] = None

            changed_fields = get_changed_fields(property_state_data, new_property_state_data)
            if not changed_fields:
                result.update(
                    {'status': 'success', 'message': 'Records are identical'}
                )
                return JsonResponse(result, status=status.HTTP_204_NO_CONTENT)
            else:
                # Not sure why we are going through the pain of logging this all right now... need to
                # reevaluate this.
                log = PropertyAuditLog.objects.select_related().filter(
                    state=property_view.state
                ).order_by('-id').first()

                if 'extra_data' in new_property_state_data.keys():
                    property_state_data['extra_data'].update(new_property_state_data.pop('extra_data'))
                property_state_data.update(new_property_state_data)

                if log.name == 'Import Creation':
                    # Add new state by removing the existing ID.
                    property_state_data.pop('id')
                    new_property_state_serializer = PropertyStateSerializer(
                        data=property_state_data
                    )
                    if new_property_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving relationships
                        new_state = new_property_state_serializer.save()

                        # Since we are creating a new relationship when we are manually editing the Properties, then
                        # we need to move the relationships over to the new manually edited record.
                        new_state = self._move_relationships(property_view.state, new_state)
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
                            {'state': new_property_state_serializer.data}
                        )
                        return JsonResponse(result, status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match', 'Merge current state in migration']:
                    # Convert this to using the serializer to save the data. This will override the previous values
                    # in the state object.

                    # Note: We should be able to use partial update here and pass in the changed fields instead of the
                    # entire state_data.
                    updated_property_state_serializer = PropertyStateSerializer(
                        property_view.state,
                        data=property_state_data
                    )
                    if updated_property_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving relationships
                        updated_property_state_serializer.save()

                        result.update(
                            {'state': updated_property_state_serializer.data}
                        )
                        return JsonResponse(result, status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                updated_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                else:
                    result = {
                        'status': 'error',
                        'message': 'Unrecognized audit log name: ' + log.name
                    }
                    return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            # save the property view, even if it hasn't changed so that the datetime gets updated on the property.
            # Uhm, does this ever get called? There are a bunch of returns in the code above.
            property_view.save()
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['PUT'], url_path='update_measures')
    def add_measures(self, request, pk=None):
        """
        Update the measures applied to the building. There are two options, one for adding
        measures and one for removing measures.

        ---
        type:
            status:
                required: true
                type: string
            message:
                required: true
                type: object
            added_measure_ids:
                required: true
                type: array
                description: list of measure ids that were added to the property
            removed_measure_ids:
                required: true
                type: array
                description: list of measure ids that were removed from the property
            existing_measure_ids:
                required: true
                type: array
                description: list of measure ids that already existed for the property
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the property view
              required: true
              paramType: query
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: add_measures
              description: list of measure_ids or measure long names to add to property
              type: array
              required: false
              paramType: form
            - name: remove_measures
              description: list of measure_ids or measure long names to remove from property
              type: array
              required: false
              paramType: form
            - name: implementation_status
              description: Enum on type of measures. Recommended, Proposed, Implemented
              required: true
              paramType: form
              type: string
              enum: ["Recommended", "Proposed", "Implemented"]
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass cycle_id as query parameter'})

        implementation_status = PropertyMeasure.str_to_impl_status(
            request.data.get('implementation_status', None))
        if not implementation_status:
            return JsonResponse(
                {'status': 'error', 'message': 'None or invalid implementation_status type'}
            )

        result = self._get_property_view(pk, cycle_pk)
        pv = None
        if result.get('status', None) != 'error':
            pv = result.pop('property_view')
        else:
            return JsonResponse(result)

        # get the list of measures to add/remove and return the ids
        add_measure_ids = Measure.validate_measures(request.data.get('add_measures', []).split(','))
        remove_measure_ids = Measure.validate_measures(
            request.data.get('remove_measures', []).split(','))

        # add_measures = request.data
        message_add = []
        message_remove = []
        message_existed = []

        property_state_id = pv.state.pk

        for m in add_measure_ids:
            join, created = PropertyMeasure.objects.get_or_create(
                property_state_id=property_state_id,
                measure_id=m,
                implementation_status=implementation_status
            )
            if created:
                message_add.append(m)
            else:
                message_existed.append(m)

        for m in remove_measure_ids:
            qs = PropertyMeasure.objects.filter(property_state_id=property_state_id,
                                                measure_id=m,
                                                implementation_status=implementation_status)
            if qs.exists():
                qs.delete()
                message_remove.append(m)

        return JsonResponse(
            {
                "status": "success",
                "message": "Updated measures for property state",
                "added_measure_ids": message_add,
                "removed_measure_ids": message_remove,
                "existing_measure_ids": message_existed,
            }
        )

    # TODO: fix the url_path to be nested. I want the url_path to be measures and have get,post,put
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['DELETE'], url_path='delete_measures')
    def delete_measures(self, request, pk=None):
        """
        Delete measures. Allow the user to define which implementation type to delete
        ---
        type:
            status:
                required: true
                type: string
            message:
                required: true
                type: string
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the property view
              required: true
              paramType: query
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: implementation_status
              description: Enum on type of measures. Recommended, Proposed, Implemented
              required: false
              paramType: form
              type: string
              enum: ["Recommended", "Proposed", "Implemented"]
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass cycle_id as query parameter'})

        impl_status = request.data.get('implementation_status', None)
        if not impl_status:
            impl_status = [PropertyMeasure.RECOMMENDED,
                           PropertyMeasure.IMPLEMENTED,
                           PropertyMeasure.PROPOSED]
        else:
            impl_status = [PropertyMeasure.str_to_impl_status(impl_status)]

        result = self._get_property_view(pk, cycle_pk)
        pv = None
        if result.get('status', None) != 'error':
            pv = result.pop('property_view')
        else:
            return JsonResponse(result)

        property_state_id = pv.state.pk
        del_count, _ = PropertyMeasure.objects.filter(
            property_state_id=property_state_id,
            implementation_status__in=impl_status,
        ).delete()

        return JsonResponse({
            "status": "status",
            "message": "Deleted {} measures".format(del_count)
        })

    # TODO: fix the url_path to be nested. I want the url_path to be measures and have get,post,put
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['GET'], url_path='measures')
    def get_measures(self, request, pk=None):
        """
        Get the list of measures for a property and the given cycle
        ---
        type:
            status:
                required: true
                type: string
            message:
                required: true
                type: object
            measures:
                required: true
                type: object
                description: list of measure objects for the property
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the property view
              required: true
              paramType: query
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass cycle_id as query parameter'})

        result = self._get_property_view(pk, cycle_pk)
        pv = None
        if result.get('status', None) != 'error':
            pv = result.pop('property_view')
        else:
            return JsonResponse(result)

        property_state_id = pv.state.pk
        join = PropertyMeasure.objects.filter(property_state_id=property_state_id).select_related(
            'measure')
        result = []
        for j in join:
            result.append({
                "implementation_type": j.get_implementation_status_display(),
                "category": j.measure.category,
                "category_display_name": j.measure.category_display_name,
                "name": j.measure.name,
                "display_name": j.measure.display_name,
                "unique_name": "{}.{}".format(j.measure.category, j.measure.name),
                "pk": j.measure.id,
            })

        return JsonResponse(
            {
                "status": "success",
                "message": "Found {} measures".format(len(result)),
                "measures": result,
            }
        )


def diffupdate(old, new):
    """Returns lists of fields changed"""
    changed_fields = []
    changed_extra_data = []
    for k, v in new.iteritems():
        if old.get(k, None) != v or k not in old:
            changed_fields.append(k)
    if 'extra_data' in changed_fields:
        changed_fields.remove('extra_data')
        changed_extra_data, _ = diffupdate(old['extra_data'], new['extra_data'])
    return changed_fields, changed_extra_data
