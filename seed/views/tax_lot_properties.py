# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""

import csv
import datetime
from collections import OrderedDict

from django.http import JsonResponse, HttpResponse
from quantityfield import ureg
from rest_framework.decorators import list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    PropertyView,
    TaxLotProperty,
    TaxLotView,
    ColumnListSetting,
)
from seed.serializers.tax_lot_properties import (
    TaxLotPropertySerializer
)
from seed.utils.api import api_endpoint_class

INVENTORY_MODELS = {'properties': PropertyView, 'taxlots': TaxLotView}


class TaxLotPropertyViewSet(GenericViewSet):
    """
    The TaxLotProperty field is used to return the properties and tax lots from the join table.
    This method presently only works with the CSV, but should eventually be extended to be the
    viewset for any tax lot / property join API call.
    """
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotPropertySerializer

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['POST'])
    def export(self, request):
        """
        Download a csv of the TaxLot and Properties

        .. code-block::

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
            - name: inventory_type
              description: properties or taxlots (as defined by the inventory list page)
              required: true
              paramType: query
            - name: ids
              description: list of property/taxlot ids to export (not property/taxlot views)
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
            - name: profile_id
              description: Either an id of a list settings profile, or undefined
              paramType: body
        """
        cycle_pk = request.query_params.get('cycle_id', None)
        if not cycle_pk:
            return JsonResponse(
                {'status': 'error', 'message': 'Must pass in cycle_id as query parameter'})
        org_id = request.query_params['organization_id']
        if 'profile_id' not in request.data:
            profile_id = None
        else:
            if request.data['profile_id'] == 'None' or request.data['profile_id'] == '':
                profile_id = None
            else:
                profile_id = request.data['profile_id']

        # get the class to operate on and the relationships
        view_klass_str = request.query_params.get('inventory_type', 'properties')
        view_klass = INVENTORY_MODELS[view_klass_str]

        # Set the first column to be the ID
        column_name_mappings = OrderedDict([('id', 'ID')])
        column_ids, add_column_name_mappings, columns_from_database = ColumnListSetting.return_columns(
            org_id,
            profile_id,
            view_klass_str)
        column_name_mappings.update(add_column_name_mappings)
        select_related = ['state', 'cycle']
        ids = request.data.get('ids', [])
        filter_str = {'cycle': cycle_pk}
        if hasattr(view_klass, 'property'):
            select_related.append('property')
            prefetch_related = ['labels']
            filter_str = {'property__organization_id': org_id}
            if ids:
                filter_str['property__id__in'] = ids
            # always export the labels
            column_name_mappings['property_labels'] = 'Property Labels'

        elif hasattr(view_klass, 'taxlot'):
            select_related.append('taxlot')
            prefetch_related = ['labels']
            filter_str = {'taxlot__organization_id': org_id}
            if ids:
                filter_str['taxlot__id__in'] = ids
            # always export the labels
            column_name_mappings['taxlot_labels'] = 'Tax Lot Labels'

        model_views = view_klass.objects.select_related(*select_related).prefetch_related(*prefetch_related).filter(**filter_str).order_by('id')

        # get the data in a dict which includes the related data
        data = TaxLotProperty.get_related(model_views, column_ids, columns_from_database)

        # add labels
        for i, record in enumerate(model_views):
            label_string = []
            if hasattr(record, 'property'):
                for label in list(record.labels.all().order_by('name')):
                    label_string.append(label.name)
                data[i]['property_labels'] = ','.join(label_string)

            elif hasattr(record, 'taxlot'):
                for label in list(record.labels.all().order_by('name')):
                    label_string.append(label.name)
                data[i]['taxlot_labels'] = ','.join(label_string)

        # force the data into the same order as the IDs
        if ids:
            order_dict = {obj_id: index for index, obj_id in enumerate(ids)}
            data.sort(key=lambda x: order_dict[x['id']])  # x is the property/taxlot object

        export_type = request.data.get('export_type', 'csv')

        filename = request.data.get('filename', f"ExportedData.{export_type}")

        if export_type == "csv":
            return self._csv_response(filename, data, column_name_mappings)
        elif export_type == "geojson":
            return self._json_response(filename, data, column_name_mappings)

    def _csv_response(self, filename, data, column_name_mappings):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)

        # check the first item in the header and make sure that it isn't ID (it can be id, or iD).
        # excel doesn't like the first item to be ID in a CSV
        header = list(column_name_mappings.values())
        if header[0] == 'ID':
            header[0] = 'id'
        writer.writerow(header)

        # iterate over the results to preserve column order and write row.
        for datum in data:
            row = []
            for column in column_name_mappings:
                row_result = datum.get(column, None)

                # Try grabbing the value out of the related field if not found yet.
                if row_result is None and datum.get('related'):
                    row_result = datum['related'][0].get(column, None)

                # Convert quantities (this is typically handled in the JSON Encoder, but that isn't here).
                if isinstance(row_result, ureg.Quantity):
                    row_result = row_result.magnitude
                elif isinstance(row_result, datetime.datetime):
                    row_result = row_result.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(row_result, datetime.date):
                    row_result = row_result.strftime("%Y-%m-%d")
                row.append(row_result)

            writer.writerow(row)

        return response

    def _json_response(self, filename, data, column_name_mappings):
        polygon_fields = ["bounding_box", "centroid", "property_footprint", "taxlot_footprint", "long_lat"]
        features = []

        # extract related records
        related_records = self._extract_related(data)

        # append related_records to data
        complete_data = data + related_records

        for datum in complete_data:
            feature = {
                "type": "Feature",
                "properties": {}
            }

            for key, value in datum.items():
                if value is None:
                    continue

                if isinstance(value, ureg.Quantity):
                    value = value.magnitude
                elif isinstance(value, datetime.datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(value, datetime.date):
                    value = value.strftime("%Y-%m-%d")

                if value and any(k in key for k in polygon_fields):
                    """
                    If object is a polygon and is populated, add the 'geometry'
                    key-value-pair in the appropriate GeoJSON format.
                    When the first geometry is added, the correct format is
                    established. When/If a second geometry is added, this is
                    appended alongside the previous geometry.
                    """
                    individual_geometry = {}

                    print("VALUE:")
                    print(value)

                    # long_lat
                    if key == 'long_lat':
                        coordinates = self._serialized_point(value)
                        # point
                        individual_geometry = {
                            "coordinates": coordinates,
                            "type": "Point"
                        }
                    else:
                        # polygons
                        coordinates = self._serialized_coordinates(value)
                        individual_geometry = {
                            "coordinates": [coordinates],
                            "type": "Polygon"
                        }

                    if feature.get("geometry", None) is None:
                        feature["geometry"] = {
                            "type": "GeometryCollection",
                            "geometries": [individual_geometry]
                        }
                    else:
                        feature["geometry"]["geometries"].append(individual_geometry)
                else:
                    """
                    Non-polygon data
                    """
                    display_key = column_name_mappings.get(key, key)
                    feature["properties"][display_key] = value

                    # # store point geometry in case you need it
                    # if display_key == "Longitude":
                    #     point_geometry[0] = value
                    # if display_key == "Latitude":
                    #     point_geometry[1] = value

            """
            Before appending feature, ensure that if there is no geometry recorded.
            Note that the GeoJson will not render if no lat/lng
            """

            # add style information
            if feature["properties"].get("property_state_id") is not None:
                feature["properties"]["stroke"] = "#185189"  # buildings color
            elif feature["properties"].get("taxlot_state_id") is not None:
                feature["properties"]["stroke"] = "#10A0A0"  # buildings color
            feature["properties"]["marker-color"] = "#E74C3C"
            # feature["properties"]["stroke-width"] = 3
            feature["properties"]["fill-opacity"] = 0

            # append feature
            features.append(feature)

            response_dict = {
                "type": "FeatureCollection",
                "crs": {
                    "type": "EPSG",
                    "properties": {"code": 4326}
                },
                "features": features
            }

        response = JsonResponse(response_dict)
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        return response

    def _serialized_coordinates(self, polygon_wkt):
        string_coord_pairs = polygon_wkt.lstrip('POLYGON (').rstrip(')').split(', ')

        coordinates = []
        for coord_pair in string_coord_pairs:
            float_coords = [float(coord) for coord in coord_pair.split(' ')]
            coordinates.append(float_coords)

        return coordinates

    def _serialized_point(self, point_wkt):
        string_coords = point_wkt.lstrip('POINT (').rstrip(')').split(', ')

        coordinates = []
        for coord in string_coords[0].split(' '):
            coordinates.append(float(coord))

        return coordinates

    def _extract_related(self, data):
        # extract all related records into a separate array
        related = []

        # figure out if we are dealing with properties or taxlots
        if data[0].get("property_state_id", None) is not None:
            is_property = True
        elif data[0].get("taxlot_state_id", None) is not None:
            is_property = False

        for datum in data:
            if datum.get("related", None) is not None:
                for record in datum["related"]:
                    related.append(record)

        # make array unique
        if is_property:

            unique = [dict(p) for p in set(tuple(i.items())
                                           for i in related)]

        else:
            unique = [dict(p) for p in set(tuple(i.items())
                                           for i in related)]

        return unique
