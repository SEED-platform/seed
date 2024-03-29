"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.models import EeejCejst
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class EEEJViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'tract_ids': ['string'],
            },
            description='An object containing IDs of census tracts to check their status as disadvantaged.',
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    'status': 'string',
                    'disadvantaged': ['string'],
                }
            )
        },
    )
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=['POST'])
    def filter_disadvantaged_tracts(self, request):
        """
        Given a list of census tracts ids, return the ones that are categorized as disadvantaged.
        """
        tract_ids = request.data.get('tract_ids', [])
        tracts = list(
            EeejCejst.objects.only('census_tract_geoid')
            .filter(census_tract_geoid__in=tract_ids, dac=True)
            .values_list('census_tract_geoid', flat=True)
        )
        return JsonResponse(
            {
                'status': 'success',
                'disadvantaged': tracts,
            },
            status=status.HTTP_200_OK,
        )
