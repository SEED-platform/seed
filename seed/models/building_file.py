# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""
from __future__ import unicode_literals

import logging

from django.db import models

from seed.building_sync.building_sync import BuildingSync
from seed.lib.mappings.mapping_data import MappingData
from seed.models import (
    PropertyState,
    Column,
    PropertyMeasure,
    Measure,
    PropertyAuditLog,
    AUDIT_IMPORT,
    Scenario,
    PropertyView,
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
    GEOJSON = 2

    BUILDING_FILE_TYPES = (
        (UNKNOWN, 'Unknown'),
        (BUILDINGSYNC, 'BuildingSync'),
        (GEOJSON, 'GeoJSON'),
    )
    # def upload_path(self):
    #     if not self.pk:
    #         i = BuildingSyncFile.objects.create()
    #         self.id = self.pk = i.id
    #     return "properties/%s/buildingsync" % str(self.id)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    property_state = models.ForeignKey('PropertyState', related_name='building_files', null=True)
    file = models.FileField(upload_to="buildingsync_files", max_length=500, blank=True, null=True)
    file_type = models.IntegerField(choices=BUILDING_FILE_TYPES, default=UNKNOWN)
    filename = models.CharField(blank=True, max_length=255)

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

    def process(self, organization_id, cycle, property_view=None):
        """
        Process the building file that was uploaded and create the correct models for the object

        :param organization_id: integer, ID of organization
        :param cycle: object, instance of cycle object
        :param property_view: PropertyView, if a property view already exists, this is it; if not, one will be created
        :return: list, [status, (PropertyView|None), messages]
        """

        if self.file_type != self.BUILDINGSYNC:
            return False, None, "File format was not set to BuildingSync"

        bs = BuildingSync()
        bs.import_file(self.file.path)
        data, errors, messages = bs.process(BuildingSync.BRICR_STRUCT)

        if errors or not data:
            return False, None, messages

        # sub-select the data that are needed to create the PropertyState object
        md = MappingData()
        create_data = {"organization_id": organization_id}
        extra_data = {}
        for k, v in data.items():
            # Skip the keys that are for measures and reports and process later
            if k in ['measures', 'reports', 'scenarios']:
                continue

            if md.find_column('PropertyState', k):
                create_data[k] = v
            else:
                # TODO: break out columns in the extra data that should be part of the
                # PropertyState and which ones should be added to some other class that
                # doesn't exist yet.
                extra_data[k] = v
                # create columns, if needed, for the extra_data fields

                Column.objects.get_or_create(
                    organization_id=organization_id,
                    column_name=k,
                    table_name='PropertyState',
                    is_extra_data=True,
                )

        if property_view:

            # and get the property state from this view
            property_state = property_view.state

        else:

            # create a new propertystate for the objects
            property_state = PropertyState.objects.create(**create_data)
            property_state.extra_data = extra_data
            property_state.save()

            # automatically promote this buildingsync file to a new instance
            property_view = property_state.promote(cycle)

        # set the property_state_id so that we can list the building files by properties
        self.property_state_id = property_state.id
        self.save()

        # add in the measures
        for m in data['measures']:
            # Find the measure in the database
            measure = Measure.objects.get(
                category=m['category'], name=m['name'], organization_id=organization_id,
            )

            # Add the measure to the join table.
            # Need to determine what constitutes the unique measure for a property
            join, _ = PropertyMeasure.objects.get_or_create(
                property_state_id=self.property_state_id,
                measure_id=measure.pk,
                implementation_status=PropertyMeasure.str_to_impl_status(
                    m['implementation_status']
                ),
                application_scale=PropertyMeasure.str_to_application_scale(
                    m.get('application_scale_of_application',
                          PropertyMeasure.SCALE_ENTIRE_FACILITY)
                ),
                category_affected=PropertyMeasure.str_to_category_affected(
                    m.get('system_category_affected', PropertyMeasure.CATEGORY_OTHER)
                ),
                recommended=m.get('recommended', 'false') == 'true',
            )
            join.description = m.get('description')
            join.property_measure_name = m.get('property_measure_name')
            join.cost_mv = m.get('mv_cost')
            join.cost_total_first = m.get('measure_total_first_cost')
            join.cost_installation = m.get('measure_installation_cost')
            join.cost_material = m.get('measure_material_cost')
            join.cost_capital_replacement = m.get('measure_capital_replacement_cost')
            join.cost_residual_value = m.get('measure_residual_value')
            join.save()

        # add in scenarios
        for s in data['scenarios']:
            # measures = models.ManyToManyField(PropertyMeasure)

            # {'reference_case': u'Baseline', 'annual_savings_site_energy': None,
            #  'measures': [], 'id': u'Baseline', 'name': u'Baseline'}

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

            # temporal_status = models.IntegerField(choices=TEMPORAL_STATUS_TYPES,
            #                                       default=TEMPORAL_STATUS_CURRENT)

            if s.get('reference_case'):
                ref_case = Scenario.objects.filter(
                    name=s.get('reference_case'),
                    property_state_id=self.property_state_id,
                )
                if len(ref_case) == 1:
                    scenario.reference_case = ref_case.first()

            # set the list of measures
            for measure_name in s['measures']:
                # find the join measure in the database
                measure = None
                try:
                    measure = PropertyMeasure.objects.get(
                        property_state_id=self.property_state_id,
                        property_measure_name=measure_name,
                    )
                except PropertyMeasure.DoesNotExist:
                    # PropertyMeasure is not in database, skipping silently
                    continue

                scenario.measures.add(measure)

            scenario.save()

        PropertyAuditLog.objects.create(
            organization_id=organization_id,
            state_id=self.property_state_id,
            name='Import Creation',
            description='Creation from Import file.',
            import_filename=self.file.path,
            record_type=AUDIT_IMPORT
        )

        return True, property_view, messages
