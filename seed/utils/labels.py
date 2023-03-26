"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from rest_framework import response, status

from seed import search
from seed.serializers.labels import LabelSerializer


def filter_labels_for_inv_type(request, inventory_type=None):
    """
    Method used to filter labels by inventory type and return is_applied inventory id's
    Method was initially built as a class defined function above to handle more parameters.
    """
    params = request.query_params.dict()
    # Since this is being passed in as a query string, the object ends up
    # coming through as a string.
    params['filter_params'] = json.loads(params.get('filter_params', '{}'))

    # If cycle_id is passed with an inventory_type limit the inventory filter
    cycle_id = params.get('cycle_id', None) if inventory_type is not None else None

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
    if 'selected' in request.data:
        # Return labels limited to the 'selected' list.  Otherwise, if selected is empty, return all
        if request.data['selected']:
            return queryset.filter(
                id__in=request.data['selected'],
            )
    return queryset


def get_labels(request, qs, super_organization, inv_type):
    inventory = filter_labels_for_inv_type(
        request=request, inventory_type=inv_type
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
