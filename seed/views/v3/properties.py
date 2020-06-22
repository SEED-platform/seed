"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from collections import namedtuple

from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from seed.decorators import ajax_request_class
from seed.models import (
    PropertyView,
    StatusLabel as Label,
)
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.labels import get_labels
from seed.utils.meters import PropertyMeterReadingsExporter


ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class PropertyViewSet(viewsets.ViewSet, OrgMixin):
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    _organization = None

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(required=True)],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'selected': ['integer'],
            },
            description='IDs for properties to be checked for which labels are applied.'
        )
    )
    @action(detail=False, methods=['POST'])
    def labels(self, request):
        """
        Returns a list of all labels where the is_applied field
        in the response pertains to the labels applied to property_view
        """
        labels = Label.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        super_organization = self.get_organization(request)
        # TODO: refactor to avoid passing request here
        return get_labels(request, labels, super_organization, 'property_view')

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'interval': 'string',
                'excluded_meter_ids': ['integer'],
            },
            required=['property_view_id', 'interval', 'excluded_meter_ids'],
            description='Properties:\n'
                        '- interval: one of "Exact", "Month", or "Year"\n'
                        '- excluded_meter_ids: array of meter IDs to exclude'
        )
    )
    @ajax_request_class
    @action(detail=True, methods=['POST'])
    def meter_usage(self, request, pk):
        body = dict(request.data)
        interval = body['interval']
        excluded_meter_ids = body['excluded_meter_ids']

        property_view = PropertyView.objects.get(pk=pk)
        property_id = property_view.property.id
        org_id = property_view.cycle.organization_id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]

        exporter = PropertyMeterReadingsExporter(property_id, org_id, excluded_meter_ids, scenario_ids=scenario_ids)

        return exporter.readings_and_column_defs(interval)
