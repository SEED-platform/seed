# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

# Imports from Standard Library
import re
from collections import defaultdict
from os import path

# Imports from Django
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils.timezone import make_naive
from rest_framework import status
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

# Local Imports
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
from seed.utils.time import convert_to_js_timestamp

# Constants
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
            'cycle_id': cycle.id,
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

            # fix specific time stamps - total hack right now. Need to reconcile with
            # /data_importer/views.py and /seed/views/properties.py
            if join_dict.get('recent_sale_date'):
                join_dict['recent_sale_date'] = make_naive(join_dict['recent_sale_date']).strftime(
                    '%Y-%m-%dT%H:%M:%S')

            if join_dict.get('release_date'):
                join_dict['release_date'] = make_naive(join_dict['release_date']).strftime(
                    '%Y-%m-%dT%H:%M:%S')

            if join_dict.get('generation_date'):
                join_dict['generation_date'] = make_naive(join_dict['generation_date']).strftime(
                    '%Y-%m-%dT%H:%M:%S')

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
                        elif log.parent2.name == 'System Match' and log.parent2.parent1.name == 'Import Creation' and \
                                log.parent2.parent2.name == 'Import Creation':
                            # Handle case where an import file matches within itself, and proceeds to match with
                            # existing records
                            record = record_dict(log.parent2.parent2)
                            history.append(record)
                            record = record_dict(log.parent2.parent1)
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
