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
from django.db.utils import IntegrityError


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

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    def create(self, request):
        """
        create data_logger
        """
        org_id = self.get_organization(request)
        property_view_id = request.GET['property_view_id']

        body = dict(request.data)
        display_name = body['display_name']
        location_identifier = body.get("location_identifier")

        property_view = PropertyView.objects.get(
            pk=property_view_id,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id

        data_logger = DataLogger(
            property_id=property_id,
            display_name=display_name,
            location_identifier=location_identifier
        )

        try:
            data_logger.save()
        except IntegrityError:
            result = {
                'status': 'error',
                'message': f'the name {display_name} is not unique.'
            }
        else:
            result = {
                'id': data_logger.id,
                'display_name': data_logger.display_name,
                'location_identifier': data_logger.location_identifier,
            }

        return result
