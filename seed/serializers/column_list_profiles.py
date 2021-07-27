# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from seed.models.derived_columns import DerivedColumn
from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import (
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    VIEW_LOCATION_TYPES,
    VIEW_LIST_INVENTORY_TYPE
)
from seed.lib.superperms.orgs.models import Organization
from seed.serializers.base import ChoiceField


class ColumnListProfileColumnSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='column.id')
    order = serializers.IntegerField()
    pinned = serializers.BooleanField()
    column_name = serializers.CharField(source='column.column_name')
    table_name = serializers.CharField(source='column.table_name')

    class Meta:
        model = ColumnListProfileColumn
        fields = ('id', 'pinned', 'order', 'column_name', 'table_name',)


class ColumnListProfileDerivedColumnSerializer(serializers.ModelSerializer):
    column_name = serializers.CharField(source='name', read_only=True)
    table_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DerivedColumn
        fields = ('id', 'column_name', 'table_name',)

    def get_table_name(self, obj):
        return DerivedColumn.INVENTORY_TYPE_TO_CLASS.get(obj.inventory_type).__name__


class ColumnListProfileSerializer(serializers.ModelSerializer):
    columns = ColumnListProfileColumnSerializer(source='columnlistprofilecolumn_set', many=True)
    derived_columns = ColumnListProfileDerivedColumnSerializer(many=True)
    profile_location = ChoiceField(choices=VIEW_LOCATION_TYPES)
    inventory_type = ChoiceField(choices=VIEW_LIST_INVENTORY_TYPE)

    class Meta:
        model = ColumnListProfile
        fields = ('id', 'name', 'profile_location', 'inventory_type', 'columns', 'derived_columns')

    def update(self, instance, validated_data):
        # remove the relationships -- to be added again in next step
        ColumnListProfileColumn.objects.filter(column_list_profile_id=instance.id).delete()
        for column in self.initial_data.get('columns', []):
            column_id = column.get('id')
            order = column.get('order')
            pinned = column.get('pinned')
            ColumnListProfileColumn(
                column_list_profile=instance, column_id=column_id, pinned=pinned, order=order
            ).save()

        instance.derived_columns.clear()
        for derived_column in self.initial_data.get('derived_columns', []):
            instance.derived_columns.add(derived_column.get('id'))

        instance.__dict__.update(**validated_data)
        instance.save()

        return instance

    def create(self, validated_data):
        # Remove *reformatted* ColumnListSettingColumn data, use unformatted initial_data later.
        del validated_data['columnlistprofilecolumn_set']
        del validated_data['derived_columns']

        # Add the already-validated organization_id
        validated_data['organization_id'] = self.context.get('request', None).query_params['organization_id']

        cls = ColumnListProfile.objects.create(**validated_data)
        if 'columns' in self.initial_data:
            for column in self.initial_data.get('columns', []):
                # At this point the column will exist for the organization based on the validation
                # step
                column_id = column.get('id')
                order = column.get('order')
                pinned = column.get('pinned')
                ColumnListProfileColumn(
                    column_list_profile=cls, column_id=column_id, pinned=pinned, order=order
                ).save()

        for derived_column in self.initial_data.get('derived_columns', []):
            cls.derived_columns.add(derived_column.get('id'))

        cls.save()

        return cls

    def validate(self, data):
        # run some custom validation on the Columns data to make sure that the columns exist are
        # part of the org
        if 'columns' in self.initial_data or 'derived_columns' in self.initial_data:
            request = self.context.get('request', None)

            # Org ID is in the request param
            org = Organization.objects.get(id=request.query_params['organization_id'])
            for column in self.initial_data.get('columns', []):
                # note that the org is the user's existing org, not the parent org!
                if not Column.objects.filter(pk=column.get('id'), organization_id=org.pk).exists():
                    raise ValidationError(f"Column does not exist for organization, column id: {column.get('id')}")

            for derived_column in self.initial_data.get('derived_columns', []):
                # note that the org is the user's existing org, not the parent org!
                if not DerivedColumn.objects.filter(pk=derived_column.get('id'), organization_id=org.pk).exists():
                    raise ValidationError(f"Derived column does not exist for organization, derived column id: {derived_column.get('id')}")

        return super().validate(data)
