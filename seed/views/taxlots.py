# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

from django.apps import apps
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.data_importer.views import ImportFileViewSet
from seed.decorators import ajax_request_class
from seed.lib.merging import merging
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    AUDIT_IMPORT,
    AUDIT_USER_EDIT,
    DATA_STATE_MATCHING,
    MERGE_STATE_UNKNOWN,
    MERGE_STATE_NEW,
    MERGE_STATE_MERGED,
    MERGE_STATE_DELETE,
    Column,
    Cycle,
    PropertyView,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
    TaxLot,
)
from seed.serializers.pint import PintJSONEncoder
from seed.serializers.properties import (
    PropertyViewSerializer
)
from seed.serializers.taxlots import (
    TaxLotSerializer,
    TaxLotStateSerializer,
    TaxLotViewSerializer
)
from seed.utils.api import api_endpoint_class
from seed.utils.properties import (
    get_changed_fields,
    pair_unpair_property_taxlot,
    update_result_with_master
)

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


class TaxLotViewSet(GenericViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotSerializer

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

        taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
            .filter(taxlot__organization_id=request.query_params['organization_id'], cycle=cycle) \
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
            'results': TaxLotProperty.get_related(taxlot_views, columns)
        }

        return JsonResponse(response, encoder=PintJSONEncoder)

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
        return self._get_filtered_results(request, columns=[])

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
    @list_route(methods=['POST'])
    def merge(self, request):
        """
        Merge multiple tax lot records into a single new record
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

        audit_log = TaxLotAuditLog
        inventory = TaxLot
        label = apps.get_model('seed', 'TaxLot_labels')
        state = TaxLotState
        view = TaxLotView

        index = 1
        merged_state = None
        while index < len(state_ids):
            # state 1 is the base, state 2 is merged on top of state 1
            # Use index 0 the first time through, merged_state from then on
            if index == 1:
                state1 = state.objects.get(id=state_ids[index - 1])
            else:
                state1 = merged_state
            state2 = state.objects.get(id=state_ids[index])

            merged_state = state.objects.create(organization_id=organization_id)
            merged_state, changes = merging.merge_state(merged_state,
                                                        state1,
                                                        state2,
                                                        merging.get_state_attrs([state1, state2]),
                                                        default=state2)

            state_1_audit_log = audit_log.objects.filter(state=state1).first()
            state_2_audit_log = audit_log.objects.filter(state=state2).first()

            audit_log.objects.create(organization=state1.organization,
                                     parent1=state_1_audit_log,
                                     parent2=state_2_audit_log,
                                     parent_state1=state1,
                                     parent_state2=state2,
                                     state=merged_state,
                                     name='Manual Match',
                                     description='Automatic Merge',
                                     import_filename=None,
                                     record_type=AUDIT_IMPORT)

            # Set the merged_state to merged
            merged_state.data_state = DATA_STATE_MATCHING
            merged_state.merge_state = MERGE_STATE_MERGED
            merged_state.save()
            state1.merge_state = MERGE_STATE_UNKNOWN
            state1.save()
            state2.merge_state = MERGE_STATE_UNKNOWN
            state2.save()

            # Delete existing views and inventory records
            views = view.objects.filter(state_id__in=[state1.id, state2.id])
            view_ids = list(views.values_list('id', flat=True))
            cycle_id = views.first().cycle_id
            label_ids = []
            # Get paired view ids
            paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id__in=view_ids)
                                   .order_by('property_view_id').distinct('property_view_id')
                                   .values_list('property_view_id', flat=True))
            for v in views:
                label_ids.extend(list(v.taxlot.labels.all().values_list('id', flat=True)))
                v.taxlot.delete()
            label_ids = list(set(label_ids))

            # Create new inventory record
            inventory_record = inventory(organization_id=organization_id)
            inventory_record.save()

            # Create new labels and view
            for label_id in label_ids:
                label(taxlot_id=inventory_record.id, statuslabel_id=label_id).save()
            new_view = view(cycle_id=cycle_id, state_id=merged_state.id,
                            taxlot_id=inventory_record.id)
            new_view.save()

            # Delete existing pairs and re-pair all to new view
            # Probably already deleted by cascade
            TaxLotProperty.objects.filter(taxlot_view_id__in=view_ids).delete()
            for paired_view_id in paired_view_ids:
                TaxLotProperty(primary=True,
                               cycle_id=cycle_id,
                               property_view_id=paired_view_id,
                               taxlot_view_id=new_view.id).save()

            index += 1

        return {
            'status': 'success'
        }

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

        label = apps.get_model('seed', 'TaxLot_labels')
        state1 = log.parent_state1
        state2 = log.parent_state2
        cycle_id = old_view.cycle_id

        # Clone the taxlot record, then the labels
        old_taxlot = old_view.taxlot
        label_ids = list(old_taxlot.labels.all().values_list('id', flat=True))
        new_taxlot = old_taxlot
        new_taxlot.id = None
        new_taxlot.save()

        for label_id in label_ids:
            label(taxlot_id=new_taxlot.id, statuslabel_id=label_id).save()

        # Create the views
        new_view1 = TaxLotView(
            cycle_id=cycle_id,
            taxlot_id=new_taxlot.id,
            state=state1
        )
        new_view2 = TaxLotView(
            cycle_id=cycle_id,
            taxlot_id=old_view.taxlot_id,
            state=state2
        )

        # Mark the merged state as deleted
        merged_state.merge_state = MERGE_STATE_DELETE
        merged_state.save()

        # Change the merge_state of the individual states
        if log.parent1.name in ['Import Creation', 'Manual Edit'] and log.parent1.import_filename is not None:
            # State belongs to a new record
            state1.merge_state = MERGE_STATE_NEW
        else:
            state1.merge_state = MERGE_STATE_MERGED
        if log.parent2.name in ['Import Creation', 'Manual Edit'] and log.parent2.import_filename is not None:
            # State belongs to a new record
            state2.merge_state = MERGE_STATE_NEW
        else:
            state2.merge_state = MERGE_STATE_MERGED
        state1.save()
        state2.save()

        # Delete the audit log entry for the merge
        log.delete()

        # Duplicate pairing
        paired_view_ids = list(TaxLotProperty.objects.filter(taxlot_view_id=old_view.id)
                               .order_by('property_view_id').values_list('property_view_id', flat=True))

        old_view.delete()
        new_view1.save()
        new_view2.save()

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
        only_used = request.query_params.get('only_used', False)
        columns = Column.retrieve_all(organization_id, 'taxlot', only_used)

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

    def _get_taxlot_view(self, taxlot_pk, cycle_pk):
        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                taxlot_id=taxlot_pk,
                cycle_id=cycle_pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success',
                'taxlot_view': taxlot_view
            }
        except TaxLotView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(
                    taxlot_pk)
            }
        except TaxLotView.MultipleObjectsReturned:
            result = {
                'status': 'error',
                'message': 'Multiple taxlot views with id {}'.format(
                    taxlot_pk)
            }
        return result

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def view(self, pk=None):
        """
        Get the TaxLot view
        """
        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success',
                'taxlot_view': taxlot_view
            }
        except TaxLotView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(pk)
            }
        return JsonResponse(result)

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
        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success'
            }
            result.update(TaxLotViewSerializer(taxlot_view).data)
            # remove TaxLotView id from result
            result.pop('id')

            result['state'] = TaxLotStateSerializer(taxlot_view.state).data
            result['properties'] = self._get_properties(taxlot_view.pk)
            result['history'], master = self.get_history(taxlot_view)
            result = update_result_with_master(result, master)
            status_code = status.HTTP_200_OK
        except TaxLotView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(pk)
            }
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk):
        """
        Update a taxlot
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        data = request.data

        try:
            taxlot_view = TaxLotView.objects.select_related(
                'taxlot', 'cycle', 'state'
            ).get(
                id=pk,
                taxlot__organization_id=self.request.GET['organization_id']
            )
            result = {
                'status': 'success'
            }
        except TaxLotView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'taxlot view with id {} does not exist'.format(pk)
            }
        if result.get('status', None) != 'error':
            taxlot_state_data = TaxLotStateSerializer(taxlot_view.state).data

            # get the taxlot state information from the request
            new_taxlot_state_data = data['state']

            # set empty strings to None
            for key, val in new_taxlot_state_data.iteritems():
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

                if 'extra_data' in new_taxlot_state_data.keys():
                    taxlot_state_data['extra_data'].update(new_taxlot_state_data.pop('extra_data'))
                taxlot_state_data.update(new_taxlot_state_data)

                if log.name == 'Import Creation':
                    # Add new state by removing the existing ID.
                    taxlot_state_data.pop('id')
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

                        return JsonResponse(result, status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_taxlot_state_serializer.errors)}
                        )
                        return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match', 'Merge current state in migration']:
                    # Convert this to using the serializer to save the data. This will override the previous values
                    # in the state object.

                    # Note: We should be able to use partial update here and pass in the changed fields instead of the
                    # entire state_data.
                    updated_taxlot_state_serializer = TaxLotStateSerializer(
                        taxlot_view.state,
                        data=taxlot_state_data
                    )
                    if updated_taxlot_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving relationships
                        updated_taxlot_state_serializer.save()

                        result.update(
                            {'state': updated_taxlot_state_serializer.data}
                        )

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

            # save the tax lot view, even if it hasn't changed so that the datetime gets updated on the taxlot.
            # Uhm, does this ever get called? There are a bunch of returns in the code above.
            taxlot_view.save()
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)
