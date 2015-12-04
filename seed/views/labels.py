from rest_framework import viewsets
from rest_framework import generics
from rest_framework import response

from seed.decorators import (
    DecoratorMixin,
)
from seed.filters import (
    BuildingFilterBackend,
)
from seed.utils.api import (
    drf_api_endpoint,
)
from seed.models import (
    StatusLabel as Label,
    BuildingSnapshot,
)
from seed.serializers.labels import (
    LabelSerializer,
    UpdateBuildingLabelsSerializer,
)


class LabelViewSet(DecoratorMixin(drf_api_endpoint),
                   viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    queryset = Label.objects.none()

    def get_queryset(self):
        return Label.objects.filter(
            super_organization__in=self.request.user.orgs.all()
        ).order_by("name").distinct()

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.request.user.orgs.first()
        return super(LabelViewSet, self).get_serializer(*args, **kwargs)


class UpdateBuildingLabelsAPIView(generics.GenericAPIView):
    filter_backends = (BuildingFilterBackend,)
    queryset = BuildingSnapshot.objects.none()
    serializer_class = UpdateBuildingLabelsSerializer

    def put(self, *args, **kwargs):
        """
        Updates label assignments to buildings.

        Payload::

            {
                "add_label_ids": {array}            Array of label ids to apply to selected buildings
                "remove_label_ids": {array}         Array of label ids to remove from selected buildings
                "buildings": {array}                Array of building ids to apply/remove labels. (this will be empty or null if select_all_checkbox is true),
                "select_all_checkbox": {boolean},   Whether select all checkbox was selected on building list
                "filter_params": {object}           A 'filter params' object containing key/value pairs for selected filters
                "org_id": {integer}                 The user's org ID
            }

        Returns::

            {
                'status': {string}                  'success' or 'error'
                'message': {string}                 Error message if status = 'error'
                'num_buildings_updated': {integer}  Number of buildings in queryset
            }

        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(
            data=self.request.data,
            queryset=queryset,
            super_organization=self.request.user.orgs.first(),
        )
        serializer.is_valid(raise_exception=True)

        updated_buildings = serializer.save()

        return response.Response({
            "num_buildings_updated": updated_buildings.count(),
        })
