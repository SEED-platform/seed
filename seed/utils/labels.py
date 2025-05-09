"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db.models import Q
from rest_framework import response, status

from seed import search
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.serializers.labels import LabelSerializer


def filter_labels_for_inv_type(request, inventory_type=None):
    """
    Method used to filter labels by inventory type and return is_applied inventory id's
    Method was initially built as a class defined function above to handle more parameters.
    """
    params = request.query_params.dict()
    # Since this is being passed in as a query string, the object ends up
    # coming through as a string.
    params["filter_params"] = json.loads(params.get("filter_params", "{}"))

    # If cycle_id is passed with an inventory_type limit the inventory filter
    cycle_id = params.get("cycle_id", None) if inventory_type is not None else None

    params = search.process_search_params(
        params=params,
        user=request.user,
        is_api_request=True,
    )
    queryset = search.inventory_search_filter_sort(
        inventory_type,
        params=params,
        user=request.user,
        cycle_id=cycle_id,
    )
    # Return labels limited to the 'selected' list.  Otherwise, if selected is empty, return all
    if request.data.get("selected"):
        return queryset.filter(
            id__in=request.data["selected"],
        )
    return queryset


def get_labels(request, qs, super_organization, inv_type):
    inventory = filter_labels_for_inv_type(request=request, inventory_type=inv_type)

    # filter by AH
    ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
    in_subtree = Q(
        **{
            f"{inv_type[:-5]}__access_level_instance__lft__gte": ali.lft,
            f"{inv_type[:-5]}__access_level_instance__rgt__lte": ali.rgt,
        }
    )
    inventory = inventory.filter(in_subtree)
    # remove labels that have been applied to goals
    if inv_type == "property_view":
        qs = qs.filter(propertyviewlabel__goal__isnull=True)

    # "is_applied" is a list of views with the label, but only the views that are in inventory.
    qs = qs.annotate(
        is_applied=ArrayAgg(f"{inv_type[:-5]}view", filter=Q(**{f"{inv_type[:-5]}view__in": inventory.values_list("id", flat=True)}))
    )

    results = LabelSerializer(qs, super_organization=super_organization, many=True).data

    status_code = status.HTTP_200_OK
    return response.Response(results, status=status_code)
