# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
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
    VIEW_LOCATION_TYPES,
    VIEW_LIST_INVENTORY_TYPE
)
from seed.lib.superperms.orgs.models import Organization
from seed.serializers.base import ChoiceField


class ColumnListSettingColumnSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='column.id')
    column_name = serializers.ReadOnlyField(source='column.column_name')
    table_name = serializers.ReadOnlyField(source='column.table_name')

    class Meta:
        model = ColumnListSettingColumn
        fields = ('id', 'pinned', 'order', 'column_name', 'table_name',)


class ColumnListSettingSerializer(serializers.ModelSerializer):
    columns = ColumnListSettingColumnSerializer(source='columnlistsettingcolumn_set', read_only=True, many=True)
    settings_location = ChoiceField(choices=VIEW_LOCATION_TYPES)
    inventory_type = ChoiceField(choices=VIEW_LIST_INVENTORY_TYPE)

    class Meta:
        model = ColumnListSetting
        fields = ('id', 'name', 'settings_location', 'inventory_type', 'columns')

    def update(self, instance, validated_data):
        # remove the relationships -- to be added again in next step
        ColumnListSettingColumn.objects.filter(column_list_setting_id=instance.id).delete()
        for column in self.initial_data.get('columns', []):
            column_id = column.get('id')
            order = column.get('order')
            pinned = column.get('pinned')
            ColumnListSettingColumn(
                column_list_setting=instance, column_id=column_id, pinned=pinned, order=order
            ).save()

        instance.__dict__.update(**validated_data)
        instance.save()

        return instance

    def create(self, validated_data):
        cls = ColumnListSetting.objects.create(**validated_data)
        if 'columns' in self.initial_data:
            for column in self.initial_data.get('columns', []):
                # At this point the column will exist for the organization based on the validation
                # step
                column_id = column.get('id')
                order = column.get('order')
                pinned = column.get('pinned')
                ColumnListSettingColumn(
                    column_list_setting=cls, column_id=column_id, pinned=pinned, order=order
                ).save()
        cls.save()

        return cls

    def validate(self, data):
        # run some custom validation on the Columns data to make sure that the columns exist are
        # part of the org
        if 'columns' in self.initial_data:
            request = self.context.get('request', None)

            # Org ID is in the request param
            org = Organization.objects.get(id=request.query_params['organization_id'])
            for column in self.initial_data.get('columns', []):
                # note that the org is the user's existing org, not the parent org!
                if not Column.objects.filter(pk=column.get('id'), organization_id=org.pk).exists():
                    raise ValidationError("Column does not exist for organization, column id: %s" % column.get('id'))

        return super().validate(data)
