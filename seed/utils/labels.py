"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author
"""
from seed.filters import (
    InventoryFilterBackendWithInvType,
)
from seed.serializers.labels import (
    LabelSerializer,
)
from rest_framework import (
    response,
    status,
)


def _get_labels(request, qs, super_organization, inv_type):
    inventory = InventoryFilterBackendWithInvType().filter_queryset_with_inv(
        request=request, inv_type=inv_type
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
