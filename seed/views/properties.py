# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import itertools
import json

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import list_route, detail_route
from django.http import JsonResponse

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

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True


def unique(lol):
    """Calculate unique elements in a list of lists."""
    return sorted(set(itertools.chain.from_iterable(lol)))


class PropertyViewSet(GenericViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = PropertySerializer

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
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = request.query_params.get('organization_id', None)
        if not org_id:
            return JsonResponse({'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)

        cycle_id = request.query_params.get('cycle')
        if cycle_id:
            cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
        else:
            cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
            if cycle:
                cycle = cycle.first()
            else:
                return JsonResponse({'status': 'error', 'message': 'Could not locate cycle'},
                                    status=status.HTTP_400_BAD_REQUEST)

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
        taxlot_views = TaxLotView.objects.select_related('taxlot', 'state', 'cycle').filter(pk__in=taxlot_view_ids)

        # Map tax lot view id to tax lot view's state data, so we can reference these easily and save some queries.
        taxlot_map = {}
        for taxlot_view in taxlot_views:
            taxlot_state_data = model_to_dict(taxlot_view.state, exclude=['extra_data'])
            taxlot_state_data['taxlot_state_id'] = taxlot_view.state.id

            # Add extra data fields right to this object.
            for extra_data_field, extra_data_value in taxlot_view.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'
                while extra_data_field in taxlot_state_data:
                    extra_data_field += '_extra'
                taxlot_state_data[extra_data_field] = extra_data_value
            taxlot_map[taxlot_view.pk] = taxlot_state_data
            # Replace taxlot_view id with taxlot id
            taxlot_map[taxlot_view.pk]['id'] = taxlot_view.taxlot.id

        # A mapping of property view pk to a list of taxlot state info for a taxlot view
        join_map = {}
        for join in joins:
            join_dict = taxlot_map[join.taxlot_view_id].copy()
            join_dict.update({
                'primary': 'P' if join.primary else 'S'
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
                while extra_data_field in p:
                    extra_data_field += '_extra'

                p[extra_data_field] = extra_data_value

            # Use property_id instead of default (state_id)
            p['id'] = prop.property_id

            p['property_state_id'] = prop.state.id

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
    @list_route(methods=['GET'])
    def columns(self, request):
        """
        List all property columns
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """

        """TODO: These property columns should be merged with
        constants.py:ASSESSOR_FIELDS"""

        columns = [
            {
                'name': 'pm_property_id',
                'displayName': 'PM Property ID',
                'pinnedLeft': True,
                'type': 'number',
                'related': False
            }, {
                'name': 'jurisdiction_property_id',
                'displayName': 'Property / Building ID',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'jurisdiction_tax_lot_id',
                'displayName': 'Jurisdiction Tax Lot ID',
                'type': 'numberStr',
                'related': True
            }, {
                'name': 'primary',
                'displayName': 'Primary/Secondary',
                'related': True
            }, {
                # INCOMPLETE, FIELD DOESN'T EXIST
                'name': 'associated_tax_lot_ids',
                'displayName': 'Associated TaxLot IDs',
                'type': 'number',
                'related': False
            }, {
                'name': 'lot_number',
                'displayName': 'Associated Building Tax Lot ID',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'address_line_1',
                'displayName': 'Address Line 1 (Property)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'city',
                'displayName': 'City (Property)',
                'related': False
            }, {
                'name': 'property_name',
                'displayName': 'Property Name',
                'related': False
            }, {
                'name': 'campus',
                'displayName': 'Campus',
                'type': 'boolean',
                'related': False
            }, {
                # INCOMPLETE, FIELD DOESN'T EXIST
                'name': 'pm_parent_property_id',
                'displayName': 'PM Parent Property ID',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'gross_floor_area',
                'displayName': 'Property Floor Area',
                'type': 'number',
                'related': False
            }, {
                'name': 'use_description',
                'displayName': 'Property Type',
                'related': False
            }, {
                'name': 'energy_score',
                'displayName': 'ENERGY STAR Score',
                'type': 'number',
                'related': False
            }, {
                'name': 'site_eui',
                'displayName': 'Site EUI (kBtu/sf-yr)',
                'type': 'number',
                'related': False
            }, {
                'name': 'property_notes',
                'displayName': 'Property Notes',
                'related': False
            }, {
                'name': 'property_type',
                'displayName': 'Property Type',
                'related': False
            }, {
                'name': 'year_ending',
                'displayName': 'Benchmarking year',
                'related': False
            }, {
                'name': 'owner',
                'displayName': 'Owner',
                'related': False
            }, {
                'name': 'owner_email',
                'displayName': 'Owner Email',
                'related': False
            }, {
                'name': 'owner_telephone',
                'displayName': 'Owner Telephone',
                'related': False
            }, {
                'name': 'address_line_2',
                'displayName': 'Address Line 2 (Property)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'state',
                'displayName': 'State (Property)',
                'related': False
            }, {
                'name': 'postal_code',
                'displayName': 'Postal Code (Property)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'building_count',
                'displayName': 'Number of Buildings',
                'type': 'number',
                'related': False
            }, {
                'name': 'year_built',
                'displayName': 'Year Built',
                'type': 'number',
                'related': False
            }, {
                'name': 'recent_sale_date',
                'displayName': 'Property Sale Date',
                'related': False
            }, {
                'name': 'conditioned_floor_area',
                'displayName': 'Property Conditioned Floor Area',
                'type': 'number',
                'related': False
            }, {
                'name': 'occupied_floor_area',
                'displayName': 'Property Occupied Floor Area',
                'type': 'number',
                'related': False
            }, {
                'name': 'owner_address',
                'displayName': 'Owner Address',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'owner_city_state',
                'displayName': 'Owner City/State',
                'related': False
            }, {
                'name': 'owner_postal_code',
                'displayName': 'Owner Postal Code',
                'type': 'number',
                'related': False
            }, {
                'name': 'home_energy_score_id',
                'displayName': 'Home Energy Score ID',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'generation_date',
                'displayName': 'PM Generation Date',
                'related': False
            }, {
                'name': 'release_date',
                'displayName': 'PM Release Date',
                'related': False
            }, {
                'name': 'source_eui_weather_normalized',
                'displayName': 'Source EUI Weather Normalized',
                'type': 'number',
                'related': False
            }, {
                'name': 'site_eui_weather_normalized',
                'displayName': 'Site EUI Weather Normalized',
                'type': 'number',
                'related': False
            }, {
                'name': 'source_eui',
                'displayName': 'Source EUI',
                'type': 'number',
                'related': False
            }, {
                'name': 'energy_alerts',
                'displayName': 'Energy Alerts',
                'related': False
            }, {
                'name': 'space_alerts',
                'displayName': 'Space Alerts',
                'related': False
            }, {
                'name': 'building_certification',
                'displayName': 'Building Certification',
                'related': False
            }, {
                # Modified field name
                'name': 'tax_address_line_1',
                'displayName': 'Address Line 1 (Tax Lot)',
                'type': 'numberStr',
                'related': True
            }, {
                # Modified field name
                'name': 'tax_address_line_2',
                'displayName': 'Address Line 2 (Tax Lot)',
                'type': 'numberStr',
                'related': True
            }, {
                # Modified field name
                'name': 'tax_city',
                'displayName': 'City (Tax Lot)',
                'related': True
            }, {
                # Modified field name
                'name': 'tax_state',
                'displayName': 'State (Tax Lot)',
                'related': True
            }, {
                # Modified field name
                'name': 'tax_postal_code',
                'displayName': 'Postal Code (Tax Lot)',
                'type': 'number',
                'related': True
            }, {
                'name': 'number_properties',
                'displayName': 'Number Properties',
                'type': 'number',
                'related': True
            }, {
                'name': 'block_number',
                'displayName': 'Block Number',
                'type': 'number',
                'related': True
            }, {
                'name': 'district',
                'displayName': 'District',
                'related': True
            }
        ]

        extra_data_columns = Column.objects.filter(
            organization_id=request.query_params['organization_id'],
            is_extra_data=True
        )

        for c in extra_data_columns:
            name = c.column_name
            if name == 'id':
                name += '_extra'
            while any(col['name'] == name for col in columns):
                name += '_extra'

            columns.append({
                'name': name,
                # '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source])
                'displayName': c.column_name,
                # Set related = True for extra data to ensure that it always aggregates
                'related': True,
                # 'related': c.extra_data_source == Column.SOURCE_TAXLOT or c.table_name == 'TaxLotState',
                'extraData': True
            })

        return JsonResponse({'columns': columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['DELETE'])
    def batch_delete(self, request):
        """
        List all property columns
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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_property_view(pk, cycle_pk)
        return JsonResponse(result)

    def _get_taxlots(self, pk):
        lot_view_pks = TaxLotProperty.objects.filter(property_view_id=pk).values_list('taxlot_view_id', flat=True)
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
        current = None
        audit_logs = PropertyAuditLog.objects.select_related('state').filter(
            view=property_view
        ).order_by('-created', '-state_id')
        for log in audit_logs:
            changed_fields = json.loads(log.description) \
                if log.record_type == AUDIT_USER_EDIT else None
            record = {
                'state': PropertyStateSerializer(log.state).data,
                'date_edited': log.created.ctime(),
                'source': log.get_record_type_display(),
                'filename': log.import_filename,
                'changed_fields': changed_fields
            }
            if log.state_id == property_view.state_id:
                current = record
            else:
                history.append(record)
        return history, current

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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_property_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            result.update(PropertyViewSerializer(property_view).data)
            # remove PropertyView id from result
            result.pop('id')
            result['state'] = PropertyStateSerializer(property_view.state).data
            result['taxlots'] = self._get_taxlots(property_view.pk)
            result['history'], current = self.get_history(property_view)
            result = update_result_with_current(result, current)
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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        data = request.data
        result = self._get_property_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            property_state_data = PropertyStateSerializer(property_view.state).data
            new_property_state_data = data['state']

            changed = True
            if new_property_state_data == property_state_data:
                changed = False
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
                property_state_data.update(new_property_state_data)
                property_state_data.pop('id')

                new_property_state_serializer = PropertyStateSerializer(
                    data=property_state_data
                )

                if new_property_state_serializer.is_valid():
                    new_state = new_property_state_serializer.save()
                    property_view.update_state(
                        new_state, description=changed_fields
                    )
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
        else:
            status_code = status.HTTP_404_NOT_FOUND
        return JsonResponse(result, status=status_code)


class TaxLotViewSet(GenericViewSet):
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotSerializer

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
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = request.query_params.get('organization_id', None)
        if not org_id:
            return JsonResponse({'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)

        cycle_id = request.query_params.get('cycle')
        if cycle_id:
            cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
        else:
            cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
            cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
            if cycle:
                cycle = cycle.first()
            else:
                return JsonResponse({'status': 'error', 'message': 'Could not locate cycle'},
                                    status=status.HTTP_400_BAD_REQUEST)

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
        joins = TaxLotProperty.objects.filter(taxlot_view_id__in=lot_ids)

        # Get all ids of properties on these joins
        property_view_ids = [j.property_view_id for j in joins]

        # Get all property views that are related
        property_views = PropertyView.objects.select_related('property', 'state', 'cycle').filter(pk__in=property_view_ids)

        # Map property view id to property view's state data, so we can reference these easily and save some queries.
        property_map = {}
        for property_view in property_views:
            property_data = model_to_dict(property_view.state, exclude=['extra_data'])
            property_data['property_state_id'] = property_view.state.id
            property_data['campus'] = property_view.property.campus

            # Add extra data fields right to this object.
            for extra_data_field, extra_data_value in property_view.state.extra_data.items():
                if extra_data_field == 'id':
                    extra_data_field += '_extra'
                while extra_data_field in property_data:
                    extra_data_field += '_extra'
                property_data[extra_data_field] = extra_data_value
            property_map[property_view.pk] = property_data
            # Replace property_view id with property id
            property_map[property_view.pk]['id'] = property_view.property.id

        # A mapping of taxlot view pk to a list of property state info for a property view
        join_map = {}
        for join in joins:

            # Find all the taxlot ids that this property relates to
            related_taxlot_view_ids = TaxLotProperty.objects.filter(property_view_id=join.property_view_id) \
                .values_list('taxlot_view_id', flat=True)
            state_ids = TaxLotView.objects.filter(pk__in=related_taxlot_view_ids).values_list('state_id', flat=True)

            jurisdiction_tax_lot_ids = TaxLotState.objects.filter(pk__in=state_ids) \
                .values_list('jurisdiction_tax_lot_id', flat=True)

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
                while extra_data_field in l:
                    extra_data_field += '_extra'
                l[extra_data_field] = extra_data_value

            # Use taxlot_id instead of default (state_id)
            l['id'] = lot.taxlot_id

            l['taxlot_state_id'] = lot.state.id

            # All the related property states.
            l['related'] = join_map.get(lot.pk, [])

            response['results'].append(l)

        return JsonResponse(response)

    # @require_organization_id
    # @require_organization_membership
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def columns(self, request):
        """
        List all property columns
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """

        # TODO: Merge this with other schemas. Check https://github.com/SEED-platform/seed/blob/d2bfe96e7503f670300448d5967a2bd6d5863634/seed/lib/mcm/data/SEED/seed.py and  https://github.com/SEED-platform/seed/blob/41c104cd105161c949e9cb379aac946ea9202c74/seed/lib/mappings/mapping_data.py  # noqa
        columns = [
            {
                'name': 'jurisdiction_tax_lot_id',
                'displayName': 'Jurisdiction Tax Lot ID',
                'pinnedLeft': True,
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'primary',
                'displayName': 'Primary/Secondary',
                'related': True
            }, {
                # INCOMPLETE, FIELD DOESN'T EXIST
                'name': 'primary_tax_lot_id',
                'displayName': 'Primary Tax Lot ID',
                'type': 'number',
                'related': False
            }, {
                # FIELD DOESN'T EXIST
                'name': 'calculated_taxlot_ids',
                'displayName': 'Associated TaxLot IDs',
                'type': 'numberStr',
                'related': True
            }, {
                # INCOMPLETE, FIELD DOESN'T EXIST
                'name': 'associated_building_tax_lot_id',
                'displayName': 'Associated Building Tax Lot ID',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'address_line_1',
                'displayName': 'Address Line 1 (Tax Lot)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'address_line_2',
                'displayName': 'Address Line 2 (Tax Lot)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'city',
                'displayName': 'City (Tax Lot)',
                'related': False
            }, {
                # Modified field name
                'name': 'property_address_line_1',
                'displayName': 'Address Line 1 (Property)',
                'type': 'numberStr',
                'related': True
            }, {
                # Modified field name
                'name': 'property_city',
                'displayName': 'City (Property)',
                'related': True
            }, {
                'name': 'property_name',
                'displayName': 'Property Name',
                'related': True
            }, {
                'name': 'jurisdiction_property_id',
                'displayName': 'Property / Building ID',
                'type': 'numberStr',
                'related': True
            }, {
                'name': 'pm_property_id',
                'displayName': 'PM Property ID',
                'type': 'number',
                'related': True
            }, {
                'name': 'campus',
                'displayName': 'Campus',
                'type': 'boolean',
                'related': True
            }, {
                # INCOMPLETE, FIELD DOESN'T EXIST
                'name': 'pm_parent_property_id',
                'displayName': 'PM Parent Property ID',
                'type': 'numberStr',
                'related': True
            }, {
                'name': 'gross_floor_area',
                'displayName': 'Property Floor Area',
                'type': 'number',
                'related': True
            }, {
                'name': 'use_description',
                'displayName': 'Property Type',
                'related': True
            }, {
                'name': 'energy_score',
                'displayName': 'ENERGY STAR Score',
                'type': 'number',
                'related': True
            }, {
                'name': 'site_eui',
                'displayName': 'Site EUI (kBtu/sf-yr)',
                'type': 'number',
                'related': True
            }, {
                'name': 'property_notes',
                'displayName': 'Property Notes',
                'related': True
            }, {
                'name': 'year_ending',
                'displayName': 'Benchmarking year',
                'related': True
            }, {
                'name': 'owner',
                'displayName': 'Owner',
                'related': True
            }, {
                'name': 'owner_email',
                'displayName': 'Owner Email',
                'related': True
            }, {
                'name': 'owner_telephone',
                'displayName': 'Owner Telephone',
                'related': True
            }, {
                # Modified field name
                'name': 'property_address_line_2',
                'displayName': 'Address Line 2 (Property)',
                'type': 'numberStr',
                'related': True
            }, {
                # Modified field name
                'name': 'property_state',
                'displayName': 'State (Property)',
                'related': True
            }, {
                # Modified field name
                'name': 'property_postal_code',
                'displayName': 'Postal Code (Property)',
                'type': 'number',
                'related': True
            }, {
                'name': 'building_count',
                'displayName': 'Number of Buildings',
                'type': 'number',
                'related': True
            }, {
                'name': 'year_built',
                'displayName': 'Year Built',
                'type': 'number',
                'related': True
            }, {
                'name': 'recent_sale_date',
                'displayName': 'Property Sale Date',
                'related': True
            }, {
                'name': 'conditioned_floor_area',
                'displayName': 'Property Conditioned Floor Area',
                'type': 'number',
                'related': True
            }, {
                'name': 'occupied_floor_area',
                'displayName': 'Property Occupied Floor Area',
                'type': 'number',
                'related': True
            }, {
                'name': 'owner_address',
                'displayName': 'Owner Address',
                'type': 'numberStr',
                'related': True
            }, {
                'name': 'owner_city_state',
                'displayName': 'Owner City/State',
                'related': True
            }, {
                'name': 'owner_postal_code',
                'displayName': 'Owner Postal Code',
                'type': 'number',
                'related': True
            }, {
                'name': 'home_energy_score_id',
                'displayName': 'Home Energy Score ID',
                'type': 'numberStr',
                'related': True
            }, {
                'name': 'generation_date',
                'displayName': 'PM Generation Date',
                'related': True
            }, {
                'name': 'release_date',
                'displayName': 'PM Release Date',
                'related': True
            }, {
                'name': 'source_eui_weather_normalized',
                'displayName': 'Source EUI Weather Normalized',
                'type': 'number',
                'related': True
            }, {
                'name': 'site_eui_weather_normalized',
                'displayName': 'Site EUI Weather Normalized',
                'type': 'number',
                'related': True
            }, {
                'name': 'source_eui',
                'displayName': 'Source EUI',
                'type': 'number',
                'related': True
            }, {
                'name': 'energy_alerts',
                'displayName': 'Energy Alerts',
                'related': True
            }, {
                'name': 'space_alerts',
                'displayName': 'Space Alerts',
                'related': True
            }, {
                'name': 'building_certification',
                'displayName': 'Building Certification',
                'related': True
            }, {
                'name': 'state',
                'displayName': 'State (Tax Lot)',
                'related': False
            }, {
                'name': 'postal_code',
                'displayName': 'Postal Code (Tax Lot)',
                'type': 'numberStr',
                'related': False
            }, {
                'name': 'number_properties',
                'displayName': 'Number Properties',
                'type': 'number',
                'related': False
            }, {
                'name': 'block_number',
                'displayName': 'Block Number',
                'related': False
            }, {
                'name': 'district',
                'displayName': 'District',
                'related': False
            }, {
                'name': 'lot_number',
                'displayName': 'Associated Tax Lot ID',
                'related': True
            }
        ]

        extra_data_columns = Column.objects.filter(
            organization_id=request.GET['organization_id'],
            is_extra_data=True
        )

        for c in extra_data_columns:
            name = c.column_name
            if name == 'id':
                name += '_extra'
            while any(col['name'] == name for col in columns):
                name += '_extra'

            columns.append({
                'name': name,
                'displayName': c.column_name,  # '%s (%s)' % (c.column_name, Column.SOURCE_CHOICES_MAP[c.extra_data_source])
                # Set related = True for extra data to ensure that it always aggregates
                'related': True,
                # 'related': c.extra_data_source == Column.SOURCE_PROPERTY or c.table_name == 'PropertyState',
                'extraData': True
            })

        return JsonResponse({'columns': columns})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['DELETE'])
    def batch_delete(self, request):
        """
        List all property columns
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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_taxlot_view(pk, cycle_pk)
        return JsonResponse(result)

    def get_history(self, taxlot_view):
        """Return history in reverse order."""
        history = []
        current = None
        audit_logs = TaxLotAuditLog.objects.select_related('state').filter(
            view=taxlot_view
        ).order_by('-created', '-state_id')
        for log in audit_logs:
            changed_fields = json.loads(log.description) \
                if log.record_type == AUDIT_USER_EDIT else None
            record = {
                'state': TaxLotStateSerializer(log.state).data,
                'date_edited': log.created.ctime(),
                'source': log.get_record_type_display(),
                'filename': log.import_filename,
                'changed_fields': changed_fields
            }
            if log.state_id == taxlot_view.state_id:
                current = record
            else:
                history.append(record)
        return history, current

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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_taxlot_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            taxlot_view = result.pop('taxlot_view')
            result.update(TaxLotViewSerializer(taxlot_view).data)
            # remove TaxLotView id from result
            result.pop('id')
            result['state'] = TaxLotStateSerializer(taxlot_view.state).data
            result['properties'] = self._get_properties(taxlot_view.pk)
            result['history'], current = self.get_history(taxlot_view)
            result = update_result_with_current(result, current)
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
            return JsonResponse({'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        result = self._get_taxlot_view(pk, cycle_pk)
        if result.get('status', None) != 'error':
            taxlot_view = result.pop('taxlot_view')
            taxlot_state_data = TaxLotStateSerializer(taxlot_view.state).data
            new_taxlot_state_data = data['state']

            changed = True
            if new_taxlot_state_data == taxlot_state_data:
                changed = False
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
                taxlot_state_data.update(new_taxlot_state_data)
                taxlot_state_data.pop('id')

                new_taxlot_state_serializer = TaxLotStateSerializer(
                    data=taxlot_state_data
                )

                if new_taxlot_state_serializer.is_valid():
                    new_state = new_taxlot_state_serializer.save()
                    taxlot_view.update_state(
                        new_state, description=changed_fields
                    )
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


def update_result_with_current(result, cur):
    result['changed_fields'] = cur.get('changed_fields', None) if cur else None
    result['date_edited'] = cur.get('date_edited', None) if cur else None
    result['source'] = cur.get('source', None) if cur else None
    result['filename'] = cur.get('filename', None) if cur else None
    return result
