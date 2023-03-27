# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author nicholas.long@nrel.gov
"""
import copy
import logging
import os
import re
from datetime import datetime
from io import BytesIO, StringIO

import xmlschema
from buildingsync_asset_extractor.processor import BSyncProcessor as BAE
from django.core.exceptions import FieldDoesNotExist
from lxml import etree
from quantityfield.units import ureg

from config.settings.common import BASE_DIR
from seed.building_sync.mappings import (
    BASE_MAPPING_V2,
    BUILDINGSYNC_URI,
    NAMESPACES,
    apply_mapping,
    merge_mappings,
    table_mapping_to_buildingsync_mapping,
    update_tree
)
from seed.models.meters import Meter

_log = logging.getLogger(__name__)

# Setup lxml parser
parser = etree.XMLParser(remove_blank_text=True)
etree.set_default_parser(parser)
etree.register_namespace('auc', BUILDINGSYNC_URI)


class ParsingError(Exception):
    pass


class BuildingSync(object):
    BUILDINGSYNC_V2_0 = '2.0'
    BUILDINGSYNC_V2_0_0 = '2.0.0'
    BUILDINGSYNC_V2_1_0 = '2.1.0'
    BUILDINGSYNC_V2_2_0 = '2.2.0'
    BUILDINGSYNC_V2_3_0 = '2.3.0'
    BUILDINGSYNC_V2_4_0 = '2.4.0'
    VERSION_MAPPINGS_DICT = {
        BUILDINGSYNC_V2_0: BASE_MAPPING_V2,
        BUILDINGSYNC_V2_2_0: BASE_MAPPING_V2,
        BUILDINGSYNC_V2_3_0: BASE_MAPPING_V2,
        BUILDINGSYNC_V2_4_0: BASE_MAPPING_V2
    }

    def __init__(self):
        self.element_tree = None
        self.version = None

    def import_file(self, source):
        """imports BuildingSync file

        :param source: string | object, path to file or a file like object
        :param require_version: bool, if true it raises an exception if unable to find version info
        """
        parser = etree.XMLParser(remove_blank_text=True)
        etree.set_default_parser(parser)

        # save filename
        self.source_filename = source

        # save element tree
        if isinstance(source, str):
            if not os.path.isfile(source):
                raise ParsingError("File not found: {}".format(source))
            with open(source) as f:
                self.element_tree = etree.parse(f)
        else:
            self.element_tree = etree.parse(source)

        self.version = self._parse_version()

        # if the namespace map is missing the auc or xsi prefix, fix the tree to include it
        root_nsmap = self.element_tree.getroot().nsmap
        if root_nsmap.get('auc') is None or root_nsmap.get('xsi') is None:
            self.fix_namespaces()

        root = self.element_tree.getroot()
        root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.githubusercontent.com/BuildingSync/schema/v{}/BuildingSync.xsd'.format(self.version))

        return True

    def fix_namespaces(self):
        """This method should be called when then namespace map is not correct.
        It will clone the tree, ensuring all nodes have the proper namespace prefixes
        """
        original_tree = self.element_tree

        etree.register_namespace('auc', BUILDINGSYNC_URI)
        # only necessary because we are temporarily allowing the import of files
        # without xsi:schemaLocation
        # TODO: consider removing once all files have explicit versions
        etree.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        self.init_tree(version=self.version)
        new_root = self.element_tree.getroot()
        original_root = original_tree.getroot()

        def clone_subtree(original, new):
            for child in original.iterchildren():
                new_child = etree.Element(child.tag)
                # update text
                new_child.text = child.text
                # update attributes
                for attr, val in child.items():
                    new_child.set(attr, val)
                new.append(new_child)
                clone_subtree(child, new_child)

        clone_subtree(original_root, new_root)

    def init_tree(self, version=BUILDINGSYNC_V2_0):
        """Initializes the tree with a BuildingSync root node

        :param version: string, should be one of the valid BuildingSync versions
        """
        if version not in self.VERSION_MAPPINGS_DICT:
            raise ParsingError(f'Invalid version "{version}"')

        xml_string = '''<?xml version="1.0"?>
        <auc:BuildingSync xmlns:auc="http://buildingsync.net/schemas/bedes-auc/2019" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://buildingsync.net/schemas/bedes-auc/2019 https://raw.githubusercontent.com/BuildingSync/schema/v{}/BuildingSync.xsd">
        </auc:BuildingSync>'''.format(version)
        self.element_tree = etree.parse(StringIO(xml_string))
        self.version = version

    def export_using_profile(self, property_state, column_mapping_profile=None):
        """Export BuildingSync file from an existing BuildingSync file (from import), property_state and
        a custom mapping.

        expected column_mapping_profile structure
        [
            {from_field: <absolute xpath>, from_field_value: 'text' | @<attr> | ..., to_field: <db_column>},
            {from_field: <absolute xpath>, from_field_value: 'text' | @<attr> | ..., to_field: <db_column>},
            .
            .
            .
        ]

        :param property_state: object, PropertyState to merge into BuildingSync
        :param column_mapping_profile: list, mappings from ColumnMappingProfile
        :return: string, as XML
        """
        if not property_state:
            return etree.tostring(self.element_tree, pretty_print=True).decode()

        if not self.element_tree:
            self.init_tree(version=BuildingSync.BUILDINGSYNC_V2_0)

        schema = self.get_schema(self.version)

        # iterate through the mappings doing the following
        # - if the property_state has the field, update the xml with that value
        # - else, ignore it
        for mapping in column_mapping_profile:
            field = mapping['to_field']
            xml_element_xpath = mapping['from_field']
            xml_element_value = mapping['from_field_value']
            seed_value = None
            if mapping['to_field'] != mapping['from_field']:
                # only do this for non BAE assets
                try:
                    property_state._meta.get_field(field)
                    seed_value = getattr(property_state, field)
                except FieldDoesNotExist:
                    _log.debug("Field {} is not a db field, trying read from extra data".format(field))
                    seed_value = property_state.extra_data.get(field, None)
                    continue

            if seed_value is None:
                continue
            if isinstance(seed_value, ureg.Quantity):
                seed_value = seed_value.magnitude

            update_tree(schema, self.element_tree, xml_element_xpath,
                        xml_element_value, str(seed_value), NAMESPACES)

        # Not sure why, but lxml was not pretty printing if the tree was updated
        # As a hack to fix this, we just export the tree, parse it, then export again
        xml_bytes = etree.tostring(self.element_tree, pretty_print=True)
        tree = etree.parse(BytesIO(xml_bytes))
        return etree.tostring(tree, pretty_print=True).decode()

    @classmethod
    def get_schema(cls, version):
        schema_dir = os.path.join(BASE_DIR, 'seed', 'building_sync', 'schemas')
        # TODO: refactor so we don't have to explicitly write schema version for
        # ever new schema added.
        schema_files = {
            cls.BUILDINGSYNC_V2_0: 'BuildingSync_v2_0.xsd',
            cls.BUILDINGSYNC_V2_1_0: 'BuildingSync_v2_1_0.xsd',
            cls.BUILDINGSYNC_V2_2_0: 'BuildingSync_v2_2_0.xsd',
            cls.BUILDINGSYNC_V2_3_0: 'BuildingSync_v2_3_0.xsd',
            cls.BUILDINGSYNC_V2_4_0: 'BuildingSync_v2_4_0.xsd',
        }
        if version in schema_files:
            schema_path = os.path.join(schema_dir, schema_files[version])
        else:
            raise ParsingError(f'Unknown file version "{version}"')

        return xmlschema.XMLSchema(schema_path)

    def restructure_mapped_result(self, result, messages):
        """Transforms the dict from applying a mapping into a more standardized structure
        for SEED to store into a model

        :param result: dict, the mapped values
        :param messages: dict, dictionary for recording warnings and errors
        :return: dict, restructured dictionary
        """
        measures = []
        for measure in result['measures']:
            if measure['category'] == '':
                messages['warnings'].append(f'Skipping measure {measure["name"]} due to missing category')
                continue

            measures.append(measure)

        scenarios = []
        for scenario in result['scenarios']:
            # process the scenario meters (aka resource uses)
            meters = {}
            for resource_use in scenario['resource_uses']:
                if resource_use['type'] is None or resource_use['units'] is None:
                    messages['warnings'].append(f'Skipping resource use {resource_use.get("source_id")} due to missing type or units')
                    continue

                meter = {
                    'source': Meter.BUILDINGSYNC,
                    'source_id': resource_use['source_id'],
                    'type': resource_use['type'],
                    'units': resource_use['units'],
                    'is_virtual': scenario['is_virtual'],
                    'readings': [],
                }

                meters[meter['source_id']] = meter

            # process the scenario meter readings
            for series_data in scenario['time_series']:
                meter_reading = {
                    'start_time': series_data['start_time'],
                    'end_time': series_data['end_time'],
                    'reading': series_data['reading'],
                    'source_id': series_data['source_id'],
                }
                meter_reading['source_unit'] = meters[meter_reading['source_id']].get('units')

                # add reading to the meter
                meters[meter_reading['source_id']]['readings'].append(meter_reading)

                #
                # Begin Audit Template weirdness
                #

                # Audit Template (AT) puts some meter reading data in AllResourceTotals
                # It uses a UserDefinedField "Linked Time Series ID" to associate the
                # reading with an auc:TimeSeries (which stores the other relevant info
                # including start time, end time, etc)
                for all_resource_total in scenario['audit_template_all_resource_totals']:
                    if all_resource_total['linked_time_series_id'] == series_data['id']:
                        # store this data in a separate "meter" -- we can't have two
                        # readings for the same time period in SEED currently
                        # NOTE: to future reader, this problem seems to arise from the
                        # fact that SEED is unaware of the _type_ of reading,
                        # e.g., see BuildingSync's ReadingType (point, median, average, peak, etc)

                        # if the meter doesn't exist yet, copy it
                        original_meter = meters[meter_reading['source_id']]
                        other_meter_source_id = f'Site Energy Use {original_meter["source_id"]}'
                        if other_meter_source_id not in meters:
                            meters[other_meter_source_id] = {
                                **original_meter,
                                'source_id': other_meter_source_id,
                                'readings': []
                            }

                        meters[other_meter_source_id]['readings'].append({
                            **meter_reading,
                            'reading': all_resource_total['site_energy_use']
                        })

                #
                # End Audit Template weirdness
                #

            # clean up the meters so that we only include ones with readings
            meters_with_readings = []
            for meter_id, meter in meters.items():
                if meter['readings']:
                    meters_with_readings.append(meter)
                else:
                    messages['warnings'].append(
                        f'Skipping meter {meter_id} because it had no valid readings.'
                    )

            # create scenario
            seed_scenario = {
                'id': scenario['id'],
                'name': scenario['name'],
                'temporal_status': scenario['temporal_status'],
                'reference_case': scenario['reference_case'],
                'annual_site_energy_savings': scenario['annual_site_energy_savings'],
                'annual_source_energy_savings': scenario['annual_source_energy_savings'],
                'annual_cost_savings': scenario['annual_cost_savings'],
                'annual_electricity_savings': scenario['annual_electricity_savings'],
                'annual_natural_gas_savings': scenario['annual_natural_gas_savings'],
                'annual_site_energy': scenario['annual_site_energy'],
                'annual_site_energy_use_intensity': scenario['annual_site_energy_use_intensity'],
                'annual_source_energy': scenario['annual_source_energy'],
                'annual_source_energy_use_intensity': scenario['annual_source_energy_use_intensity'],
                'annual_electricity_energy': scenario['annual_electricity_energy'],
                'annual_peak_demand': scenario['annual_peak_demand'],
                'annual_peak_electricity_reduction': scenario['annual_peak_electricity_reduction'],
                'annual_natural_gas_energy': scenario['annual_natural_gas_energy'],
                'measures': [id['id'] for id in scenario['measure_ids']],
                'meters': meters_with_readings,
            }

            #
            # Begin Audit Template weirdness
            #
            # Audit Template (AT) BuildingSync files include scenarios we don't want
            # in SEED. For example, "Audit Template Annual Summary - Electricity"
            # which doesn't contain measures or meter data so we want to skip it.
            # Note that it's OK to skip scenarios without measures b/c AT does not
            # have Baseline scenarios (the type of scenario where it's OK to not
            # have measures.
            #

            if (
                self._is_from_audit_template_tool()
                and not seed_scenario['measures']
                and not seed_scenario['meters']
            ):
                # Skip this scenario!
                messages['warnings'].append(
                    f'Skipping Scenario {scenario["id"]} because it doesn\'t include '
                    'measures or meter data.'
                )
                continue

            #
            # End Audit Template weirdness
            #

            scenarios.append(seed_scenario)

        # get most recent audit date
        audit_dates = result["audit_dates"]
        audit_dates.sort(key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"))
        most_recent_audit_date = {} if len(audit_dates) == 0 else audit_dates[-1]

        property_ = result['property']
        res = {
            'measures': measures,
            'scenarios': scenarios,
            # property fields are at the root of the object
            'address_line_1': property_['address_line_1'],
            'city': property_['city'],
            'state': property_['state'],
            'postal_code': property_['postal_code'],
            'longitude': property_['longitude'],
            'latitude': property_['latitude'],
            'property_name': property_['property_name'],
            'property_type': property_['property_type'],
            'year_built': property_['year_built'],
            'floors_above_grade': property_['floors_above_grade'],
            'floors_below_grade': property_['floors_below_grade'],
            'premise_identifier': property_['premise_identifier'],
            'custom_id_1': property_['custom_id_1'],
            'gross_floor_area': property_['gross_floor_area'],
            'net_floor_area': property_['net_floor_area'],
            'footprint_floor_area': property_['footprint_floor_area'],
            'audit_template_building_id': property_['audit_template_building_id'],
            'audit_date': most_recent_audit_date.get("date"),
            'audit_date_type': most_recent_audit_date.get("custom_date_type"),
        }

        return res

    def _process_struct(self, base_mapping, custom_mapping=None):
        """Internal call for processing the xml data into data for SEED

        :param base_mapping: dict, a base mapping object; see mappings.py
        :param custom_mapping: dict, another mapping object which is given higher priority over base_mapping
        :return: list, [dict, dict], [results, dict of errors and warnings]
        """

        merged_mappings = merge_mappings(base_mapping, custom_mapping)
        messages = {'warnings': [], 'errors': []}
        result = apply_mapping(self.element_tree, merged_mappings, messages, NAMESPACES)

        # turn result into SEED structure
        seed_result = self.restructure_mapped_result(result, messages)

        # BuildingSync Asset Extractor
        bae = BAE(self.source_filename)
        bae.extract()
        assets = bae.get_assets()

        # add to data and column headers
        for item in assets:
            seed_result[item['name']] = item['value']

        return seed_result, messages

    def process(self, table_mappings=None):
        """Process the BuildingSync file based on the process structure.

        :param table_mapping: dict, a table_mapping structure from ColumnMapping.get_column_mappings_by_table_name()
        :return: list, [dict, dict], [results, dict of errors and warnings]
        """
        # API call to BuildingSync Selection Tool on other server for appropriate use case
        # prcess_struct = new_use_case (from Building Selection Tool)
        base_mapping = self.VERSION_MAPPINGS_DICT.get(self.version)
        if base_mapping is None:
            raise ParsingError(f'Version of BuildingSync object is not supported: "{self.version}"')

        # convert the table_mappings into a buildingsync mapping
        custom_mapping = None
        if table_mappings is not None:
            custom_mapping = table_mapping_to_buildingsync_mapping(table_mappings)

        return self._process_struct(base_mapping, custom_mapping)

    def process_property_xpaths(self, table_mappings=None):
        """Process the BuildingSync file based on the mapping structure. Result is
        a flat dict of PropertyState fields with the full xpaths as keys and
        their parsed values as the value

        :param table_mapping: dict, a table_mapping structure from ColumnMapping.get_column_mappings_by_table_name()
        :return: dict, results
        """
        base_mapping = self.VERSION_MAPPINGS_DICT.get(self.version)
        if base_mapping is None:
            raise ParsingError(f'Version of BuildingSync object is not supported: "{self.version}"')

        # convert the table_mappings into a buildingsync mapping
        custom_mapping = None
        if table_mappings is not None:
            custom_mapping = table_mapping_to_buildingsync_mapping(table_mappings)

        merged_mapping = merge_mappings(base_mapping, custom_mapping)

        # remove all root keys except for property since we only want to process property
        for key, _ in merged_mapping.copy().items():
            if key != 'property':
                del merged_mapping[key]

        messages = {'warnings': [], 'errors': []}
        result = apply_mapping(self.element_tree, merged_mapping, messages,
                               NAMESPACES, xpaths_as_keys=True)

        # flatten the dictionary and make all keys absolute xpaths
        base_xpath = list(result.keys())[0]  # only one key in result, the property xpath
        flattened_result = {}
        for relative_xpath, value in result[base_xpath].items():
            abs_xpath = base_xpath.rstrip('/') + '/' + relative_xpath.lstrip('./')
            flattened_result[abs_xpath] = value

        return flattened_result

    def _parse_version(self):
        """Attempts to get the schema version from the imported data. Raises an exception if
        none is found or if it's an invalid version.

        :return: string, schema version (raises Exception when not found or invalid)
        """
        if self.element_tree is None:
            raise ParsingError('A file must first be imported with import method')

        bsync_element = self.element_tree.getroot()
        if not bsync_element.tag.endswith('BuildingSync'):
            raise ParsingError('Expected BuildingSync element as root element in xml')

        # first check for a version attribute in the buldingsync tag
        if "version" in bsync_element.attrib:
            return bsync_element.attrib["version"]

        # second check if it's a file form Audit Template Tool
        if self._is_from_audit_template_tool():

            # it must be a 2.0 file as that was the last version which didn't require @version
            return self.BUILDINGSYNC_V2_0

        # attempt to parse the version from the xsi:schemaLocation
        schemas = bsync_element.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', '').split()
        schema_regex = r'^https\:\/\/raw\.githubusercontent\.com\/BuildingSync\/schema\/v((\d+\.\d+)(-pr\d+)?)\/BuildingSync\.xsd$'

        for schema_def in schemas:
            schema_search = re.search(schema_regex, schema_def)
            if schema_search:
                parsed_version = schema_search.group(1)
                if parsed_version in self.VERSION_MAPPINGS_DICT:
                    return parsed_version

                raise ParsingError(f'Unsupported BuildingSync schema version "{parsed_version}". Supported versions: {list(self.VERSION_MAPPINGS_DICT.keys())}')

        raise ParsingError('Invalid or missing schema specification. Expected a valid BuildingSync schemaLocation in the BuildingSync element. For example: https://raw.githubusercontent.com/BuildingSync/schema/v<schema version here>/BuildingSync.xsd')

    def _is_from_audit_template_tool(self):
        """Determines if the source file is from audit template tool

        :return bool:
        """
        report_type_xpath = '/' + '/'.join(['auc:BuildingSync',
                                            'auc:Facilities',
                                            'auc:Facility',
                                            'auc:Reports',
                                            'auc:Report',
                                            'auc:UserDefinedFields',
                                            'auc:UserDefinedField[auc:FieldName="Audit Template Report Type"]'])

        report_type = self.element_tree.xpath(report_type_xpath, namespaces=NAMESPACES)
        return len(report_type) != 0

    def get_base_mapping(self):
        if not self.version:
            raise ParsingError('You must call import_file to determine the version first')
        return copy.deepcopy(self.VERSION_MAPPINGS_DICT[self.version])
