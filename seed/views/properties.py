# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import csv
import re
from os import path

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.filtersets import PropertyViewFilterSet, PropertyStateFilterSet
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    AUDIT_USER_EDIT,
    Column,
    Cycle,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLotProperty,
    TaxLotView
)
from seed.models import Property as PropertyModel
from seed.serializers.pint import PintJSONEncoder
from seed.serializers.properties import (
    PropertySerializer,
    PropertyStateSerializer,
    PropertyViewAsStateSerializer,
    PropertyViewSerializer
)
from seed.serializers.taxlots import (
    TaxLotViewSerializer
)
from seed.utils.api import api_endpoint_class
from seed.utils.properties import (
    get_changed_fields,
    pair_unpair_property_taxlot,
    update_result_with_master
)
from seed.utils.time import convert_to_js_timestamp
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
                        if 'organization' in result['state']:
                            result['state'].pop('organization')
                        if 'import_file' in result['state']:
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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['POST'])
    def csv(self, request):
        """
        Download a csv of the data quality checks by the pk which is the cache_key

        Example Body:
            {
        	    "ids": [1,2,3],
	            "columns": ["tax_jurisdiction_tax_lot_id", "address_line_1", "property_view_id"]
            }
        ---
        parameter_strategy: replace
        parameters:
            - name: cycle
              description: cycle
              required: true
              paramType: query
            - name: ids
              description: list of ids to export
              required: true
              paramType: body
            - name: columns
              description: list of columns to export
              required: true
              paramType: body
            - name: filename
              description: name of the file to create
              required: false
              paramType: body


        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        columns = request.data.get('columns', None)
        if columns is None:
            # default the columns for now if no columns are passed
            columns = [
                "pm_property_id", "pm_parent_property_id", "tax_jurisdiction_tax_lot_id",
                "custom_id_1", "tax_custom_id_1", "city", "state", "postal_code",
                "tax_primary", "property_name", "campus", "gross_floor_area",
                "use_description", "energy_score", "site_eui", "property_notes",
                "property_type", "year_ending", "owner", "owner_email", "owner_telephone",
                "building_count", "year_built", "recent_sale_date", "conditioned_floor_area",
                "occupied_floor_area", "owner_address", "owner_city_state", "owner_postal_code",
                "home_energy_score_id", "generation_date", "release_date",
                "source_eui_weather_normalized", "site_eui_weather_normalized", "source_eui",
                "energy_alerts", "space_alerts", "building_certification", "number_properties",
                "block_number", "district", "BLDGS", "property_state_id", "taxlot_state_id",
                "property_view_id", "taxlot_view_id"
            ]
        # always export the labels
        columns += ['property_labels', 'taxlot_labels']

        ids = request.data.get('ids', None)
        if ids:
            property_views = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(property__organization_id=request.query_params['organization_id'],
                        cycle=cycle_pk,
                        id__in=ids).order_by('id')
        else:
            # return all the ids for the property
            property_views = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(property__organization_id=request.query_params['organization_id'],
                        cycle=cycle_pk).order_by('id')

        filename = request.data.get('filename', None)
        if not filename:
            filename = "ExportedData.csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)

        # get the data in a dict which includes the related data
        data = TaxLotProperty.get_related(property_views, columns)

        # note that the labels are in the property_labels column and are returned by the
        # TaxLotProperty.get_related method

        # header
        writer.writerow(columns)

        # iterate over the results to preserve column order and write row
        for datum in data:
            row = []
            for column in columns:
                if column.startswith('tax_') or column == 'jurisdiction_tax_lot_id':
                    if datum.get('related') and len(datum['related']) > 0:
                        # Looks like related returns a list. Is this as expected?
                        row.append(datum['related'][0].get(re.sub(r'^tax_', '', column), None))
                    else:
                        row.append(None)
                else:
                    row.append(datum.get(column, None))

            writer.writerow(row)

        return response
