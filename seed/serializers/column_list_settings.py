# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import (
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
)
from seed.serializers.base import ChoiceField
from seed.utils.api import OrgValidator, OrgValidateMixin, OrgMixin

COLUMN_VALIDATOR = OrgValidator('column', 'organization_id')


class ColumnListSettingColumnSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='column.id')
    column_name = serializers.ReadOnlyField(source='column.column_name')
    table_name = serializers.ReadOnlyField(source='column.table_name')

    class Meta:
        model = ColumnListSettingColumn
        fields = ('id', 'pinned', 'order', 'column_name', 'table_name',)


class ColumnListSettingSerializer(OrgMixin, OrgValidateMixin, serializers.ModelSerializer):
    columns = ColumnListSettingColumnSerializer(source="columnlistsettingcolumn_set", read_only=True, many=True)
    settings_location = ChoiceField(choices=ColumnListSetting.VIEW_LOCATION_TYPES)
    inventory_type = ChoiceField(choices=ColumnListSetting.VIEW_LIST_INVENTORY_TYPE)
    org_validators = [COLUMN_VALIDATOR]

    class Meta:
        model = ColumnListSetting
        fields = ('id', 'name', 'settings_location', 'inventory_type', 'columns')

    def update(self, instance, validated_data):
        # remove the relationships -- to be added again in next step
        ColumnListSettingColumn.objects.filter(column_list_setting_id=instance.id).delete()
        for column in self.initial_data.get("columns"):
            column_id = column.get("id")
            order = column.get("order")
            pinned = column.get("pinned")
            ColumnListSettingColumn(column_list_setting=instance, column_id=column_id, pinned=pinned,
                                    order=order).save()

        instance.__dict__.update(**validated_data)
        instance.save()

        return instance

    def create(self, validated_data):
        cls = ColumnListSetting.objects.create(**validated_data)
        if "columns" in self.initial_data:
            for column in self.initial_data.get("columns"):
                # At this point the column will exist for the organization based on the validation step
                column_id = column.get("id")
                order = column.get("order")
                pinned = column.get("pinned")
                ColumnListSettingColumn(column_list_setting=cls, column_id=column_id, pinned=pinned, order=order).save()
        cls.save()

        return cls

    def validate(self, data):
        # run some custom validation on the Columns data to make sure that the columns exist are are part of the org
        if "columns" in self.initial_data:
            request = self.context.get('request', None)
            org_id = self.get_organization(request)
            for column in self.initial_data.get("columns"):
                if not Column.objects.filter(pk=column.get("id"), organization_id=org_id).exists():
                    raise ValidationError('Column does not exist for organization, column id: %s' % column.get("id"))

        return super(ColumnListSettingSerializer, self).validate(data)
