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
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization
)
from seed.models import (
    AUDIT_USER_EDIT,
    DATA_STATE_MATCHING,
    MERGE_STATE_NEW,
    MERGE_STATE_MERGED,
    MERGE_STATE_DELETE,
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
    Cycle,
    Note,
    PropertyView,
    StatusLabel,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
    TaxLot,
    VIEW_LIST,
    VIEW_LIST_TAXLOT)
from seed.serializers.pint import (
    apply_display_unit_preferences,
    add_pint_unit_suffix
)
from seed.serializers.properties import (
    PropertyViewSerializer
)
from seed.serializers.taxlots import (
    TaxLotSerializer,
    TaxLotStateSerializer,
    TaxLotViewSerializer
)
from seed.utils.api import api_endpoint_class, ProfileIdMixin
from seed.utils.merge import merge_taxlots
from seed.utils.properties import (
    get_changed_fields,
    pair_unpair_property_taxlot,
    update_result_with_master
)

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


class TaxLotViewSet(GenericViewSet, ProfileIdMixin):
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotSerializer

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

        # Return taxlot views limited to the 'inventory_ids' list.  Otherwise, if selected is empty, return all
        if 'inventory_ids' in request.data and request.data['inventory_ids']:
            taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
                .filter(taxlot_id__in=request.data['inventory_ids'], taxlot__organization_id=org_id,
                        cycle=cycle) \
                .order_by('id')
        else:
            taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
                .filter(taxlot__organization_id=org_id, cycle=cycle) \
                .order_by('id')

        paginator = Paginator(taxlot_views_list, per_page)

        try:
            taxlot_views = paginator.page(page)
            page = int(page)
        except PageNotAnInteger:
            taxlot_views = paginator.page(1)
            page = 1
        except EmptyPage:
            taxlot_views = paginator.page(paginator.num_pages)
            page = paginator.num_pages

        org = Organization.objects.get(pk=org_id)

        # Retrieve all the columns that are in the db for this organization
        columns_from_database = Column.retrieve_all(org_id, 'taxlot', False)

        # This uses an old method of returning the show_columns. There is a new method that
        # is preferred in v2.1 API with the ProfileIdMixin.
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
                    inventory_type=VIEW_LIST_TAXLOT
                )
                show_columns = list(ColumnListSettingColumn.objects.filter(
                    column_list_setting_id=profile.id
                ).values_list('column_id', flat=True))
            except ColumnListSetting.DoesNotExist:
                show_columns = None

        related_results = TaxLotProperty.get_related(taxlot_views, show_columns,
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

    # @require_organization_id
    # @require_organization_membership
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
              description: The ID of the cycle to get taxlots
              required: true
              paramType: query
            - name: page
              description: The current page of taxlots to return
              required: false
              paramType: query
            - name: per_page
              description: The number of items per page to return
              required: false
              paramType: query
        """
        return self._get_filtered_results(request, profile_id=-1)

    # @require_organization_id
    # @require_organization_membership
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
              description: The ID of the cycle to get taxlots
              required: true
              paramType: query
            - name: page
              description: The current page of taxlots to return
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

        return self._get_filtered_results(request, profile_id=profile_id)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['POST'])
    def merge(self, request):
        """
        Merge multiple tax lot records into a single new record, and run this
        new record through a match and merge round within it's current Cycle.
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: state_ids
              description: Array containing tax lot state ids to merge
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

        merged_state = merge_taxlots(state_ids, organization_id, 'Manual Match')

        count, view_id = match_merge_in_cycle(merged_state.taxlotview_set.first().id, 'TaxLotState')

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
        Unmerge a taxlot view into two taxlot views
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        try:
            old_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
        except TaxLotView.DoesNotExist:
            return {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(pk)
            }

        # Duplicate pairing
        paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id=old_view.id)
                               .order_by('property_view_id').values_list('property_view_id',
                                                                         flat=True))

        # Capture previous associated labels
        label_ids = list(old_view.labels.all().values_list('id', flat=True))

        notes = old_view.notes.all()
        for note in notes:
            note.taxlot_view = None

        merged_state = old_view.state
        if merged_state.data_state != DATA_STATE_MATCHING or merged_state.merge_state != MERGE_STATE_MERGED:
            return {
                'status': 'error',
                'message': 'taxlot view with id {} is not a merged taxlot view'.format(pk)
            }

        log = TaxLotAuditLog.objects.select_related('parent_state1', 'parent_state2').filter(
            state=merged_state
        ).order_by('-id').first()

        if log.parent_state1 is None or log.parent_state2 is None:
            return {
                'status': 'error',
                'message': 'taxlot view with id {} must have two parent states'.format(pk)
            }

        state1 = log.parent_state1
        state2 = log.parent_state2
        cycle_id = old_view.cycle_id

        # Clone the taxlot record twice
        old_taxlot = old_view.taxlot
        new_taxlot = old_taxlot
        new_taxlot.id = None
        new_taxlot.save()

        new_taxlot_2 = TaxLot.objects.get(pk=new_taxlot.pk)
        new_taxlot_2.id = None
        new_taxlot_2.save()

        # If the canonical TaxLot is NOT associated to another -View
        if not TaxLotView.objects.filter(taxlot_id=old_view.taxlot_id).exclude(pk=old_view.id).exists():
            TaxLot.objects.get(pk=old_view.taxlot_id).delete()

        # Create the views
        new_view1 = TaxLotView(
            cycle_id=cycle_id,
            taxlot_id=new_taxlot.id,
            state=state1
        )
        new_view2 = TaxLotView(
            cycle_id=cycle_id,
            taxlot_id=new_taxlot_2.id,
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
            note.taxlot_view = new_view1
            note.save()
            ids = [note.id]
            note.id = None
            note.taxlot_view = new_view2
            note.save()
            ids.append(note.id)
            # Correct the created and updated times to match the original note
            Note.objects.filter(id__in=ids).update(created=created, updated=updated)

        for paired_view_id in paired_view_ids:
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           taxlot_view_id=new_view1.id,
                           property_view_id=paired_view_id).save()
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           taxlot_view_id=new_view2.id,
                           property_view_id=paired_view_id).save()

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
        Pair a property to this taxlot
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: property_id
              description: The property id to pair up with this taxlot
              required: true
              paramType: query
            - name: pk
              description: pk (taxlot ID)
              required: true
              paramType: path
        """
        # TODO: Call with PUT /api/v2/taxlots/1/pair/?property_id=1&organization_id=1
        organization_id = int(request.query_params.get('organization_id'))
        property_id = int(request.query_params.get('property_id'))
        taxlot_id = int(pk)
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, True)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['PUT'])
    def unpair(self, request, pk=None):
        """
        Unpair a property from this taxlot
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: property_id
              description: The property id to unpair from this taxlot
              required: true
              paramType: query
            - name: pk
              description: pk (taxlot ID)
              required: true
              paramType: path
        """
        # TODO: Call with PUT /api/v2/taxlots/1/unpair/?property_id=1&organization_id=1
        organization_id = int(request.query_params.get('organization_id'))
        property_id = int(request.query_params.get('property_id'))
        taxlot_id = int(pk)
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, False)

    # @require_organization_id
    # @require_organization_membership
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def columns(self, request):
        """
        List all tax lot columns
        ---
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
        organization = Organization.objects.get(pk=organization_id)

        only_used = request.query_params.get('only_used', False)
        columns = Column.retrieve_all(organization_id, 'taxlot', only_used)
        unitted_columns = [add_pint_unit_suffix(organization, x) for x in columns]

        return JsonResponse({'status': 'success', 'columns': unitted_columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def mappable_columns(self, request):
        """
        List only taxlot columns that are mappable
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        organization_id = int(request.query_params.get('organization_id'))
        columns = Column.retrieve_mapping_columns(organization_id, 'taxlot')

        return JsonResponse({'status': 'success', 'columns': columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['DELETE'])
    def batch_delete(self, request):
        """
        Batch delete several tax lots
        ---
        parameters:
            - name: selected
              description: A list of taxlot ids to delete
              many: true
              required: true
        """
        taxlot_states = request.data.get('selected', [])
        resp = TaxLotState.objects.filter(pk__in=taxlot_states).delete()

        if resp[0] == 0:
            return JsonResponse({'status': 'warning', 'message': 'No action was taken'})

        return JsonResponse({'status': 'success', 'taxlots': resp[1]['seed.TaxLotState']})

    def _get_taxlot_view(self, taxlot_pk):
        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=taxlot_pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success',
                'taxlot_view': taxlot_view
            }
        except TaxLotView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(taxlot_pk)
            }
        return result

    def get_history(self, taxlot_view):
        """Return history in reverse order"""

        # access the history from the property state
        history, master = taxlot_view.state.history()

        # convert the history and master states to StateSerializers
        master['state'] = TaxLotStateSerializer(master['state_data']).data
        del master['state_data']
        del master['state_id']

        for h in history:
            h['state'] = TaxLotStateSerializer(h['state_data']).data
            del h['state_data']
            del h['state_id']

        return history, master

    def _get_properties(self, taxlot_view_pk):
        property_view_pks = TaxLotProperty.objects.filter(
            taxlot_view_id=taxlot_view_pk
        ).values_list('property_view_id', flat=True)
        property_views = PropertyView.objects.filter(
            pk__in=property_view_pks
        ).select_related('cycle', 'state')
        properties = []
        for property_view in property_views:
            properties.append(PropertyViewSerializer(property_view).data)
        return properties

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def properties(self, pk):
        """
        Get related properties for this tax lot
        """
        return JsonResponse(self._get_properties(pk))

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk):
        """
        Get taxlot details
        ---
        parameters:
            - name: pk
              description: The primary key of the TaxLotView
              required: true
              paramType: path
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        result = self._get_taxlot_view(pk)
        if result.get('status', None) != 'error':
            taxlot_view = result.pop('taxlot_view')
            result.update(TaxLotViewSerializer(taxlot_view).data)
            # remove TaxLotView id from result
            result.pop('id')

            result['state'] = TaxLotStateSerializer(taxlot_view.state).data
            result['properties'] = self._get_properties(taxlot_view.pk)
            result['history'], master = self.get_history(taxlot_view)
            result = update_result_with_master(result, master)
            return JsonResponse(result, status=status.HTTP_200_OK)
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk):
        """
        Update a taxlot and run the updated record through a match and merge
        round within it's current Cycle.
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        data = request.data

        result = self._get_taxlot_view(pk)
        if result.get('status', 'error') != 'error':
            taxlot_view = result.pop('taxlot_view')
            taxlot_state_data = TaxLotStateSerializer(taxlot_view.state).data

            # get the taxlot state information from the request
            new_taxlot_state_data = data['state']

            # set empty strings to None
            for key, val in new_taxlot_state_data.items():
                if val == '':
                    new_taxlot_state_data[key] = None

            changed_fields = get_changed_fields(taxlot_state_data, new_taxlot_state_data)
            if not changed_fields:
                result.update(
                    {'status': 'success', 'message': 'Records are identical'}
                )
                return JsonResponse(result, status=status.HTTP_204_NO_CONTENT)
            else:
                # Not sure why we are going through the pain of logging this all right now... need to
                # reevaluate this.
                log = TaxLotAuditLog.objects.select_related().filter(
                    state=taxlot_view.state
                ).order_by('-id').first()

                if 'extra_data' in new_taxlot_state_data:
                    taxlot_state_data['extra_data'].update(new_taxlot_state_data.pop('extra_data'))
                taxlot_state_data.update(new_taxlot_state_data)

                if log.name == 'Import Creation':
                    # Add new state by removing the existing ID.
                    taxlot_state_data.pop('id')
                    # Remove the import_file_id for the first edit of a new record
                    # If the import file has been deleted and this value remains the serializer won't be valid
                    taxlot_state_data.pop('import_file')
                    new_taxlot_state_serializer = TaxLotStateSerializer(
                        data=taxlot_state_data
                    )
                    if new_taxlot_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving relationships
                        new_state = new_taxlot_state_serializer.save()

                        # then assign this state to the property view and save the whole view
                        taxlot_view.state = new_state
                        taxlot_view.save()

                        TaxLotAuditLog.objects.create(organization=log.organization,
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
                            {'state': new_taxlot_state_serializer.data}
                        )

                        # save the property view so that the datetime gets updated on the property.
                        taxlot_view.save()

                        count, view_id = match_merge_in_cycle(taxlot_view.id, 'TaxLotState')

                        if view_id is not None:
                            result.update({
                                'view_id': view_id,
                                'match_merged_count': count,
                            })

                        return JsonResponse(result, status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_taxlot_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match',
                                  'Merge current state in migration']:
                    # Convert this to using the serializer to save the data. This will override the
                    # previous values in the state object.

                    # Note: We should be able to use partial update here and pass in the changed
                    # fields instead of the entire state_data.
                    updated_taxlot_state_serializer = TaxLotStateSerializer(
                        taxlot_view.state,
                        data=taxlot_state_data
                    )
                    if updated_taxlot_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving
                        # relationships
                        updated_taxlot_state_serializer.save()

                        result.update(
                            {'state': updated_taxlot_state_serializer.data}
                        )

                        # save the property view so that the datetime gets updated on the property.
                        taxlot_view.save()

                        count, view_id = match_merge_in_cycle(taxlot_view.id, 'TaxLotState')

                        if view_id is not None:
                            result.update({
                                'view_id': view_id,
                                'match_merged_count': count,
                            })

                        return JsonResponse(result, status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                updated_taxlot_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                else:
                    result = {
                        'status': 'error',
                        'message': 'Unrecognized audit log name: ' + log.name
                    }
                    return JsonResponse(result, status=status.HTTP_204_NO_CONTENT)
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
