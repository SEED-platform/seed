# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California,
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
from rest_framework.viewsets import GenericViewSet

from seed.utils.match import match_merge_in_cycle
from seed.data_importer.views import ImportFileViewSet
from seed.decorators import ajax_request_class
from seed.filtersets import PropertyViewFilterSet, PropertyStateFilterSet
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization
)
from seed.models import (
    AUDIT_USER_EDIT,
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
    Cycle,
    DATA_STATE_MATCHING,
    MERGE_STATE_DELETE,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    Meter,
    Measure,
    Note,
    Property,
    PropertyAuditLog,
    PropertyMeasure,
    PropertyState,
    PropertyView,
    Simulation,
    StatusLabel,
    TaxLotProperty,
    TaxLotView,
    VIEW_LIST,
    VIEW_LIST_PROPERTY
)
from seed.models import Property as PropertyModel
from seed.serializers.pint import PintJSONEncoder
from seed.serializers.pint import (
    apply_display_unit_preferences,
    add_pint_unit_suffix
)
from seed.serializers.properties import (
    PropertySerializer,
    PropertyStateSerializer,
    PropertyViewAsStateSerializer,
    PropertyViewSerializer,
)
from seed.serializers.taxlots import (
    TaxLotViewSerializer,
)
from seed.utils.api import ProfileIdMixin, api_endpoint_class
from seed.utils.properties import (
    get_changed_fields,
    pair_unpair_property_taxlot,
    update_result_with_master,
)
from seed.utils.merge import merge_properties
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
    queryset = PropertyView.objects.all().select_related('state')


class PropertyViewSet(GenericViewSet, ProfileIdMixin):
    renderer_classes = (JSONRenderer,)
    serializer_class = PropertySerializer

    def _get_filtered_results(self, request, profile_id):
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = request.query_params.get('organization_id', None)
        cycle_id = request.query_params.get('cycle')
        # check if there is a query paramater for the profile_id. If so, then use that one
        profile_id = request.query_params.get('profile_id', profile_id)

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

        # Return property views limited to the 'inventory_ids' list.  Otherwise, if selected is empty, return all
        if 'inventory_ids' in request.data and request.data['inventory_ids']:
            property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(property_id__in=request.data['inventory_ids'],
                        property__organization_id=org_id, cycle=cycle) \
                .order_by('id')  # TODO: test adding .only(*fields['PropertyState'])
        else:
            property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(property__organization_id=org_id, cycle=cycle) \
                .order_by('id')  # TODO: test adding .only(*fields['PropertyState'])

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

        org = Organization.objects.get(pk=org_id)

        # Retrieve all the columns that are in the db for this organization
        columns_from_database = Column.retrieve_all(org_id, 'property', False)

        # This uses an old method of returning the show_columns. There is a new method that
        # is prefered in v2.1 API with the ProfileIdMixin.
        if profile_id is None:
            show_columns = None
        elif profile_id == -1:
            show_columns = list(Column.objects.filter(
                organization_id=org_id
            ).values_list('id', flat=True))
        else:
            try:
                profile = ColumnListSetting.objects.get(
                    organization=org,
                    id=profile_id,
                    settings_location=VIEW_LIST,
                    inventory_type=VIEW_LIST_PROPERTY
                )
                show_columns = list(ColumnListSettingColumn.objects.filter(
                    column_list_setting_id=profile.id
                ).values_list('column_id', flat=True))
            except ColumnListSetting.DoesNotExist:
                show_columns = None

        related_results = TaxLotProperty.get_related(property_views, show_columns,
                                                     columns_from_database)

        # collapse units here so we're only doing the last page; we're already a
        # realized list by now and not a lazy queryset
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

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
            'results': unit_collapsed_results
        }

        return JsonResponse(response)

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

        # Move the old building file to the new state to preserve the history
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
        List all the properties	with all columns
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
        return self._get_filtered_results(request, profile_id=-1)

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
            - name: profile_id
              description: Either an id of a list settings profile, or undefined
              paramType: body
        """
        if 'profile_id' not in request.data:
            profile_id = None
        else:
            if request.data['profile_id'] == 'None':
                profile_id = None
            else:
                profile_id = request.data['profile_id']

                # ensure that profile_id is an int
                try:
                    profile_id = int(profile_id)
                except TypeError:
                    pass

        return self._get_filtered_results(request, profile_id=profile_id)

    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['POST'])
    def meters_exist(self, request):
        """
        Check to see if the given Properties (given by ID) have Meters.
        ---
        parameters:
            - name: inventory_ids
              description: Array containing Property IDs.
              paramType: body
        """
        body = request.data
        property_ids = body.get('inventory_ids', [])

        return Meter.objects.filter(property_id__in=property_ids).exists()

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['POST'])
    def merge(self, request):
        """
        Merge multiple property records into a single new record, and run this
        new record through a match and merge round within it's current Cycle.
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: state_ids
              description: Array containing property state ids to merge
              paramType: body
        """
        body = request.data

        state_ids = body.get('state_ids', [])
        organization_id = int(request.query_params.get('organization_id', None))

        # Check the number of state_ids to merge
        if len(state_ids) < 2:
            return JsonResponse({
                'status': 'error',
                'message': 'At least two ids are necessary to merge'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Make sure the state isn't already matched
        for state_id in state_ids:
            if ImportFileViewSet.has_coparent(state_id, 'properties'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Source state [' + state_id + '] is already matched'
                }, status=status.HTTP_400_BAD_REQUEST)

        merged_state = merge_properties(state_ids, organization_id, 'Manual Match')

        count, view_id = match_merge_in_cycle(merged_state.propertyview_set.first().id, 'PropertyState')

        result = {
            'status': 'success'
        }

        if view_id is not None:
            result.update({'match_merged_count': count})

        return result

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['POST'])
    def unmerge(self, request, pk=None):
        """
        Unmerge a property view into two property views
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        try:
            old_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                id=pk,
                property__organization_id=self.request.GET['organization_id']
            )
        except PropertyView.DoesNotExist:
            return {
                'status': 'error',
                'message': 'property view with id {} does not exist'.format(pk)
            }

        # Duplicate pairing
        paired_view_ids = list(TaxLotProperty.objects.filter(property_view_id=old_view.id)
                               .order_by('taxlot_view_id').values_list('taxlot_view_id', flat=True))

        # Capture previous associated labels
        label_ids = list(old_view.labels.all().values_list('id', flat=True))

        notes = old_view.notes.all()
        for note in notes:
            note.property_view = None

        merged_state = old_view.state
        if merged_state.data_state != DATA_STATE_MATCHING or merged_state.merge_state != MERGE_STATE_MERGED:
            return {
                'status': 'error',
                'message': 'property view with id {} is not a merged property view'.format(pk)
            }

        log = PropertyAuditLog.objects.select_related('parent_state1', 'parent_state2').filter(
            state=merged_state
        ).order_by('-id').first()

        if log.parent_state1 is None or log.parent_state2 is None:
            return {
                'status': 'error',
                'message': 'property view with id {} must have two parent states'.format(pk)
            }

        state1 = log.parent_state1
        state2 = log.parent_state2
        cycle_id = old_view.cycle_id

        # Clone the property record twice, then copy over meters
        old_property = old_view.property
        new_property = old_property
        new_property.id = None
        new_property.save()

        new_property_2 = Property.objects.get(pk=new_property.id)
        new_property_2.id = None
        new_property_2.save()

        Property.objects.get(pk=new_property.id).copy_meters(old_view.property_id)
        Property.objects.get(pk=new_property_2.id).copy_meters(old_view.property_id)

        # If canonical Property is NOT associated to a different -View, delete it
        if not PropertyView.objects.filter(property_id=old_view.property_id).exclude(id=old_view.id).exists():
            Property.objects.get(pk=old_view.property_id).delete()

        # Create the views
        new_view1 = PropertyView(
            cycle_id=cycle_id,
            property_id=new_property.id,
            state=state1
        )
        new_view2 = PropertyView(
            cycle_id=cycle_id,
            property_id=new_property_2.id,
            state=state2
        )

        # Mark the merged state as deleted
        merged_state.merge_state = MERGE_STATE_DELETE
        merged_state.save()

        # Change the merge_state of the individual states
        if log.parent1.name in ['Import Creation',
                                'Manual Edit'] and log.parent1.import_filename is not None:
            # State belongs to a new record
            state1.merge_state = MERGE_STATE_NEW
        else:
            state1.merge_state = MERGE_STATE_MERGED
        if log.parent2.name in ['Import Creation',
                                'Manual Edit'] and log.parent2.import_filename is not None:
            # State belongs to a new record
            state2.merge_state = MERGE_STATE_NEW
        else:
            state2.merge_state = MERGE_STATE_MERGED
        # In most cases data_state will already be 3 (DATA_STATE_MATCHING), but if one of the parents was a
        # de-duplicated record then data_state will be 0. This step ensures that the new states will be 3.
        state1.data_state = DATA_STATE_MATCHING
        state2.data_state = DATA_STATE_MATCHING
        state1.save()
        state2.save()

        # Delete the audit log entry for the merge
        log.delete()

        old_view.delete()
        new_view1.save()
        new_view2.save()

        # Asssociate labels
        label_objs = StatusLabel.objects.filter(pk__in=label_ids)
        new_view1.labels.set(label_objs)
        new_view2.labels.set(label_objs)

        # Duplicate notes to the new views
        for note in notes:
            created = note.created
            updated = note.updated
            note.id = None
            note.property_view = new_view1
            note.save()
            ids = [note.id]
            note.id = None
            note.property_view = new_view2
            note.save()
            ids.append(note.id)
            # Correct the created and updated times to match the original note
            Note.objects.filter(id__in=ids).update(created=created, updated=updated)

        for paired_view_id in paired_view_ids:
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           property_view_id=new_view1.id,
                           taxlot_view_id=paired_view_id).save()
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           property_view_id=new_view2.id,
                           taxlot_view_id=paired_view_id).save()

        return {
            'status': 'success',
            'view_id': new_view1.id
        }

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
            - name: used_only
              description: Determine whether or not to show only the used fields. Ones that have been mapped
              type: boolean
              required: false
              paramType: query
        """
        organization_id = int(request.query_params.get('organization_id'))
        only_used = request.query_params.get('only_used', False)
        columns = Column.retrieve_all(organization_id, 'property', only_used)
        organization = Organization.objects.get(pk=organization_id)
        unitted_columns = [add_pint_unit_suffix(organization, x) for x in columns]

        return JsonResponse({'status': 'success', 'columns': unitted_columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def mappable_columns(self, request):
        """
        List only property columns that are mappable
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        organization_id = int(request.query_params.get('organization_id'))
        columns = Column.retrieve_mapping_columns(organization_id, 'property')

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

    def _get_property_view(self, pk):
        """
        Return the property view

        :param pk: id, The property view ID
        :param cycle_pk: cycle
        :return:
        """
        try:
            property_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                id=pk,
                property__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success',
                'property_view': property_view
            }
        except PropertyView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'property view with id {} does not exist'.format(pk)
            }
        return result

    def _get_taxlots(self, pk):
        lot_view_pks = TaxLotProperty.objects.filter(property_view_id=pk).values_list(
            'taxlot_view_id', flat=True)
        lot_views = TaxLotView.objects.filter(pk__in=lot_view_pks).select_related('cycle', 'state').prefetch_related('labels')
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
              description: The primary key of the PropertyView
              required: true
              paramType: path
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        result = self._get_property_view(pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            result = {'status': 'success'}
            result.update(PropertyViewSerializer(property_view).data)
            # remove PropertyView id from result
            result.pop('id')

            # Grab extra_data columns to be shown in the result
            organization_id = request.query_params['organization_id']
            all_extra_data_columns = Column.objects.filter(
                organization_id=organization_id,
                is_extra_data=True,
                table_name='PropertyState').values_list('column_name', flat=True)

            result['state'] = PropertyStateSerializer(property_view.state,
                                                      all_extra_data_columns=all_extra_data_columns).data
            result['taxlots'] = self._get_taxlots(property_view.pk)
            result['history'], master = self.get_history(property_view)
            result = update_result_with_master(result, master)
            return JsonResponse(result, encoder=PintJSONEncoder, status=status.HTTP_200_OK)
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk=None):
        """
        Update a property and run the updated record through a match and merge
        round within it's current Cycle.

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
        """
        data = request.data

        result = self._get_property_view(pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            property_state_data = PropertyStateSerializer(property_view.state).data

            # get the property state information from the request
            new_property_state_data = data['state']

            # set empty strings to None
            for key, val in new_property_state_data.items():
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

                if 'extra_data' in new_property_state_data:
                    property_state_data['extra_data'].update(
                        new_property_state_data.pop('extra_data'))
                property_state_data.update(new_property_state_data)

                if log.name == 'Import Creation':
                    # Add new state by removing the existing ID.
                    property_state_data.pop('id')
                    # Remove the import_file_id for the first edit of a new record
                    # If the import file has been deleted and this value remains the serializer won't be valid
                    property_state_data.pop('import_file')
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

                        # save the property view so that the datetime gets updated on the property.
                        property_view.save()

                        count, view_id = match_merge_in_cycle(property_view.id, 'PropertyState')

                        if view_id is not None:
                            result.update({
                                'view_id': view_id,
                                'match_merged_count': count,
                            })

                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match',
                                  'Merge current state in migration']:
                    # Convert this to using the serializer to save the data. This will override the previous values
                    # in the state object.

                    # Note: We should be able to use partial update here and pass in the changed fields instead of the
                    # entire state_data.
                    updated_property_state_serializer = PropertyStateSerializer(
                        property_view.state,
                        data=property_state_data
                    )
                    if updated_property_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving
                        # relationships
                        updated_property_state_serializer.save()

                        result.update(
                            {'state': updated_property_state_serializer.data}
                        )

                        # save the property view so that the datetime gets updated on the property.
                        property_view.save()

                        count, view_id = match_merge_in_cycle(property_view.id, 'PropertyState')

                        if view_id is not None:
                            result.update({
                                'view_id': view_id,
                                'match_merged_count': count,
                            })

                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                updated_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                else:
                    result = {
                        'status': 'error',
                        'message': 'Unrecognized audit log name: ' + log.name
                    }
                    return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
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

        result = self._get_property_view(pk)
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

        result = self._get_property_view(pk)
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

        result = self._get_property_view(pk)
        if result.get('status', None) != 'error':
            pv = result.pop('property_view')
            property_state_id = pv.state.pk
            join = PropertyMeasure.objects.filter(
                property_state_id=property_state_id).select_related(
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
        else:
            return JsonResponse(result)


def diffupdate(old, new):
    """Returns lists of fields changed"""
    changed_fields = []
    changed_extra_data = []
    for k, v in new.items():
        if old.get(k, None) != v or k not in old:
            changed_fields.append(k)
    if 'extra_data' in changed_fields:
        changed_fields.remove('extra_data')
        changed_extra_data, _ = diffupdate(old['extra_data'], new['extra_data'])
    return changed_fields, changed_extra_data
