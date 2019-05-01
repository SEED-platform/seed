# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from seed.filters import ColumnListSettingFilterBackend
from seed.models import (
    ColumnListSetting
)
from seed.serializers.column_list_settings import (
    ColumnListSettingSerializer,
)
from seed.utils.api import OrgValidateMixin
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


class ColumnListingViewSet(OrgValidateMixin, SEEDOrgCreateUpdateModelViewSet):
    """
    API endpoint for returning Column List Settings

    create:
        Create a new list setting. The list of columns is an array of column primary keys. If using Swagger, then
        this will be enters as a list with returns between each primary key.

        JSON POST Example:

            {
                "name": "some new name 3",
                "settings_location": "List View Settings",
                "inventory_type": "Tax Lot",
                "columns": [
                    {"id": 1, "pinned": false, "order": 10},
                    {"id": 5, "pinned": true, "order": 14},
                    {"id": 7, "pinned": true, "order": 14}
                ]
            }

    """
    serializer_class = ColumnListSettingSerializer
    model = ColumnListSetting
    filter_backends = (ColumnListSettingFilterBackend,)
    pagination_class = None
    # force_parent = True  # Ideally the column list settings would inherit from the parent,
    # but not yet.
