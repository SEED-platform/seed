# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""
from __future__ import unicode_literals

import logging

from django.db import models

from seed.building_sync.building_sync import BuildingSync, ParsingError
from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.hpxml.hpxml import HPXML as HPXMLParser
from seed.lib.merging.merging import merge_state
from seed.models import (
    PropertyState,
    Column,
    PropertyMeasure,
    Measure,
    PropertyAuditLog,
    AUDIT_IMPORT,
    Scenario,
    Meter,
    MeterReading,
    MERGE_STATE_MERGED,
)


_log = logging.getLogger(__name__)


class BuildingFile(models.Model):
    """
    BuildingFile contains any building related file, such as a BuildingSync file, that
    are attached to a PropertyState. Typically the file is used to create/update the
    PropertyState record.
    """
    UNKNOWN = 0
    BUILDINGSYNC = 1
    HPXML = 3

    BUILDING_FILE_TYPES = (
        (UNKNOWN, 'Unknown'),
        (BUILDINGSYNC, 'BuildingSync'),
        (HPXML, 'HPXML')
    )

    BUILDING_FILE_PARSERS = {
        HPXML: HPXMLParser,
        BUILDINGSYNC: BuildingSync
    }

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    property_state = models.ForeignKey('PropertyState', on_delete=models.CASCADE, related_name='building_files', null=True)
    file = models.FileField(upload_to="buildingsync_files", max_length=500, blank=True, null=True)
    file_type = models.IntegerField(choices=BUILDING_FILE_TYPES, default=UNKNOWN)
    filename = models.CharField(blank=True, max_length=255)

    _cache_kbtu_thermal_conversion_factors = None

    @classmethod
    def str_to_file_type(cls, file_type):
        """
        convert an integer or string of the file_type to the integer that will be saved

        :param file_type: integer or string, file type name
        :return: integer, enum integer
        """
        if not file_type:
            return None

        # If it is already an integer, then move along.
        try:
            if int(file_type):
                return int(file_type)
        except ValueError:
            pass

        value = [y[0] for x, y in enumerate(cls.BUILDING_FILE_TYPES) if
                 y[1].lower() == file_type.lower()]
        if len(value) == 1:
            return value[0]
        else:
            return None

    def _create_property_state(self, organization_id, data):
        """given data parsed from a file, it creates the property state
        for this BuildingFile and returns it.

        :param organization_id: integer, ID of organization
        :param data: dict, a dictionary that was returned from a parser
        :return: PropertyState
        """
        # sub-select the data that are needed to create the PropertyState object
        db_columns = Column.retrieve_db_field_table_and_names_from_db_tables()
        create_data = {"organization_id": organization_id}
        extra_data = {}
        for k, v in data.items():
            # Skip the keys that are for measures and reports and process later
            if k in ['measures', 'reports', 'scenarios']:
                continue

            # Check if the column exists, if not, then create one.
            if ('PropertyState', k) in db_columns:
                create_data[k] = v
            else:
                extra_data[k] = v

        # create the property state
        property_state = PropertyState.objects.create(**create_data, extra_data=extra_data)

        PropertyAuditLog.objects.create(
            organization_id=organization_id,
            state_id=property_state.id,
            name='Import Creation',
            description='Creation from Import file.',
            import_filename=self.file.path,
            record_type=AUDIT_IMPORT
        )
        # set the property_state_id so that we can list the building files by properties
        self.property_state_id = property_state.id
        self.save()

        Column.save_column_names(property_state)

        return property_state

    def _kbtu_thermal_conversion_factors(self):
        if self._cache_kbtu_thermal_conversion_factors is None:
            # assuming "US" for conversion_factor but could be "CAN"
            self._cache_kbtu_thermal_conversion_factors = kbtu_thermal_conversion_factors("US")

        return self._cache_kbtu_thermal_conversion_factors

    def process(self, organization_id, cycle, property_view=None):
        """
        Process the building file that was uploaded and create the correct models for the object

        :param organization_id: integer, ID of organization
        :param cycle: object, instance of cycle object
        :param property_view: Existing property view of the building file that will be updated from merging the property_view.state
        :return: list, [status, (PropertyState|None), (PropertyView|None), messages]
        """

        Parser = self.BUILDING_FILE_PARSERS.get(self.file_type, None)
        if not Parser:
            acceptable_file_types = ', '.join(
                map(dict(self.BUILDING_FILE_TYPES).get, list(self.BUILDING_FILE_PARSERS.keys()))
            )
            return False, None, None, "File format was not one of: {}".format(acceptable_file_types)

        parser = Parser()
        try:
            parser.import_file(self.file.path)
            parser_args = []
            parser_kwargs = {}
            # TODO: use table_mappings for BuildingSync process method
            data, messages = parser.process(*parser_args, **parser_kwargs)
        except ParsingError as e:
            return False, None, None, [str(e)]

        if len(messages['errors']) > 0 or not data:
            return False, None, None, messages

        # Create the property state if none already exists for this file
        if self.property_state is None:
            property_state = self._create_property_state(organization_id, data)
        else:
            property_state = self.property_state

        # save the property state
        self.property_state_id = property_state.id
        self.save()

        # add in the measures
        for m in data.get('measures', []):
            # Find the measure in the database
            try:
                measure = Measure.objects.get(
                    category=m['category'], name=m['name'], organization_id=organization_id,
                )
            except Measure.DoesNotExist:
                messages['warnings'].append('Measure category and name is not valid %s:%s' % (m['category'], m['name']))
                continue

            # Add the measure to the join table.
            # Need to determine what constitutes the unique measure for a property
            implementation_status = m['implementation_status'] if m.get('implementation_status') else 'Proposed'
            application_scale = m['application_scale_of_application'] if m.get('application_scale_of_application') else PropertyMeasure.SCALE_ENTIRE_FACILITY
            category_affected = m['system_category_affected'] if m.get('system_category_affected') else PropertyMeasure.CATEGORY_OTHER
            # for some reason this is returning none if the field is empty. So none and true should both be true.
            recommended = str(m.get('recommended', 'true')).lower() in ['true', 'none']
            join, _ = PropertyMeasure.objects.get_or_create(
                property_state_id=self.property_state_id,
                measure_id=measure.pk,
                property_measure_name=m.get('property_measure_name'),
                implementation_status=PropertyMeasure.str_to_impl_status(implementation_status),
                application_scale=PropertyMeasure.str_to_application_scale(application_scale),
                category_affected=PropertyMeasure.str_to_category_affected(category_affected),
                recommended=recommended,
            )
            join.description = m.get('description')
            join.cost_mv = m.get('mv_cost')
            join.cost_total_first = m.get('measure_total_first_cost')
            join.cost_installation = m.get('measure_installation_cost')
            join.cost_material = m.get('measure_material_cost')
            join.cost_capital_replacement = m.get('measure_capital_replacement_cost')
            join.cost_residual_value = m.get('measure_residual_value')
            join.useful_life = m.get('useful_life')
            join.save()

        # add in scenarios
        linked_meters = []
        for s in data.get('scenarios', []):
            # measures = models.ManyToManyField(PropertyMeasure)

            # {'reference_case': 'Baseline', 'annual_savings_site_energy': None,
            #  'measures': [], 'id': 'Baseline', 'name': 'Baseline'}

            # If the scenario does not have a name then log a warning and continue
            if not s.get('name'):
                messages['warnings'].append('Skipping scenario because it does not have a name. ID = %s' % s.get('id'))
                continue

            scenario, _ = Scenario.objects.get_or_create(
                name=s.get('name'),
                property_state_id=self.property_state_id,
            )
            scenario.description = s.get('description')
            scenario.annual_site_energy_savings = s.get('annual_site_energy_savings')
            scenario.annual_source_energy_savings = s.get('annual_source_energy_savings')
            scenario.annual_cost_savings = s.get('annual_cost_savings')
            scenario.summer_peak_load_reduction = s.get('summer_peak_load_reduction')
            scenario.winter_peak_load_reduction = s.get('winter_peak_load_reduction')
            scenario.hdd = s.get('hdd')
            scenario.hdd_base_temperature = s.get('hdd_base_temperature')
            scenario.cdd = s.get('cdd')
            scenario.cdd_base_temperature = s.get('cdd_base_temperature')
            scenario.annual_electricity_savings = s.get('annual_electricity_savings')
            scenario.annual_natural_gas_savings = s.get('annual_natural_gas_savings')
            scenario.annual_site_energy = s.get('annual_site_energy')
            scenario.annual_source_energy = s.get('annual_source_energy')
            scenario.annual_site_energy_use_intensity = s.get('annual_site_energy_use_intensity')
            scenario.annual_source_energy_use_intensity = s.get('annual_source_energy_use_intensity')
            scenario.annual_natural_gas_energy = s.get('annual_natural_gas_energy')
            scenario.annual_electricity_energy = s.get('annual_electricity_energy')
            scenario.annual_peak_demand = s.get('annual_peak_demand')
            scenario.annual_peak_electricity_reduction = s.get('annual_peak_electricity_reduction')

            # temporal_status = models.IntegerField(choices=TEMPORAL_STATUS_TYPES,
            #                                       default=TEMPORAL_STATUS_CURRENT)

            if s.get('reference_case'):
                ref_case = Scenario.objects.filter(
                    name=s.get('reference_case'),
                    property_state_id=self.property_state_id,
                )
                if len(ref_case) == 1:
                    scenario.reference_case = ref_case.first()

            # set the list of measures. Note that this can be empty (e.g. baseline has no measures)
            for measure_name in s.get('measures', []):
                # find the join measure in the database
                measure = None
                try:
                    measure = PropertyMeasure.objects.get(
                        property_state_id=self.property_state_id,
                        property_measure_name=measure_name,
                    )
                except PropertyMeasure.DoesNotExist:
                    # PropertyMeasure is not in database, skipping silently
                    messages['warnings'].append('Measure associated with scenario not found. Scenario: %s, Measure name: %s' % (s.get('name'), measure_name))
                    continue

                scenario.measures.add(measure)

            scenario.save()

            # meters
            energy_types = dict(Meter.ENERGY_TYPES)
            for m in s.get('meters', []):
                num_skipped_readings = 0
                valid_readings = []
                for mr in m.get('readings', []):
                    is_usable = (
                        mr.get('start_time') is not None
                        and mr.get('end_time') is not None
                        and mr.get('reading') is not None
                    )
                    if is_usable:
                        valid_readings.append(mr)
                    else:
                        num_skipped_readings += 1

                if len(valid_readings) == 0:
                    # skip this meter
                    messages['warnings'].append(f'Skipped meter {m.get("source_id")} because it had no valid readings')
                    continue

                if num_skipped_readings > 0:
                    messages['warnings'].append(
                        f'Skipped {num_skipped_readings} readings due to missing start time,'
                        f' end time, or reading value for meter {m.get("source_id")}'
                    )

                # print("BUILDING FILE METER: {}".format(m))
                # check by scenario_id and source_id
                meter, _ = Meter.objects.get_or_create(
                    scenario_id=scenario.id,
                    source_id=m.get('source_id'),
                )
                meter.source = m.get('source')
                meter.type = m.get('type')
                if meter.type is None:
                    meter.type = Meter.OTHER
                meter.is_virtual = m.get('is_virtual')
                if meter.is_virtual is None:
                    meter.is_virtual = False
                meter.save()
                linked_meters.append(meter)

                # meterreadings
                if meter.type in energy_types:
                    meter_type = energy_types[meter.type]
                else:
                    meter_type = None
                meter_conversions = self._kbtu_thermal_conversion_factors().get(meter_type, {})

                valid_reading_models = {
                    MeterReading(
                        start_time=mr.get('start_time'),
                        end_time=mr.get('end_time'),
                        reading=float(mr.get('reading', 0)) * meter_conversions.get(mr.get('source_unit'), 1.00),
                        source_unit=mr.get('source_unit'),
                        meter_id=meter.id,
                        conversion_factor=meter_conversions.get(mr.get('source_unit'), 1.00)
                    )
                    for mr in valid_readings
                }
                MeterReading.objects.bulk_create(valid_reading_models)

        # merge or create the property state's view
        if property_view:
            # create a new blank state to merge the two together
            merged_state = PropertyState.objects.create(organization_id=organization_id)

            # assume the same cycle id as the former state.
            # should merge_state also copy/move over the relationships?
            priorities = Column.retrieve_priorities(organization_id)
            merged_state = merge_state(
                merged_state, property_view.state, property_state, priorities['PropertyState']
            )

            # log the merge
            # Not a fan of the parent1/parent2 logic here, seems error prone, what this
            # is also in here: https://github.com/SEED-platform/seed/blob/63536e99cf5be3a9a86391c5cead6dd4ff74462b/seed/data_importer/tasks.py#L1549
            PropertyAuditLog.objects.create(
                organization_id=organization_id,
                parent1=PropertyAuditLog.objects.filter(state=property_view.state).first(),
                parent2=PropertyAuditLog.objects.filter(state=property_state).first(),
                parent_state1=property_view.state,
                parent_state2=property_state,
                state=merged_state,
                name='System Match',
                description='Automatic Merge',
                import_filename=None,
                record_type=AUDIT_IMPORT
            )

            property_view.state = merged_state
            property_view.save()

            merged_state.merge_state = MERGE_STATE_MERGED
            merged_state.save()

            # set the property_state to the new one
            property_state = merged_state
        elif not property_view:
            property_view = property_state.promote(cycle)
        else:
            # invalid arguments, must pass both or neither
            return False, None, None, "Invalid arguments passed to BuildingFile.process()"

        for meter in linked_meters:
            meter.property = property_view.property
            meter.save()

        return True, property_state, property_view, messages
