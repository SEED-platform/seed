# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from rest_framework import serializers

from seed.models import (
    Column,
    ColumnListSetting,
)
from seed.utils.api import OrgValidator, OrgValidateMixin, OrgMixin

COLUMN_VALIDATOR = OrgValidator('column', 'organization_id')


class ColumnListSettingColumnField(OrgMixin, serializers.PrimaryKeyRelatedField):
    """Make sure to only return the columns that are part of the organization"""
    def get_queryset(self):
        request = self.context.get('request', None)
        queryset = super(ColumnListSettingColumnField, self).get_queryset()
        if not request or not queryset:
            return None
        return queryset.filter(organization_id=self.get_organization(request))


class ColumnListSettingSerializer(OrgValidateMixin, serializers.ModelSerializer):
    columns = ColumnListSettingColumnField(many=True, queryset=Column.objects)
    org_validators = [COLUMN_VALIDATOR]

    class Meta:
        model = ColumnListSetting
        fields = (
            'id', 'name', 'organization_id', 'columns'
        )
