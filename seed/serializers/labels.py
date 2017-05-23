# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    StatusLabel as Label,
    Property, TaxLot, PropertyView, TaxLotView)


class LabelSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(
        source="super_organization",
        read_only=True,
    )
    is_applied = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        """
        Labels always exist in the context of the organization they are
        assigned to.  This serializer requires that the `super_organization`
        for the label be passed into the serializer during initialization so
        that uniqueness constraints involving the `super_organization` can be
        validated by the serializer.

        """
        if 'super_organization' not in kwargs:
            return
        super_organization = kwargs.pop('super_organization')
        self.inventory = kwargs.pop('inventory')
        super(LabelSerializer, self).__init__(*args, **kwargs)
        if getattr(self, 'initial_data', None):
            self.initial_data['super_organization'] = super_organization.pk

    class Meta:
        fields = (
            "id",
            "name",
            "color",
            "organization_id",
            "super_organization",
            "is_applied",
        )
        extra_kwargs = {
            "super_organization": {"write_only": True},
        }
        model = Label

    def get_is_applied(self, obj):
        filtered_result = False
        if self.inventory:
            result = self.inventory.filter(
                labels=obj,
            ).values_list('id', flat=True)

            # Limit results to ones attached to view
            if self.inventory.model is Property:
                filtered_result = PropertyView.objects.filter(property_id__in=result).values_list('property_id', flat=True)
            elif self.inventory.model is TaxLot:
                filtered_result = TaxLotView.objects.filter(taxlot_id__in=result).values_list('taxlot_id', flat=True)

        return filtered_result
