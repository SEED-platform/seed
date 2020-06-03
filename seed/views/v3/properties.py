from rest_framework import viewsets
from rest_framework.decorators import action
from seed.utils.api_schema import AutoSchemaHelper
from collections import namedtuple
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import (
    response,
    status,
)
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from seed.filters import InventoryFilterBackend
from seed.models import StatusLabel as Label
from seed.serializers.labels import LabelSerializer

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class PropertiesSchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('POST', 'labels'): [self.org_id_field()]
        }

class PropertyLabelsViewSet(viewsets.ViewSet):
    swagger_schema = PropertiesSchema
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    _organization = None

    def get_parent_organization(self):
        org = self.get_organization()
        if org.is_parent:
            return org
        else:
            return org.parent_org

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

        labels = Label.objects.filter(
            super_organization=self.get_parent_organization()
        ).order_by("name").distinct()
        return labels

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.get_organization()
        inventory = InventoryFilterBackend().filter_queryset(
            request=self.request,
        )
        kwargs['inventory'] = inventory
        return super().get_serializer(*args, **kwargs)

    def _get_labels(self, request):
        qs = self.get_queryset()
        super_organization = self.get_organization()
        inventory = InventoryFilterBackend().filter_queryset(
            request=self.request,
        )
        results = [
            LabelSerializer(
                q,
                super_organization=super_organization,
                inventory=inventory
            ).data for q in qs
        ]
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    @action(detail=False, methods=['POST'])
    def labels(self, request):
        """
        Api endpoint to list only labels applied to property inventory type
        ___
        """
        request.query_params._mutable = True
        request.query_params['inventory_type'] = 'property_view'
        request.query_params._mutable = False
        return self._get_labels(request)
