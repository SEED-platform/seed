# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.utils.decorators import method_decorator

from seed.filtersets import PropertyViewFilterSet
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import AccessLevelInstance, PropertyView
from seed.serializers.properties import BriefPropertyViewSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet


@method_decorator(
    name='list',
    decorator=[has_perm_class('requires_viewer')]
)
@method_decorator(
    name='retrieve',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(property_view_id_kwarg="pk")]
)
@method_decorator(
    name='destroy',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(property_view_id_kwarg="pk")]
)
@method_decorator(
    name='update',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(property_view_id_kwarg="pk")]
)
@method_decorator(
    name='update',
    decorator=[has_perm_class('requires_viewer'), has_hierarchy_access(property_view_id_kwarg="pk")]
)
class PropertyViewViewSet(SEEDOrgModelViewSet):
    """PropertyViews API Endpoint

        Returns::
            {
                'status': 'success',
                'properties': [
                    {
                        'id': PropertyView primary key,
                        'property_id': id of associated Property,
                        'state': dict of associated PropertyState values (writeable),
                        'cycle': dict of associated Cycle values,
                        'certifications': dict of associated GreenAssessmentProperties values
                    }
                ]
            }


    retrieve:
        Return a PropertyView instance by pk if it is within specified org.

    list:
        Return all PropertyViews available to user through specified org.

    create:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Create a new PropertyView within user`s specified org.

    delete:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Remove an existing PropertyView.

    update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update a PropertyView record.

    partial_update:
        WARNING: using this endpoint is not recommended as it can cause unexpected results; please use the `properties/` endpoints instead. Update one or more fields on an existing PropertyView.
    """
    def get_queryset(self):
        if hasattr(self.request, 'access_level_instance_id'):
            access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

            return PropertyView.objects.filter(
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )

        else:
            return PropertyView.objects.filter(pk=-1)

    serializer_class = BriefPropertyViewSerializer
    pagination_class = None
    model = PropertyView
    filter_class = PropertyViewFilterSet
    orgfilter = 'property__organization_id'
    data_name = "property_views"
    queryset = PropertyView.objects.all()
