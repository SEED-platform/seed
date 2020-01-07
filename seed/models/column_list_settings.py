# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from collections import OrderedDict

from django.apps import apps
from django.db import models

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models import (
    Column,
)

VIEW_LIST = 0
VIEW_DETAIL = 1
VIEW_LOCATION_TYPES = [
    (VIEW_LIST, 'List View Settings'),
    (VIEW_DETAIL, 'Detail View Settings'),
]

VIEW_LIST_PROPERTY = 0
VIEW_LIST_TAXLOT = 1
VIEW_LIST_INVENTORY_TYPE = [
    (VIEW_LIST_PROPERTY, 'Property'),
    (VIEW_LIST_TAXLOT, 'Tax Lot'),
]


class ColumnListSetting(models.Model):
    """Ability to persist a list of views with different columns. The list of column views points to the columns that
    are contained in the list view."""

    organization = models.ForeignKey(SuperOrganization, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=512, db_index=True)
    settings_location = models.IntegerField(choices=VIEW_LOCATION_TYPES, default=VIEW_LIST)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    columns = models.ManyToManyField(Column, related_name='column_list_settings',
                                     through='seed.ColumnListSettingColumn')

    PROFILE_TYPE = {'properties': VIEW_LIST_PROPERTY, 'taxlots': VIEW_LIST_TAXLOT}
    COLUMN_TYPE = {'properties': 'property', 'taxlots': 'taxlot'}

    @classmethod
    def return_columns(cls, organization_id, profile_id, inventory_type='properties'):
        """
        Return a list of columns based on the profile_id. If the profile ID doesn't exist, then it
        will return the list of raw database fields for the organization (i.e. all the fields).

        :param organization_id: int, ID of the organization
        :param profile_id: int, ID of the profile id to retrieve
        :param inventory_type: str, type of inventory (either properties or taxlots)
        :return: list, column_ids, column_name_mappings, and selected_columns_from_database
        """
        try:
            profile = ColumnListSetting.objects.get(
                organization=organization_id,
                id=profile_id,
                settings_location=VIEW_LIST,
                inventory_type=cls.PROFILE_TYPE[inventory_type]
            )
            profile_id = profile.id

        except ColumnListSetting.DoesNotExist:
            profile_id = False

        column_ids = []
        column_name_mappings = OrderedDict()
        columns_from_database = Column.retrieve_all(organization_id, cls.COLUMN_TYPE[inventory_type], False)
        selected_columns_from_database = []

        if profile_id:
            for c in apps.get_model('seed', 'ColumnListSettingColumn').objects.filter(
                column_list_setting_id=profile_id
            ).order_by('order'):
                # find the items from the columns_from_database object and return only the ones that are in the
                # selected profile
                for c_db in columns_from_database:
                    if "%s_%s" % (c.column.column_name, c.column.id) == c_db['name']:
                        selected_columns_from_database.append(c_db)
                        column_ids.append(c_db['id'])
                        column_name_mappings[c_db['name']] = c_db['display_name']
        else:
            # return all the columns for the organization
            for c in columns_from_database:
                column_ids.append(c['id'])
                column_name_mappings[c['name']] = c['display_name']
                selected_columns_from_database.append(c)

        return column_ids, column_name_mappings, selected_columns_from_database
