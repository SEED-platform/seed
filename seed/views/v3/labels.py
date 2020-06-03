

# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from collections import namedtuple
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import (
    response,
    status,
)
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import DecoratorMixin
from seed.filters import (
    LabelFilterBackend,
    InventoryFilterBackend,
)
from seed.models import (
    StatusLabel as Label,
)
from seed.serializers.labels import (
    LabelSerializer,
)
from seed.utils.api import drf_api_endpoint
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class LabelViewSet(DecoratorMixin(drf_api_endpoint), SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """
    retrieve:
        Return a label instance by pk if it is within user`s specified org.

    list:
        Return all labels available to user through user`s specified org.

    create:
        Create a new label within user`s specified org.

    delete:
        Remove an existing label.

    update:
        Update a label record.
    """
    serializer_class = LabelSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser, FormParser)
    queryset = Label.objects.none()
    filter_backends = (LabelFilterBackend,)
    pagination_class = None
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

    def list(self, request):
        """
        Returns a list of all labels
        """
        return self._get_labels(request)
