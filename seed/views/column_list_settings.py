# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
"""

from seed.models import (
    ColumnListSetting
)

from seed.serializers.column_list_settings import (
    ColumnListSettingSerializer,
)

from seed.utils.viewsets import (
    SEEDOrgCreateUpdateModelViewSet
)


class ColumnListingViewSet(SEEDOrgCreateUpdateModelViewSet):
    """
    API endpoint for returning Column List Settings

    create:
        Create a new list setting. The list of columns is an array of column primary keys. If using Swagger, then
        this will be enters as a list with returns between each primary key.
    """
    serializer_class = ColumnListSettingSerializer
    model = ColumnListSetting
