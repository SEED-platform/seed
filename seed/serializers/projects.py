# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    Project, ProjectPropertyView, ProjectTaxLotView
)

STATUS_LOOKUP = {
    choice[0]: str(choice[1]).lower() for choice in Project.STATUS_CHOICES
}


class ProjectSerializer(serializers.ModelSerializer):

    last_modified_by = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_compliance = serializers.SerializerMethodField()
    compliance_type = serializers.SerializerMethodField()
    deadline_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'slug', 'modified', 'last_modified_by',
            'description', 'status', 'is_compliance',
            'compliance_type', 'deadline_date', 'end_date',
            'property_count', 'taxlot_count'
        )

    def get_last_modified_by(self, obj):
        last_modified_by = obj.last_modified_by
        return {
            'first_name': getattr(last_modified_by, 'first_name', None),
            'last_name': getattr(last_modified_by, 'last_name', None),
            'email': getattr(last_modified_by, 'email', None),
        }

    def get_compliance(self, obj):
        if not getattr(self, '_compliance', None):
            self._compliance = obj.get_compliance()
        return self._compliance

    def get_compliance_attr(self, obj, attr):
        return getattr(self.get_compliance(obj), attr, None)

    def get_compliance_type(self, obj):
        return self.get_compliance_attr(obj, 'compliance_type')

    def get_deadline_date(self, obj):
        return self.get_compliance_attr(obj, 'deadline_date')

    def get_end_date(self, obj):
        return self.get_compliance_attr(obj, 'end_date')

    def get_is_compliance(self, obj):
        return self.get_compliance(obj) is not None

    def get_status(self, obj):
        return STATUS_LOOKUP[obj.status]


class ProjectPropertyViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectPropertyView


class ProjectTaxLotViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectTaxLotView
