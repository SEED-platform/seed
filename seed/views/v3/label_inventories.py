# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Piper Merriam <pmerriam@quickleft.com>'
"""
from collections import namedtuple

from django.apps import apps
from django.db import IntegrityError
from rest_framework import (
    response,
    status,
)
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    StatusLabel as Label,
    PropertyView,
    TaxLotView,
)
from seed.utils.api_schema import AutoSchemaHelper

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class LabelInventoryViewSet(APIView):
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
        ),
        'missing_inventory_ids': ErrorState(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'inventory_ids cannot be undefined or empty'
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
        """Returns a mapping of label IDs to inventories which already have that
        label applied

        :param qs: QuerySet of inventory labels
        :param inventory_type: string
        :param label_ids: list
        :return: dict
        """
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
        inventory_views = getattr(Model, "{}view".format(inventory_type)).get_queryset()
        inventory_parent_org_id = inventory_views.get(pk=inventory_id)\
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
        """Add labels in the add_label_ids list to inventory

        :param qs: QuerySet of inventory labels to exclude
        :param inventory_type: string
        :param inventory_ids: list
        :param add_label_ids: list
        """
        added = []
        if add_label_ids:
            model = self.models[inventory_type]
            exclude = self.exclude(qs, inventory_type, add_label_ids)
            new_inventory_labels = []
            for label_id in add_label_ids:
                for pk in inventory_ids:
                    if pk not in exclude[label_id]:
                        new_inventory_label = self.label_factory(inventory_type, label_id, pk)
                        new_inventory_labels.append(new_inventory_label)
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'add_label_ids': ['integer'],
                'remove_label_ids': ['integer'],
                'inventory_ids': ['integer'],
            },
            required=['inventory_ids'],
            description='Properties:\n'
                        '- add_label_ids: label ids to add to the inventories\n'
                        '- remove_label_ids: label ids to remove from the inventories\n'
                        '- inventory_ids: List of inventory IDs'
        )
    )
    @has_perm_class('can_modify_data')
    def put(self, request, inventory_type):
        """
        Updates label assignments to inventory items.

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
        inventory_ids = request.data.get('inventory_ids', [])
        organization_id = request.query_params['organization_id']
        error = None
        # ensure add_label_ids and remove_label_ids are different
        if not set(add_label_ids).isdisjoint(remove_label_ids):
            error = self.errors['disjoint']
        elif not organization_id:
            error = self.errors['missing_org']
        elif len(inventory_ids) == 0:
            error = self.errors['missing_inventory_ids']
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
