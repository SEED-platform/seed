from rest_framework import fields
from rest_framework import serializers

from seed.models import (
    StatusLabel as Label,
    CanonicalBuilding,
)


class LabelSerializer(serializers.ModelSerializer):
    organization_id = serializers.PrimaryKeyRelatedField(
        source="super_organization",
        read_only=True,
    )

    def __init__(self, *args, **kwargs):
        """
        Labels always exist in the context of the organization they are
        assigned to.  This serializer requires that the `super_organization`
        for the label be passed into the serializer during initialization so
        that uniqueness constraints involving the `super_organization` can be
        validated by the serializer.

        """
        super_organization = kwargs.pop('super_organization')
        super(LabelSerializer, self).__init__(*args, **kwargs)
        if getattr(self, 'initial_data', None):
            self.initial_data['super_organization'] = super_organization.pk

    class Meta:
        fields = ("id", "name", "color", "organization_id", "super_organization")
        extra_kwargs = {
            "super_organization": {"write_only": True},
        }
        model = Label


class UpdateBuildingLabelsSerializer(serializers.Serializer):
    add_label_ids = serializers.ListSerializer(
        child=fields.IntegerField(),
        allow_empty=True,
    )
    remove_label_ids = serializers.ListSerializer(
        child=fields.IntegerField(),
        allow_empty=True,
    )
    selected_buildings = serializers.ListSerializer(
        child=fields.IntegerField(),
        allow_empty=True,
    )
    select_all_checkbox = fields.BooleanField()

    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.pop('queryset')
        self.super_organization = kwargs.pop('super_organization')
        super(UpdateBuildingLabelsSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        if validated_data['select_all_checkbox']:
            building_snapshots = self.queryset
        else:
            building_snapshots = self.queryset.filter(
                id__in=validated_data['selected_buildings'],
            )

        canonical_buildings = CanonicalBuilding.objects.filter(
            id__in=building_snapshots.values_list('canonical_building', flat=True),
        )

        if validated_data['add_label_ids']:
            add_labels = Label.objects.filter(
                pk__in=validated_data['add_label_ids'],
                super_organization=self.super_organization,
            )
        else:
            add_labels = []

        if validated_data['remove_label_ids']:
            remove_labels = Label.objects.filter(
                pk__in=validated_data['remove_label_ids'],
                super_organization=self.super_organization,
            )
        else:
            remove_labels = []

        for cb in canonical_buildings:
            cb.labels.remove(*remove_labels)
            cb.labels.add(*add_labels)

        return building_snapshots
