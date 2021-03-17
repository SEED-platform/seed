"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from collections import namedtuple

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Subquery
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models import (AUDIT_USER_EDIT, DATA_STATE_MATCHING,
                         MERGE_STATE_DELETE, MERGE_STATE_MERGED,
                         MERGE_STATE_NEW, VIEW_LIST, VIEW_LIST_TAXLOT, Column,
                         ColumnListProfile, ColumnListProfileColumn, Cycle,
                         Note, PropertyView, StatusLabel, TaxLot,
                         TaxLotAuditLog, TaxLotProperty, TaxLotState,
                         TaxLotView)
from seed.serializers.pint import apply_display_unit_preferences
from seed.serializers.properties import PropertyViewSerializer
from seed.serializers.taxlots import (TaxLotSerializer, TaxLotStateSerializer,
                                      TaxLotViewSerializer,
                                      UpdateTaxLotPayloadSerializer)
from seed.utils.api import OrgMixin, ProfileIdMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.labels import get_labels
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_taxlots
from seed.utils.properties import (get_changed_fields,
                                   pair_unpair_property_taxlot,
                                   update_result_with_master)
from seed.utils.taxlots import taxlots_across_cycles

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class TaxlotViewSet(viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotSerializer
    parser_classes = (JSONParser,)
    _organization = None

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(required=True)],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'selected': ['integer'],
            },
            description='IDs for taxlots to be checked for which labels are applied.'
        )
    )
    @action(detail=False, methods=['POST'])
    def labels(self, request):
        """
        Returns a list of all labels where the is_applied field
        in the response pertains to the labels applied to taxlot_view
        """
        labels = StatusLabel.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        super_organization = self.get_organization(request)
        # TODO: refactor to avoid passing request here
        return get_labels(request, labels, super_organization, 'taxlot_view')

    def _get_filtered_results(self, request, profile_id):
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = self.get_organization(request)
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

        # Return taxlot views limited to the 'taxlot_view_ids' list.  Otherwise, if selected is empty, return all
        if 'taxlot_view_ids' in request.data and request.data['taxlot_view_ids']:
            taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
                .filter(id__in=request.data['taxlot_view_ids'], taxlot__organization_id=org_id,
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
                profile = ColumnListProfile.objects.get(
                    organization=org,
                    id=profile_id,
                    profile_location=VIEW_LIST,
                    inventory_type=VIEW_LIST_TAXLOT
                )
                show_columns = list(ColumnListProfileColumn.objects.filter(
                    column_list_profile_id=profile.id
                ).values_list('column_id', flat=True))
            except ColumnListProfile.DoesNotExist:
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

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle',
                required=True,
                description='The ID of the cycle to get taxlots'
            ),
            AutoSchemaHelper.query_integer_field(
                'page',
                required=False,
                description='The current page of taxlots to return'
            ),
            AutoSchemaHelper.query_integer_field(
                'per_page',
                required=False,
                description='The number of items per page to return'
            ),
            AutoSchemaHelper.query_integer_field(
                'profile_id',
                required=False,
                description='The ID of the column profile to use'
            )
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        List all the properties
        """
        return self._get_filtered_results(request, profile_id=-1)

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'organization_id': 'integer',
                'profile_id': 'integer',
                'cycle_ids': ['integer'],
            },
            required=['organization_id', 'cycle_ids'],
            description='Properties:\n'
                        '- organization_id: ID of organization\n'
                        '- profile_id: Either an id of a list settings profile, '
                        'or undefined\n'
                        '- cycle_ids: The IDs of the cycle to get taxlots'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def filter_by_cycle(self, request):
        """
        List all the taxlots with all columns
        """
        # NOTE: we are using a POST http method b/c swagger and django handle
        # arrays differently in query parameters. ie this is just simpler
        org_id = request.data.get('organization_id', None)
        profile_id = request.data.get('profile_id', -1)
        cycle_ids = request.data.get('cycle_ids', [])

        if not org_id:
            return JsonResponse(
                {'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                status=status.HTTP_400_BAD_REQUEST)

        response = taxlots_across_cycles(org_id, profile_id, cycle_ids)

        return JsonResponse(response)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle',
                required=True,
                description='The ID of the cycle to get tax lots'
            ),
            AutoSchemaHelper.query_integer_field(
                'page',
                required=False,
                description='The current page of taxlots to return'
            ),
            AutoSchemaHelper.query_integer_field(
                'per_page',
                required=False,
                description='The number of items per page to return'
            ),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'profile_id': 'integer',
                'taxlot_view_ids': ['integer'],
            },
            required=['profile_id'],
            description='Properties:\n'
                        '- profile_id: Either an id of a list settings profile, or undefined\n'
                        '- taxlot_view_ids: List of taxlot view ids'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def filter(self, request):
        """
        List all the tax lots
        """
        if 'profile_id' not in request.data:
            profile_id = None
        else:
            if request.data['profile_id'] == 'None':
                profile_id = None
            else:
                profile_id = request.data['profile_id']

        return self._get_filtered_results(request, profile_id=profile_id)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'taxlot_view_ids': ['integer']
            },
            required=['taxlot_view_ids'],
            description='Properties:\n'
                        '- taxlot_view_ids: Array containing tax lot state ids to merge'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def merge(self, request):
        """
        Merge multiple tax lot records into a single new record, and run this
        new record through a match and merge round within it's current Cycle.
        """
        body = request.data
        organization_id = int(self.get_organization(request))

        taxlot_view_ids = body.get('taxlot_view_ids', [])
        taxlot_states = TaxLotView.objects.filter(
            id__in=taxlot_view_ids,
            cycle__organization_id=organization_id
        ).values('id', 'state_id')
        # get the state ids in order according to the given view ids
        taxlot_states_dict = {t['id']: t['state_id'] for t in taxlot_states}
        taxlot_state_ids = [
            taxlot_states_dict[view_id]
            for view_id in taxlot_view_ids if view_id in taxlot_states_dict
        ]

        if len(taxlot_state_ids) != len(taxlot_view_ids):
            return {
                'status': 'error',
                'message': 'All records not found.'
            }

        # Check the number of taxlot_state_ids to merge
        if len(taxlot_state_ids) < 2:
            return JsonResponse({
                'status': 'error',
                'message': 'At least two ids are necessary to merge'
            }, status=status.HTTP_400_BAD_REQUEST)

        merged_state = merge_taxlots(taxlot_state_ids, organization_id, 'Manual Match')

        merge_count, link_count, view_id = match_merge_link(merged_state.taxlotview_set.first().id, 'TaxLotState')

        result = {
            'status': 'success'
        }

        result.update({
            'match_merged_count': merge_count,
            'match_link_count': link_count,
        })

        return result

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def unmerge(self, request, pk=None):
        """
        Unmerge a taxlot view into two taxlot views
        """
        try:
            old_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=pk,
                taxlot__organization_id=self.get_organization(request)
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['GET'])
    def links(self, request, pk=None):
        """
        Get taxlot details for each linked taxlot across org cycles
        """
        organization_id = self.get_organization(request)
        base_view = TaxLotView.objects.select_related('cycle').filter(
            pk=pk,
            cycle__organization_id=organization_id
        )

        if base_view.exists():
            result = {'data': []}

            linked_views = TaxLotView.objects.select_related('cycle').filter(
                taxlot_id=base_view.get().taxlot_id,
                cycle__organization_id=organization_id
            ).order_by('-cycle__start')
            for linked_view in linked_views:
                state_data = TaxLotStateSerializer(linked_view.state).data

                state_data['cycle_id'] = linked_view.cycle.id
                state_data['view_id'] = linked_view.id
                result['data'].append(state_data)

            return JsonResponse(result, status=status.HTTP_200_OK)
        else:
            result = {
                'status': 'error',
                'message': 'property view with id {} does not exist in given organization'.format(pk)
            }
            return JsonResponse(result)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def match_merge_link(self, request, pk=None):
        """
        Runs match merge link for an individual taxlot.

        Note that this method can return a view_id of None if the given -View
        was not involved in a merge.
        """
        org_id = self.get_organization(request)

        taxlot_view = TaxLotView.objects.get(
            pk=pk,
            cycle__organization_id=org_id
        )
        merge_count, link_count, view_id = match_merge_link(taxlot_view.pk, 'TaxLotState')

        result = {
            'view_id': view_id,
            'match_merged_count': merge_count,
            'match_link_count': link_count,
        }

        return JsonResponse(result)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'property_id',
                required=True,
                description='The property id to pair up with this taxlot'
            )
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['PUT'])
    def pair(self, request, pk=None):
        """
        Pair a property to this taxlot
        """
        organization_id = int(self.get_organization(request))
        property_id = int(request.query_params.get('property_id'))
        taxlot_id = int(pk)
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, True)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'property_id',
                required=True,
                description='The property id to unpair from this taxlot'
            )
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['PUT'])
    def unpair(self, request, pk=None):
        """
        Unpair a property from this taxlot
        """
        organization_id = int(self.get_organization(request))
        property_id = int(request.query_params.get('property_id'))
        taxlot_id = int(pk)
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, False)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'taxlot_view_ids': ['integer']
            },
            required=['taxlot_view_ids'],
            description='A list of taxlot view ids to delete'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['DELETE'])
    def batch_delete(self, request):
        """
        Batch delete several tax lots
        """
        org_id = self.get_organization(request)

        taxlot_view_ids = request.data.get('taxlot_view_ids', [])
        taxlot_state_ids = TaxLotView.objects.filter(
            id__in=taxlot_view_ids,
            cycle__organization_id=org_id
        ).values_list('state_id', flat=True)
        resp = TaxLotState.objects.filter(pk__in=Subquery(taxlot_state_ids)).delete()

        if resp[0] == 0:
            return JsonResponse({'status': 'warning', 'message': 'No action was taken'})

        return JsonResponse({'status': 'success', 'taxlots': resp[1]['seed.TaxLotState']})

    def _get_taxlot_view(self, taxlot_pk):
        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=taxlot_pk,
                taxlot__organization_id=self.get_organization(self.request)
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

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    def retrieve(self, request, pk):
        """
        Get taxlot details
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=UpdateTaxLotPayloadSerializer,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk):
        """
        Update a taxlot and run the updated record through a match and merge
        round within it's current Cycle.
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

            changed_fields, previous_data = get_changed_fields(taxlot_state_data, new_taxlot_state_data)
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

                # if checks above pass, create an exact copy of the current state for historical purposes
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
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_taxlot_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                # redo assignment of this variable in case this was an initial edit
                taxlot_state_data = TaxLotStateSerializer(taxlot_view.state).data

                if 'extra_data' in new_taxlot_state_data:
                    taxlot_state_data['extra_data'].update(
                        new_taxlot_state_data['extra_data']
                    )

                taxlot_state_data.update(
                    {k: v for k, v in new_taxlot_state_data.items() if k != 'extra_data'}
                )

                log = TaxLotAuditLog.objects.select_related().filter(
                    state=taxlot_view.state
                ).order_by('-id').first()

                if log.name in ['Manual Edit', 'Manual Match', 'System Match', 'Merge current state in migration']:
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

                        Note.create_from_edit(request.user.id, taxlot_view, new_taxlot_state_data, previous_data)

                        merge_count, link_count, view_id = match_merge_link(taxlot_view.id, 'TaxLotState')

                        result.update({
                            'view_id': view_id,
                            'match_merged_count': merge_count,
                            'match_link_count': link_count,
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
