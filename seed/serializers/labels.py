from rest_framework import serializers

from seed.models import (
    StatusLabel as Label,
)


class LabelSerializer(serializers.ModelSerializer):
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
        fields = ("id", "name", "color", "super_organization")
        model = Label
