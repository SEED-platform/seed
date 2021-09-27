# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""
import csv
import datetime
import io
from collections import OrderedDict

import xlsxwriter
from django.http import JsonResponse, HttpResponse

from drf_yasg.utils import swagger_auto_schema

from quantityfield.units import ureg
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    PropertyView,
    TaxLotProperty,
    TaxLotView,
    ColumnListProfile,
)
from seed.models.meters import (
    Meter,
    MeterReading
)
from seed.models.property_measures import (
    PropertyMeasure
)
from seed.models.scenarios import (
    Scenario
)
from seed.serializers.tax_lot_properties import (
    TaxLotPropertySerializer
)
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

INVENTORY_MODELS = {'properties': PropertyView, 'taxlots': TaxLotView}


class TaxLotPropertyViewSet(GenericViewSet, OrgMixin):
    """
    The TaxLotProperty field is used to return the properties and tax lots from the join table.
    This method presently only works with the CSV, but should eventually be extended to be the
    viewset for any tax lot / property join API call.
    """
    renderer_classes = (JSONRenderer,)
    serializer_class = TaxLotPropertySerializer

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_string_field(
                "inventory_type",
                False,
                "Either 'taxlots' or 'properties' and defaults to 'properties'."),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'ids': ['integer'],
                'filename': 'string',
                'export_type': 'string',
                'profile_id': 'integer'
            },
            description='- ids: (View) IDs for records to be exported\n'
                        '- filename: desired filename including extension (defaulting to \'ExportedData.{export_type}\')\n'
                        '- export_types: \'csv\', \'geojson\', \'xlsx\' (defaulting to \'csv\')\n'
                        '- profile_id: Column List Profile ID to use for customizing fields included in export'
        ),
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['POST'])
    def export(self, request):
        """
        Download a collection of the TaxLot and Properties in multiple formats.
        """
        org_id = self.get_organization(request)
        profile_id = None
        column_profile = None
        if 'profile_id' in request.data and str(request.data['profile_id']) not in ['None', '']:
            profile_id = request.data['profile_id']
            column_profile = ColumnListProfile.objects.get(id=profile_id)

        # get the class to operate on and the relationships
        view_klass_str = request.query_params.get('inventory_type', 'properties')
        view_klass = INVENTORY_MODELS[view_klass_str]

        # Set the first column to be the ID
        column_name_mappings = OrderedDict([('id', 'ID')])
        column_ids, add_column_name_mappings, columns_from_database = ColumnListProfile.return_columns(
            org_id,
            profile_id,
            view_klass_str)
        column_name_mappings.update(add_column_name_mappings)

        select_related = ['state', 'cycle']
        prefetch_related = ['labels']
        ids = request.data.get('ids', [])
        filter_str = {}
        if ids:
            filter_str['id__in'] = ids
        if hasattr(view_klass, 'property'):
            select_related.append('property')
            filter_str['property__organization_id'] = org_id
            # always export the labels and notes
            column_name_mappings['property_notes'] = 'Property Notes'
            column_name_mappings['property_labels'] = 'Property Labels'

        elif hasattr(view_klass, 'taxlot'):
            select_related.append('taxlot')
            filter_str['taxlot__organization_id'] = org_id
            # always export the labels and notes
            column_name_mappings['taxlot_notes'] = 'Tax Lot Notes'
            column_name_mappings['taxlot_labels'] = 'Tax Lot Labels'

        model_views = view_klass.objects.select_related(*select_related).prefetch_related(
            *prefetch_related).filter(**filter_str).order_by('id')

        # get the data in a dict which includes the related data
        data = TaxLotProperty.get_related(model_views, column_ids, columns_from_database)

        derived_columns = column_profile.derived_columns.all() if column_profile is not None else []
        column_name_mappings.update({dc.name: dc.name for dc in derived_columns})

        # add labels, notes, and derived columns
        include_notes = request.data.get('include_notes', True)
        for i, record in enumerate(model_views):
            label_string = []
            note_string = []
            for label in list(record.labels.all().order_by('name')):
                label_string.append(label.name)
            if include_notes:
                for note in list(record.notes.all().order_by('created')):
                    note_string.append(
                        note.created.astimezone().strftime("%Y-%m-%d %I:%M:%S %p") + "\n" +
                        note.text
                    )

            if hasattr(record, 'property'):
                data[i]['property_labels'] = ','.join(label_string)
                data[i]['property_notes'] = '\n----------\n'.join(note_string) if include_notes else '(excluded during export)'
            elif hasattr(record, 'taxlot'):
                data[i]['taxlot_labels'] = ','.join(label_string)
                data[i]['taxlot_notes'] = '\n----------\n'.join(note_string) if include_notes else '(excluded during export)'

            # add derived columns
            for derived_column in derived_columns:
                data[i][derived_column.name] = derived_column.evaluate(inventory_state=record.state)

        # force the data into the same order as the IDs
        if ids:
            order_dict = {obj_id: index for index, obj_id in enumerate(ids)}
            if view_klass_str == 'properties':
                view_id_str = 'property_view_id'
            else:
                view_id_str = 'taxlot_view_id'
            data.sort(key=lambda inventory_obj: order_dict[inventory_obj[view_id_str]])

        export_type = request.data.get('export_type', 'csv')

        filename = request.data.get('filename', f"ExportedData.{export_type}")

        if export_type == "csv":
            return self._csv_response(filename, data, column_name_mappings)
        elif export_type == "geojson":
            return self._json_response(filename, data, column_name_mappings)
        elif export_type == "xlsx":
            return self._spreadsheet_response(filename, data, column_name_mappings)

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

    def _spreadsheet_response(self, filename, data, column_name_mappings):
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        scenario_keys = (
            'id', 'name', 'description', 'annual_site_energy_savings', 'annual_source_energy_savings',
            'annual_cost_savings', 'analysis_state', 'analysis_state_message', 'annual_electricity_savings',
            'annual_natural_gas_savings', 'annual_site_energy', 'annual_source_energy', 'annual_natural_gas_energy',
            'annual_electricity_energy', 'annual_peak_demand', 'annual_site_energy_use_intensity',
            'annual_source_energy_use_intensity'
        )
        scenario_key_mappings = {
            'annual_site_energy_savings': 'annual_site_energy_savings_mmbtu',
            'annual_source_energy_savings': 'annual_source_energy_savings_mmbtu',
            'annual_cost_savings': 'annual_cost_savings_dollars',
            'annual_site_energy': 'annual_site_energy_kbtu',
            'annual_site_energy_use_intensity': 'annual_site_energy_use_intensity_kbtu_ft2',
            'annual_source_energy': 'annual_source_energy_kbtu',
            'annual_source_energy_use_intensity': 'annual_source_energy_use_intensity_kbtu_ft2',
            'annual_natural_gas_energy': 'annual_natural_gas_energy_mmbtu',
            'annual_electricity_energy': 'annual_electricity_energy_mmbtu',
            'annual_peak_demand': 'annual_peak_demand_kw',
            'annual_electricity_savings': 'annual_electricity_savings_kbtu',
            'annual_natural_gas_savings': 'annual_natural_gas_savings_kbtu'
        }

        property_measure_keys = (
            'id', 'property_measure_name', 'measure_id', 'cost_mv', 'cost_total_first',
            'cost_installation', 'cost_material', 'cost_capital_replacement', 'cost_residual_value'
        )
        measure_keys = ('name', 'display_name', 'category', 'category_display_name')
        # find measures and scenarios
        for i, record in enumerate(data):
            measures = PropertyMeasure.objects.filter(property_state_id=record['property_state_id'])
            record['measures'] = measures

            scenarios = Scenario.objects.filter(property_state_id=record['property_state_id'])
            record['scenarios'] = scenarios

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'remove_timezone': True})

        # add tabs
        ws1 = wb.add_worksheet('Properties')
        ws2 = wb.add_worksheet('Measures')
        ws3 = wb.add_worksheet('Scenarios')
        ws4 = wb.add_worksheet('Scenario Measure Join Table')
        ws5 = wb.add_worksheet('Meter Readings')
        bold = wb.add_format({'bold': True})

        row = 0
        row2 = 0
        col2 = 0
        row3 = 0
        col3 = 0
        row4 = 0
        row5 = 0

        for index, val in enumerate(list(column_name_mappings.values())):
            # Do not write the first element as ID, this causes weird issues with Excel.
            if index == 0 and val == 'ID':
                ws1.write(row, index, 'id', bold)
            else:
                ws1.write(row, index, val, bold)

        # iterate over the results to preserve column order and write row.
        add_m_headers = True
        add_s_headers = True
        for datum in data:
            row += 1
            id = None
            for index, column in enumerate(column_name_mappings):
                if column == 'id':
                    id = datum.get(column, None)

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
                ws1.write(row, index, row_result)

            # measures
            for index, m in enumerate(datum['measures']):
                if add_m_headers:
                    # grab headers
                    for key in property_measure_keys:
                        ws2.write(row2, col2, key, bold)
                        col2 += 1
                    for key in measure_keys:
                        ws2.write(row2, col2, 'measure ' + key, bold)
                        col2 += 1
                    add_m_headers = False

                row2 += 1
                col2 = 0
                for key in property_measure_keys:
                    ws2.write(row2, col2, getattr(m, key))
                    col2 += 1
                for key in measure_keys:
                    ws2.write(row2, col2, getattr(m.measure, key))
                    col2 += 1

            # scenarios (and join table)
            # join table
            ws4.write('A1', 'property_id', bold)
            ws4.write('B1', 'scenario_id', bold)
            ws4.write('C1', 'measure_id', bold)
            for index, s in enumerate(datum['scenarios']):
                scenario_id = s.id
                if add_s_headers:
                    # grab headers
                    for key in scenario_keys:
                        # double check scenario_key_mappings in case a different header is desired
                        if key in scenario_key_mappings.keys():
                            key = scenario_key_mappings[key]
                        ws3.write(row3, col3, key, bold)
                        col3 += 1
                    add_s_headers = False
                row3 += 1
                col3 = 0
                for key in scenario_keys:
                    ws3.write(row3, col3, getattr(s, key))
                    col3 += 1

                for sm in s.measures.all():
                    row4 += 1
                    ws4.write(row4, 0, id)
                    ws4.write(row4, 1, scenario_id)
                    ws4.write(row4, 2, sm.id)

            # scenario meter readings
            ws5.write('A1', 'scenario_id', bold)
            ws5.write('B1', 'meter_id', bold)
            ws5.write('C1', 'type', bold)
            ws5.write('D1', 'start_time', bold)
            ws5.write('E1', 'end_time', bold)
            ws5.write('F1', 'reading', bold)
            ws5.write('G1', 'units', bold)
            ws5.write('H1', 'is_virtual', bold)
            # datetime formatting
            date_format = wb.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})

            for index, s in enumerate(datum['scenarios']):
                scenario_id = s.id
                # retrieve meters
                meters = Meter.objects.filter(scenario_id=scenario_id)
                for m in meters:
                    # retrieve readings
                    readings = MeterReading.objects.filter(meter_id=m.id).order_by('start_time')
                    for r in readings:
                        row5 += 1
                        ws5.write(row5, 0, scenario_id)
                        ws5.write(row5, 1, m.id)
                        the_type = next((item for item in Meter.ENERGY_TYPES if item[0] == m.type), None)
                        the_type = the_type[1] if the_type is not None else None
                        ws5.write(row5, 2, the_type)  # use energy type enum to determine reading type
                        ws5.write_datetime(row5, 3, r.start_time, date_format)
                        ws5.write_datetime(row5, 4, r.end_time, date_format)
                        ws5.write(row5, 5, r.reading)  # this is now a float field
                        ws5.write(row5, 6, r.source_unit)
                        ws5.write(row5, 7, m.is_virtual)

        wb.close()

        # xlsx_data contains the Excel file
        xlsx_data = output.getvalue()

        response.write(xlsx_data)
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
