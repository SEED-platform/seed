# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from seed.filtersets import PropertyStateFilterSet
from seed.models import PropertyState
from seed.serializers.properties import PropertyStateSerializer
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet


class PropertyStateViewSet(SEEDOrgCreateUpdateModelViewSet):
    """Property State API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        all PropertyState fields/values
                    }
                ]
            }


    retrieve:
        Return a PropertyState instance by pk if it is within specified org.

    list:
        Return all PropertyStates available to user through specified org.

    create:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Create a new PropertyState within user`s specified org.

    delete:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Remove an existing PropertyState.

    update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update a PropertyState record.

    partial_update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update one or more fields on an existing PropertyState."""
    serializer_class = PropertyStateSerializer
    model = PropertyState
    filter_class = PropertyStateFilterSet
    data_name = "properties"
