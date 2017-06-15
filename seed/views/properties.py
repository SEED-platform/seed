# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import itertools
import json
import re
from collections import defaultdict
from os import path

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import model_to_dict
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import list_route, detail_route
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    Column, Cycle, AUDIT_USER_EDIT, PropertyAuditLog, PropertyState, PropertyView,
    TaxLotAuditLog, TaxLotView, TaxLotState, TaxLotProperty
)
from seed.serializers.properties import (
    PropertyStateSerializer, PropertyViewSerializer, PropertySerializer
)
from seed.serializers.taxlots import (
    TaxLotViewSerializer, TaxLotStateSerializer, TaxLotSerializer
)
from seed.utils.api import api_endpoint_class
from seed.utils.time import convert_to_js_timestamp

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


def unique(lol):
    """Calculate unique elements in a list of lists."""
    return sorted(set(itertools.chain.from_iterable(lol)))


def pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, pair):
    # TODO: validate against organization_id, make sure cycle_ids are the same

    try:
        property_view = PropertyView.objects.get(pk=property_id)
    except PropertyView.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'property view with id {} does not exist'.format(property_id)
        }, status=status.HTTP_404_NOT_FOUND)
    try:
        taxlot_view = TaxLotView.objects.get(pk=taxlot_id)
    except TaxLotView.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'tax lot view with id {} does not exist'.format(taxlot_id)
        }, status=status.HTTP_404_NOT_FOUND)

    pv_cycle = property_view.cycle_id
    tv_cycle = taxlot_view.cycle_id

    if pv_cycle != tv_cycle:
        return JsonResponse({
            'status': 'error',
            'message': 'Cycle mismatch between PropertyView and TaxLotView'
        }, status=status.HTTP_400_BAD_REQUEST)

    if pair:
        string = 'pair'

        if TaxLotProperty.objects.filter(property_view_id=property_id,
                                         taxlot_view_id=taxlot_id).exists():
            return JsonResponse({
                'status': 'success',
                'message': 'taxlot {} and property {} are already {}ed'.format(taxlot_id,
                                                                               property_id, string)
            })
        TaxLotProperty(
            primary=True,
            cycle_id=pv_cycle,
            property_view_id=property_id,
            taxlot_view_id=taxlot_id
        ).save()

        success = True
    else:
        string = 'unpair'

        if not TaxLotProperty.objects.filter(property_view_id=property_id,
                                             taxlot_view_id=taxlot_id).exists():
            return JsonResponse({
                'status': 'success',
                'message': 'taxlot {} and property {} are already {}ed'.format(taxlot_id,
                                                                               property_id, string)
            })
        TaxLotProperty.objects.filter(
            property_view_id=property_id,
            taxlot_view_id=taxlot_id).delete()

        success = True

    if success:
        return JsonResponse({
            'status': 'success',
            'message': 'taxlot {} and property {} are now {}ed'.format(taxlot_id, property_id,
                                                                       string)
        })
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Could not {} because reasons, maybe bad organization id={}'.format(string,
                                                                                           organization_id)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                    'results': []
                })

        property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
            .filter(property__organization_id=request.query_params['organization_id'], cycle=cycle)

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
            'results': []
        }

        # Ids of propertyviews to look up in m2m
        prop_ids = [p.pk for p in property_views]
        joins = TaxLotProperty.objects.filter(property_view_id__in=prop_ids)

        # Get all ids of tax lots on these joins
        taxlot_view_ids = [j.taxlot_view_id for j in joins]

        # Get all tax lot views that are related
        taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle').filter(
            pk__in=taxlot_view_ids)

        # Map tax lot view id to tax lot view's state data, so we can reference these easily and save some queries.
        db_columns = Column.retrieve_db_fields()
        for lot in taxlot_views:
            # Each object in the response is built from the state data, with related data added on.
            l = model_to_dict(lot.state, exclude=['extra_data'])

            for extra_data_field, extra_data_value in lot.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                # Check if the extra data field is already a database field
                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

        taxlot_map = {}
        for taxlot_view in taxlot_views:
            l = model_to_dict(taxlot_view.state, exclude=['extra_data'])
            l['taxlot_state_id'] = taxlot_view.state.id

            # Add extra data fields right to this object.
            for extra_data_field, extra_data_value in taxlot_view.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                l[extra_data_field] = extra_data_value

            # Only return the requested rows. speeds up the json string time
            l = {key: value for key, value in l.items() if key in columns}

            taxlot_map[taxlot_view.pk] = l
            # Replace taxlot_view id with taxlot id
            taxlot_map[taxlot_view.pk]['id'] = taxlot_view.taxlot.id

        # A mapping of property view pk to a list of taxlot state info for a taxlot view
        join_map = {}
        for join in joins:
            join_dict = taxlot_map[join.taxlot_view_id].copy()
            join_dict.update({
                'primary': 'P' if join.primary else 'S',
                'taxlot_view_id': join.taxlot_view_id
            })
            try:
                join_map[join.property_view_id].append(join_dict)
            except KeyError:
                join_map[join.property_view_id] = [join_dict]

        for prop in property_views:
            # Each object in the response is built from the state data, with related data added on.
            p = model_to_dict(prop.state, exclude=['extra_data'])

            for extra_data_field, extra_data_value in prop.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                p[extra_data_field] = extra_data_value

            # Use property_id instead of default (state_id)
            p['id'] = prop.property_id

            p['property_state_id'] = prop.state.id
            p['property_view_id'] = prop.id

            p['campus'] = prop.property.campus

            # All the related tax lot states.
            p['related'] = join_map.get(prop.pk, [])

            response['results'].append(p)

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

    # @require_organization_id
    # @require_organization_membership
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

        return JsonResponse({'columns': columns})

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
                'message': 'property view with id {} does not exist'.format(pk)
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
        """Return history in reverse order."""
        history = []

        def record_dict(log):
            filename = None if not log.import_filename else path.basename(log.import_filename)
            if filename:
                # Attempt to remove NamedTemporaryFile suffix
                name, ext = path.splitext(filename)
                pattern = re.compile('(.*?)(_[a-zA-Z0-9]{7})$')
                match = pattern.match(name)
                if match:
                    filename = match.groups()[0] + ext
            return {
                'state': PropertyStateSerializer(log.state).data,
                'date_edited': convert_to_js_timestamp(log.created),
                'source': log.get_record_type_display(),
                'filename': filename,
                # 'changed_fields': json.loads(log.description) if log.record_type == AUDIT_USER_EDIT else None
            }

        log = PropertyAuditLog.objects.select_related('state', 'parent1', 'parent2').filter(
            state_id=property_view.state_id
        ).order_by('-id').first()
        master = {
            'state': PropertyStateSerializer(log.state).data,
            'date_edited': convert_to_js_timestamp(log.created),
        }

        # Traverse parents and add to history
        if log.name in ['Manual Match', 'System Match', 'Merge current state in migration']:
            done_searching = False
            while not done_searching:
                if (log.parent1_id is None and log.parent2_id is None) or log.name == 'Manual Edit':
                    done_searching = True
                elif log.name == 'Merge current state in migration':
                    record = record_dict(log.parent1)
                    history.append(record)
                    if log.parent1.name == 'Import Creation':
                        done_searching = True
                    else:
                        tree = log.parent1
                        log = tree
                else:
                    tree = None
                    if log.parent2:
                        if log.parent2.name in ['Import Creation', 'Manual Edit']:
                            record = record_dict(log.parent2)
                            history.append(record)
                        else:
                            tree = log.parent2
                    if log.parent1.name in ['Import Creation', 'Manual Edit']:
                        record = record_dict(log.parent1)
                        history.append(record)
                    else:
                        tree = log.parent1

                    if not tree:
                        done_searching = True
                    else:
                        log = tree
        elif log.name == 'Manual Edit':
            record = record_dict(log.parent1)
            history.append(record)
        elif log.name == 'Import Creation':
            record = record_dict(log)
            history.append(record)

        return history, master

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Get property details
        ---
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
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_property_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            result.update(PropertyViewSerializer(property_view).data)
            # remove PropertyView id from result
            result.pop('id')
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
        Update a property
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
                        new_state = new_property_state_serializer.save()
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
                    'results': []
                })

        taxlot_views_list = TaxLotView.objects.select_related('taxlot', 'state', 'cycle') \
            .filter(taxlot__organization_id=request.query_params['organization_id'], cycle=cycle)

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
            'results': []
        }

        # Ids of taxlotviews to look up in m2m
        lot_ids = [l.pk for l in taxlot_views]
        joins = TaxLotProperty.objects.filter(taxlot_view_id__in=lot_ids).select_related(
            'property_view')

        # Get all ids of properties on these joins
        property_view_ids = [j.property_view_id for j in joins]

        # Get all property views that are related
        property_views = PropertyView.objects.select_related('property', 'state', 'cycle').filter(
            pk__in=property_view_ids)

        db_columns = Column.retrieve_db_fields()

        # Map property view id to property view's state data, so we can reference these easily and
        # save some queries.
        property_map = {}
        for property_view in property_views:
            p = model_to_dict(property_view.state, exclude=['extra_data'])
            p['property_state_id'] = property_view.state.id
            p['campus'] = property_view.property.campus

            # Add extra data fields right to this object.
            for extra_data_field, extra_data_value in property_view.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                p[extra_data_field] = extra_data_value

            # Only return the requested rows. speeds up the json string time
            p = {key: value for key, value in p.items() if key in columns}

            property_map[property_view.pk] = p
            # Replace property_view id with property id
            property_map[property_view.pk]['id'] = property_view.property.id

        # A mapping of taxlot view pk to a list of property state info for a property view
        join_map = {}
        # Get whole taxlotstate table:
        tuplePropToJurisdictionTL = tuple(
            TaxLotProperty.objects.values_list('property_view_id',
                                               'taxlot_view__state__jurisdiction_tax_lot_id'))

        # create a mapping that defaults to an empty list
        propToJurisdictionTL = defaultdict(list)

        # populate the mapping
        for name, pth in tuplePropToJurisdictionTL:
            propToJurisdictionTL[name].append(pth)

        for join in joins:
            jurisdiction_tax_lot_ids = propToJurisdictionTL[join.property_view_id]

            # Filter out associated tax lots that are present but which do not have preferred
            none_in_jurisdiction_tax_lot_ids = None in jurisdiction_tax_lot_ids
            jurisdiction_tax_lot_ids = filter(lambda x: x is not None, jurisdiction_tax_lot_ids)

            if none_in_jurisdiction_tax_lot_ids:
                jurisdiction_tax_lot_ids.append('Missing')

            # jurisdiction_tax_lot_ids = [""]

            join_dict = property_map[join.property_view_id].copy()
            join_dict.update({
                'primary': 'P' if join.primary else 'S',
                'calculated_taxlot_ids': '; '.join(jurisdiction_tax_lot_ids)
            })
            try:
                join_map[join.taxlot_view_id].append(join_dict)
            except KeyError:
                join_map[join.taxlot_view_id] = [join_dict]

        for lot in taxlot_views:
            # Each object in the response is built from the state data, with related data added on.
            l = model_to_dict(lot.state, exclude=['extra_data'])

            for extra_data_field, extra_data_value in lot.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'

                # Check if the extra data field is already a database field
                while extra_data_field in db_columns:
                    extra_data_field += '_extra'

                # save to dictionary
                l[extra_data_field] = extra_data_value

            # Use taxlot_id instead of default (state_id)
            l['id'] = lot.taxlot_id

            l['taxlot_state_id'] = lot.state.id
            l['taxlot_view_id'] = lot.id

            # All the related property states.
            l['related'] = join_map.get(lot.pk, [])

            response['results'].append(l)

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

        return JsonResponse({'columns': columns})

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
        """Return history in reverse order."""
        history = []

        def record_dict(log):
            filename = None if not log.import_filename else path.basename(log.import_filename)
            if filename:
                # Attempt to remove NamedTemporaryFile suffix
                name, ext = path.splitext(filename)
                pattern = re.compile('(.*?)(_[a-zA-Z0-9]{7})$')
                match = pattern.match(name)
                if match:
                    filename = match.groups()[0] + ext
            return {
                'state': TaxLotStateSerializer(log.state).data,
                'date_edited': convert_to_js_timestamp(log.created),
                'source': log.get_record_type_display(),
                'filename': filename,
                # 'changed_fields': json.loads(log.description) if log.record_type == AUDIT_USER_EDIT else None
            }

        log = TaxLotAuditLog.objects.select_related('state', 'parent1', 'parent2').filter(
            state_id=taxlot_view.state_id
        ).order_by('-id').first()
        master = {
            'state': TaxLotStateSerializer(log.state).data,
            'date_edited': convert_to_js_timestamp(log.created),
        }

        # Traverse parents and add to history
        if log.name in ['Manual Match', 'System Match', 'Merge current state in migration']:
            done_searching = False
            while not done_searching:
                if (log.parent1_id is None and log.parent2_id is None) or log.name == 'Manual Edit':
                    done_searching = True
                elif log.name == 'Merge current state in migration':
                    record = record_dict(log.parent1)
                    history.append(record)
                    if log.parent1.name == 'Import Creation':
                        done_searching = True
                    else:
                        tree = log.parent1
                        log = tree
                else:
                    tree = None
                    if log.parent2:
                        if log.parent2.name in ['Import Creation', 'Manual Edit']:
                            record = record_dict(log.parent2)
                            history.append(record)
                        else:
                            tree = log.parent2
                    if log.parent1.name in ['Import Creation', 'Manual Edit']:
                        record = record_dict(log.parent1)
                        history.append(record)
                    else:
                        tree = log.parent1

                    if not tree:
                        done_searching = True
                    else:
                        log = tree
        elif log.name == 'Manual Edit':
            record = record_dict(log.parent1)
            history.append(record)
        elif log.name == 'Import Creation':
            record = record_dict(log)
            history.append(record)

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

        else:
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)


def get_changed_fields(old, new):
    """Return changed fields as json string"""
    changed_fields, changed_extra_data = diffupdate(old, new)
    if 'id' in changed_fields:
        changed_fields.remove('id')
    if 'pk' in changed_fields:
        changed_fields.remove('pk')
    if not (changed_fields or changed_extra_data):
        return None
    else:
        return json.dumps({
            'regular_fields': changed_fields,
            'extra_data_fields': changed_extra_data
        })


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


def update_result_with_master(result, master):
    result['changed_fields'] = master.get('changed_fields', None) if master else None
    result['date_edited'] = master.get('date_edited', None) if master else None
    result['source'] = master.get('source', None) if master else None
    result['filename'] = master.get('filename', None) if master else None
    return result
