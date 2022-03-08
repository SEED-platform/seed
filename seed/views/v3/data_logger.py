"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import viewsets
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (PropertyView,
                         DataLogger)
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.api import OrgMixin


class DataLoggerViewSet(viewsets.ViewSet, OrgMixin):
    raise_exception = True

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        Retrieves data_loggers for the property
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET['property_view_id']

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        res = []
        for data_logger in DataLogger.objects.filter(property_id=property_id):
            res.append({
                'id': data_logger.id,
                'display_name': data_logger.display_name,
                'location_identifier': data_logger.location_identifier,
            })

        return res
