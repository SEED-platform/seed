# !/usr/bin/env python
# encoding: utf-8
from collections import namedtuple

from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response, status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    InventoryGroup,
    InventoryGroupMapping,
    Property,
    PropertyView,
    TaxLot,
    TaxLotView
)
from seed.serializers.inventory_groups import InventoryGroupMappingSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class InventoryGroupMappingViewSet(viewsets.ViewSet):
    model = InventoryGroupMapping
    serializer_class = InventoryGroupMappingSerializer
    inventory_models = {'property': Property, 'tax_lot': TaxLot}

    errors = {
        'disjoint': ErrorState(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'add_group_ids and remove_group_ids cannot contain elements in common'
        ),
        'missing_org': ErrorState(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'missing organization_id'
        )
    }

    def combine_group_ids(self, add_group_ids, remove_group_ids):
        """
        Returns set of both added group ids and removed group ids
        """
        return InventoryGroup.objects.filter(
            pk__in=add_group_ids + remove_group_ids
        ).values('id')

    def group_factory(self, inventory_type, group_id, inventory_id):
        """
        For each inventory id, check org correctness & then match group id with inv id (and prop/taxlot type)
        """
        inventory_model = self.inventory_models[inventory_type]

        inventory_org_id = inventory_model.objects.get(pk=inventory_id).organization.id
        group_org_id = InventoryGroup.objects.get(pk=group_id).organization.id

        if inventory_org_id == group_org_id:
            create_dict = {
                'group_id': group_id,
                "{}_id".format(inventory_type): inventory_id
            }
            return InventoryGroupMapping(**create_dict)

        else:
            raise IntegrityError(
                'Group with organization_id={} cannot be applied to a record with '
                'organization_id={}.'.format(
                    group_org_id,
                    inventory_org_id
                )
            )

    def get_inventory_id(self, q, inventory_type):
        return getattr(q, "{}_id".format(inventory_type))

    def exclude(self, qs, inventory_type, group_ids):
        exclude = {group: [] for group in group_ids}
        for q in qs:
            if q.group_id in group_ids:
                inventory_id = self.get_inventory_id(q, inventory_type)
                exclude[q.group_id].append(inventory_id)
        return exclude

    def add_groups(self, qs, inventory_type, inventory_ids, add_group_ids):
        """
        Adds items to groups in GroupMappings and returns list of inventory ids that were added.
        """
        added = []
        if add_group_ids:
            model = InventoryGroupMapping
            inventory_model = self.inventory_models[inventory_type]
            exclude = self.exclude(qs, inventory_type, add_group_ids)
            inventory_ids = inventory_ids if inventory_ids else [
                m.pk for m in inventory_model.objects.all()
            ]
            new_inventory_groups = [
                self.group_factory(inventory_type, group_id, pk)
                for group_id in add_group_ids for pk in inventory_ids
                if pk not in exclude[group_id]
            ]
            model.objects.bulk_create(new_inventory_groups)
            added = [
                self.get_inventory_id(m, inventory_type)
                for m in new_inventory_groups
            ]
        return added

    def remove_groups(self, qs, inventory_type, inventory_ids, remove_group_ids):
        """
        Removes items from groups in GroupMappings and returns list of inventory ids that were removed.
        """
        removed = []
        if remove_group_ids:
            if inventory_type == 'property':
                rqs = qs.filter(
                    group_id__in=remove_group_ids,
                    property__in=inventory_ids
                )
                removed = [self.get_inventory_id(q, inventory_type) for q in rqs]
                rqs.delete()
            elif inventory_type == 'tax_lot':
                rqs = qs.filter(
                    group_id__in=remove_group_ids,
                    tax_lot__in=inventory_ids
                )
                removed = [self.get_inventory_id(q, inventory_type) for q in rqs]
                rqs.delete()

        return removed

    def filter_by_inventory(self, qs, inventory_type, inventory_ids):
        """
        Returns rows in GroupMapping that match inventory item ids given
        """
        if inventory_type == 'property':
            qs = qs.filter(property__in=inventory_ids)
        elif inventory_type == 'tax_lot':
            qs = qs.filter(tax_lot__in=inventory_ids)
        return qs

    def get_queryset_for_inventory_type(self, inventory_type):
        """
        Returns all rows in GroupMapping of a certain inventory_type.
        """
        if inventory_type == 'property':
            mappings = InventoryGroupMapping.objects.filter(
                property__isnull=False
            ).order_by("group_id")
        else:
            mappings = InventoryGroupMapping.objects.filter(
                tax_lot__isnull=False
            ).order_by("group_id")
        return mappings

    def get_inventory_ids(self, inventory_type, inventory_ids):
        """
        Takes property_view/taxlot_view ids and returns property/taxlot ids
        """
        ids = []
        if inventory_type == 'property':
            ids = PropertyView.objects.filter(
                pk__in=inventory_ids
            ).order_by('id').values_list('property_id', flat=True)
        else:
            ids = TaxLotView.objects.filter(
                pk__in=inventory_ids
            ).order_by('id').values_list('taxlot_id', flat=True)
        return ids

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {'add_group_ids': ['integer'],
             'remove_group_ids': ['integer'],
             'inventory_ids': ['integer'],
             'inventory_type': 'string'
             }
        ),
        responses={
            200: AutoSchemaHelper.schema_factory({
                'status': 'string',
                'message': 'string',
                'num_updated': 'integer',
                'inventory_groups': ['integer']
            })
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['PUT'])
    def put(self, request):
        """
            Adds or removes group mappings.
        """
        add_group_ids = request.data.get('add_group_ids', [])
        remove_group_ids = request.data.get('remove_group_ids', [])
        inventory_ids = request.data.get('inventory_ids', None)
        inventory_type = request.data.get('inventory_type', None)
        organization = request.query_params['organization_id']
        error = None

        if not set(add_group_ids).isdisjoint(remove_group_ids):
            error = self.errors['disjoint']
        elif not organization:
            error = self.errors['missing_org']
        if error:
            result = {
                'status': 'error',
                'message': str(error)
            }
            status_code = error.status_code
        else:
            # get ids from view_ids
            inventory_ids = self.get_inventory_ids(inventory_type, inventory_ids)

            qs = self.get_queryset_for_inventory_type(inventory_type)
            qs = self.filter_by_inventory(qs, inventory_type, inventory_ids)

            removed = self.remove_groups(qs, inventory_type, inventory_ids, remove_group_ids)
            added = self.add_groups(qs, inventory_type, inventory_ids, add_group_ids)

            num_updated = len(set(added).union(removed))
            groups = self.combine_group_ids(add_group_ids, remove_group_ids)
            result = {
                'status': 'success',
                'num_updated': num_updated,
                'inventory_groups': groups
            }
            status_code = status.HTTP_200_OK
        return response.Response(result, status=status_code)
