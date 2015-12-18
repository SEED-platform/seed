from django.core.exceptions import ObjectDoesNotExist

from rest_framework import viewsets
from rest_framework import generics
from rest_framework import response

from seed.decorators import (
    DecoratorMixin,
)
from seed.filters import (
    LabelFilterBackend,
    BuildingFilterBackend,
)
from seed.utils.api import (
    drf_api_endpoint,
)
from seed.models import (
    StatusLabel as Label,
    BuildingSnapshot,
    CanonicalBuilding,
)
from seed.serializers.labels import (
    LabelSerializer,
    UpdateBuildingLabelsSerializer,
)


class LabelViewSet(DecoratorMixin(drf_api_endpoint),
                   viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    queryset = Label.objects.none()
    filter_backends = (LabelFilterBackend,)

    _organization = None

    def get_organization(self):
        if self._organization is None:
            try:
                self._organization = self.request.user.orgs.get(
                    pk=self.request.query_params["organization_id"],
                )
            except (KeyError, ObjectDoesNotExist):
                self._organization = self.request.user.orgs.all()[0]
        return self._organization

    def get_queryset(self):
        return Label.objects.filter(
            super_organization=self.get_organization()
        ).order_by("name").distinct()

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.get_organization()
        building_snapshots = BuildingFilterBackend().filter_queryset(
            request=self.request,
            queryset=BuildingSnapshot.objects.all(),
            view=self,
        )
        kwargs['building_snapshots'] = building_snapshots
        return super(LabelViewSet, self).get_serializer(*args, **kwargs)


class UpdateBuildingLabelsAPIView(generics.GenericAPIView):
    filter_backends = (BuildingFilterBackend,)
    queryset = BuildingSnapshot.objects.all()
    serializer_class = UpdateBuildingLabelsSerializer

    _organization = None

    def get_organization(self):
        if self._organization is None:
            try:
                self._organization = self.request.user.orgs.get(
                    pk=self.request.query_params["organization_id"],
                )
            except ObjectDoesNotExist:
                self._organization = self.request.user.orgs.all()[0]
        return self._organization

    def put(self, *args, **kwargs):
        """
        Updates label assignments to buildings.

        Payload::

            {
                "add_label_ids": {array}            Array of label ids to apply to selected buildings
                "remove_label_ids": {array}         Array of label ids to remove from selected buildings
                "buildings": {array}                Array of building ids to apply/remove labels. (this will be empty or null if select_all_checkbox is true),  # NOQA
                "select_all_checkbox": {boolean},   Whether select all checkbox was selected on building list
                "filter_params": {object}           A 'filter params' object containing key/value pairs for selected filters  # NOQA
                "org_id": {integer}                 The user's org ID
            }

        Returns::

            {
                'status': {string}                  'success' or 'error'
                'message': {string}                 Error message if status = 'error'
                'num_buildings_updated': {integer}  Number of buildings in queryset
            }

        """
        building_snapshots = self.filter_queryset(self.get_queryset())
        queryset = CanonicalBuilding.objects.filter(
            id__in=building_snapshots.values_list('canonical_building', flat=True),
        )
        serializer = self.get_serializer(
            data=self.request.data,
            queryset=queryset,
            super_organization=self.get_organization(),
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return response.Response({
            "num_buildings_updated": building_snapshots.count(),
        })
