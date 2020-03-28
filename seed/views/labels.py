# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from collections import namedtuple

from django.apps import apps
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import (
    response,
    status,
    viewsets
)
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from seed.decorators import DecoratorMixin
from seed.filters import (
    LabelFilterBackend,
    InventoryFilterBackend,
)
from seed.models import (
    StatusLabel as Label,
    PropertyView,
    TaxLotView,
)
from seed.serializers.labels import (
    LabelSerializer,
)
from seed.utils.api import drf_api_endpoint

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class LabelViewSet(DecoratorMixin(drf_api_endpoint), viewsets.ModelViewSet):
    """API endpoint for viewing and creating labels.

            Returns::
                [
                    {
                        'id': Label's primary key
                        'name': Name given to label
                        'color': Color of label,
                        'organization_id': Id of organization label belongs to,
                        'is_applied': Will be empty array if not applied to property/taxlots
                    }
                ]

    ---
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

    @action(detail=False, methods=['POST'])
    def filter(self, request):
        return self._get_labels(request)

    def list(self, request):
        return self._get_labels(request)


class UpdateInventoryLabelsAPIView(APIView):
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    inventory_models = {'property': PropertyView, 'taxlot': TaxLotView}
    errors = {
        'disjoint': ErrorState(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'add_label_ids and remove_label_ids cannot contain elements in common'
        ),
        'missing_org': ErrorState(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'missing organization_id'
        )
    }

    @property
    def models(self):
        """
        Exposes Django's internal models for join table.

        Used for bulk_create operations.
        """
        return {
            'property': apps.get_model('seed', 'PropertyView_labels'),
            'taxlot': apps.get_model('seed', 'TaxLotView_labels')
        }

    def get_queryset(self, inventory_type, organization_id):
        Model = self.models[inventory_type]
        return Model.objects.filter(
            statuslabel__super_organization_id=organization_id
        )

    def get_label_desc(self, add_label_ids, remove_label_ids):
        return Label.objects.filter(
            pk__in=add_label_ids + remove_label_ids
        ).values('id', 'color', 'name')

    def get_inventory_id(self, q, inventory_type):
        return getattr(q, "{}view_id".format(inventory_type))

    def exclude(self, qs, inventory_type, label_ids):
        exclude = {label: [] for label in label_ids}
        for q in qs:
            if q.statuslabel_id in label_ids:
                inventory_id = self.get_inventory_id(q, inventory_type)
                exclude[q.statuslabel_id].append(inventory_id)
        return exclude

    def filter_by_inventory(self, qs, inventory_type, inventory_ids):
        if inventory_ids:
            filterdict = {
                "{}view__pk__in".format(inventory_type): inventory_ids
            }
            qs = qs.filter(**filterdict)
        return qs

    def label_factory(self, inventory_type, label_id, inventory_id):
        Model = self.models[inventory_type]

        # Ensure the the label org and inventory org are the same
        inventory_parent_org_id = getattr(Model, "{}view".format(inventory_type)).get_queryset().get(pk=inventory_id)\
            .cycle.organization.get_parent().id
        label_super_org_id = Model.statuslabel.get_queryset().get(pk=label_id).super_organization_id
        if inventory_parent_org_id == label_super_org_id:
            create_dict = {
                'statuslabel_id': label_id,
                "{}view_id".format(inventory_type): inventory_id
            }

            return Model(**create_dict)
        else:
            raise IntegrityError(
                'Label with super_organization_id={} cannot be applied to a record with parent '
                'organization_id={}.'.format(
                    label_super_org_id,
                    inventory_parent_org_id
                )
            )

    def add_labels(self, qs, inventory_type, inventory_ids, add_label_ids):
        added = []
        if add_label_ids:
            model = self.models[inventory_type]
            inventory_model = self.inventory_models[inventory_type]
            exclude = self.exclude(qs, inventory_type, add_label_ids)
            inventory_ids = inventory_ids if inventory_ids else [
                m.pk for m in inventory_model.objects.all()
            ]
            new_inventory_labels = [
                self.label_factory(inventory_type, label_id, pk)
                for label_id in add_label_ids for pk in inventory_ids
                if pk not in exclude[label_id]
            ]
            model.objects.bulk_create(new_inventory_labels)
            added = [
                self.get_inventory_id(m, inventory_type)
                for m in new_inventory_labels
            ]
        return added

    def remove_labels(self, qs, inventory_type, remove_label_ids):
        removed = []
        if remove_label_ids:
            rqs = qs.filter(
                statuslabel_id__in=remove_label_ids
            )
            removed = [self.get_inventory_id(q, inventory_type) for q in rqs]
            rqs.delete()
        return removed

    def put(self, request, inventory_type):
        """
        Updates label assignments to inventory items.

        Payload::

            {
                "add_label_ids": {array}        Array of label ids to add
                "remove_label_ids": {array}     Array of label ids to remove
                "inventory_ids": {array}        Array property/taxlot ids
                "organization_id": {integer}    The user's org ID
            }

        Returns::

            {
                'status': {string}              'success' or 'error'
                'message': {string}             Error message if error
                'num_updated': {integer}        Number of properties/taxlots updated
                'labels': [                     List of labels affected.
                    {
                        'color': {string}
                        'id': {int}
                        'label': {'string'}
                        'name': {string}
                    }...
                ]
            }

        """
        add_label_ids = request.data.get('add_label_ids', [])
        remove_label_ids = request.data.get('remove_label_ids', [])
        inventory_ids = request.data.get('inventory_ids', None)
        organization_id = request.query_params['organization_id']
        error = None
        # ensure add_label_ids and remove_label_ids are different
        if not set(add_label_ids).isdisjoint(remove_label_ids):
            error = self.errors['disjoint']
        elif not organization_id:
            error = self.errors['missing_org']
        if error:
            result = {
                'status': 'error',
                'message': str(error)
            }
            status_code = error.status_code
        else:
            qs = self.get_queryset(inventory_type, organization_id)
            qs = self.filter_by_inventory(qs, inventory_type, inventory_ids)
            removed = self.remove_labels(qs, inventory_type, remove_label_ids)
            added = self.add_labels(qs, inventory_type, inventory_ids, add_label_ids)
            num_updated = len(set(added).union(removed))
            labels = self.get_label_desc(add_label_ids, remove_label_ids)
            result = {
                'status': 'success',
                'num_updated': num_updated,
                'labels': labels
            }
            status_code = status.HTTP_200_OK
        return response.Response(result, status=status_code)
