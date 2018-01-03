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
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    AUDIT_USER_EDIT,
    Column,
    Cycle,
    PropertyView,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    TaxLotView
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
        """
        organization_id = int(request.query_params.get('organization_id'))
        columns = Column.retrieve_all(organization_id, 'taxlot')

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
    def view(self, request, pk=None):
        """
        Get the TaxLot view
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
        result = self._get_taxlot_view(pk, cycle_pk)
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
        Get property details
        ---
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the taxlot view
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
        result = self._get_taxlot_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            taxlot_view = result.pop('taxlot_view')
            result.update(TaxLotViewSerializer(taxlot_view).data)
            # remove TaxLotView id from result
            result.pop('id')
            result['taxlot']['db_taxlot_updated'] = result['taxlot']['updated']
            result['taxlot']['db_taxlot_created'] = result['taxlot']['created']
            result['state'] = TaxLotStateSerializer(taxlot_view.state).data
            result['properties'] = self._get_properties(taxlot_view.pk)
            result['history'], master = self.get_history(taxlot_view)
            result = update_result_with_master(result, master)
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk):
        """
        Update a taxlot
        ---
        parameters:
            - name: cycle_id
              description: The cycle id for filtering the taxlot view
              required: true
              paramType: query
        """
        data = request.data
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_taxlot_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            taxlot_view = result.pop('taxlot_view')
            taxlot_state_data = TaxLotStateSerializer(taxlot_view.state).data
            new_taxlot_state_data = data['state']

            changed = True
            for key, val in new_taxlot_state_data.iteritems():
                if val == '':
                    new_taxlot_state_data[key] = None
            changed_fields = get_changed_fields(
                taxlot_state_data, new_taxlot_state_data
            )
            if not changed_fields:
                changed = False
            if not changed:
                result.update(
                    {'status': 'error', 'message': 'Nothing to update'}
                )
                status_code = 422  # status.HTTP_422_UNPROCESSABLE_ENTITY
            else:
                log = TaxLotAuditLog.objects.select_related().filter(
                    state=taxlot_view.state
                ).order_by('-id').first()

                if 'extra_data' in new_taxlot_state_data.keys():
                    taxlot_state_data['extra_data'].update(new_taxlot_state_data.pop('extra_data'))
                taxlot_state_data.update(new_taxlot_state_data)

                if log.name == 'Import Creation':
                    # Add new state
                    taxlot_state_data.pop('id')
                    new_taxlot_state_serializer = TaxLotStateSerializer(
                        data=taxlot_state_data
                    )
                    if new_taxlot_state_serializer.is_valid():
                        new_state = new_taxlot_state_serializer.save()
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
                            {'state': new_taxlot_state_serializer.validated_data}
                        )
                        # Removing organization key AND import_file key because they're not JSON-serializable
                        # TODO find better solution
                        result['state'].pop('organization')
                        result['state'].pop('import_file')
                        status_code = status.HTTP_201_CREATED
                    else:
                        result.update(
                            {'status': 'error', 'message': 'Invalid Data'}
                        )
                        status_code = 422  # status.HTTP_422_UNPROCESSABLE_ENTITY
                elif log.name in ['Manual Edit', 'Manual Match', 'System Match',
                                  'Merge current state in migration']:
                    # Override previous edit state or merge state
                    state = taxlot_view.state
                    for key, value in new_taxlot_state_data.iteritems():
                        setattr(state, key, value)
                    state.save()

                    result.update(
                        {'state': TaxLotStateSerializer(state).data}
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

            # save the tax lot view, even if it hasn't changed so that the datetime gets updated on the taxlot.
            taxlot_view.save()
        else:
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)
