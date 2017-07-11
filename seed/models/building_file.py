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
    property_state = models.ForeignKey('PropertyState', related_name='building_file', null=True)
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

    def process(self, organization_id, cycle):
        """
        Process the building file that was uploaded and create the correct models for the object

        :param organization_id: integer, ID of organization
        :param cycle: object, instance of cycle object
        :return: list, [status, and (PropertyState|None)]
        """

        if self.file_type == self.BUILDINGSYNC:
            bs = BuildingSync()
            bs.import_file(self.file.path)
            data, _, _ = bs.process(BuildingSync.BRICR_STRUCT)

            property_state = None
            if data:
                # subselect the data that are needed to create the PropertyState object
                md = MappingData()
                create_data = {"organization_id": organization_id}
                extra_data = {}
                for k, v in data.items():
                    # Skip the keys that are for measures and reports and process later
                    if k in ['measures', 'reports']:
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

                # create a new propertystate for the objects
                property_state = PropertyState.objects.create(**create_data)
                property_state.extra_data = extra_data
                property_state.save()

                # TODO: needs to be a merge instead of simply promoting
                property_state.promote(cycle)

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
                    join.cost_mv = m.get('mv_cost')
                    join.cost_total_first = m.get('measure_total_first_cost')
                    join.cost_installation = m.get('measure_installation_cost')
                    join.cost_material = m.get('measure_material_cost')
                    join.cost_capital_replacement = m.get('measure_capital_replacement_cost')
                    join.cost_residual_value = m.get('measure_residual_value')
                    join.save()

                PropertyAuditLog.objects.create(
                    organization_id=organization_id,
                    state_id=self.property_state_id,
                    name='Import Creation',
                    description='Creation from Import file.',
                    import_filename=self.file.path,
                    record_type=AUDIT_IMPORT
                )

            return True, property_state

        else:
            return False, None
