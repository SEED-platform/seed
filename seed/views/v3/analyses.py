# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from django.db.models import Count
from pint import Quantity
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.status import HTTP_409_CONFLICT

from quantityfield.units import ureg

from seed.analysis_pipelines.pipeline import AnalysisPipeline, AnalysisPipelineException
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Analysis, Cycle, PropertyView, PropertyState
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper


class CreateAnalysisSerializer(AnalysisSerializer):
    property_view_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    class Meta:
        model = Analysis
        fields = ['name', 'service', 'configuration', 'property_view_ids']

    def create(self, validated_data):
        return Analysis.objects.create(
            name=validated_data['name'],
            service=validated_data['service'],
            configuration=validated_data.get('configuration', {}),
            user_id=validated_data['user_id'],
            organization_id=validated_data['organization_id']
        )


class AnalysisViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisSerializer
    model = Analysis

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_boolean_field(
                name='start_analysis',
                required=True,
                description='If true, immediately start running the analysis after creation. Defaults to false.',
            )
        ],
        request_body=CreateAnalysisSerializer,
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def create(self, request):
        serializer = CreateAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': serializer.errors
            })

        analysis = serializer.save(
            user_id=request.user.id,
            organization_id=self.get_organization(request)
        )
        pipeline = AnalysisPipeline.factory(analysis)
        try:
            progress_data = pipeline.prepare_analysis(
                serializer.validated_data['property_view_ids'],
                start_analysis=request.query_params.get('start_analysis', False)
            )
            return JsonResponse({
                'status': 'success',
                'progress_key': progress_data['progress_key'],
                'progress': progress_data,
            })
        except AnalysisPipelineException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field('property_id', False, 'Property ID')
        ]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request):
        organization_id = self.get_organization(request)
        property_id = request.query_params.get('property_id', None)
        analyses = []
        if property_id is not None:
            analyses_queryset = (
                Analysis.objects.filter(organization=organization_id, analysispropertyview__property=property_id)
                .distinct()
                .order_by('-id')
            )
        else:
            analyses_queryset = (
                Analysis.objects.filter(organization=organization_id)
                .order_by('-id')
            )
        for analysis in analyses_queryset:
            serialized_analysis = AnalysisSerializer(analysis).data
            serialized_analysis.update(analysis.get_property_view_info(property_id))
            serialized_analysis.update({'highlights': analysis.get_highlights(property_id)})
            analyses.append(serialized_analysis)

        return JsonResponse({
            'status': 'success',
            'analyses': analyses
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis doesn't exist in this organization."
            }, status=HTTP_409_CONFLICT)
        serialized_analysis = AnalysisSerializer(analysis).data
        serialized_analysis.update(analysis.get_property_view_info())
        serialized_analysis.update({'highlights': analysis.get_highlights()})

        return JsonResponse({
            'status': 'success',
            'analysis': serialized_analysis
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['post'])
    def start(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            progress_data = pipeline.start_analysis()
            return JsonResponse({
                'status': 'success',
                'progress_key': progress_data['progress_key'],
                'progress': progress_data,
            })
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Requested analysis doesn\'t exist in this organization.'
            }, status=HTTP_409_CONFLICT)
        except AnalysisPipelineException as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['post'])
    def stop(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            pipeline.stop()
            return JsonResponse({
                'status': 'success',
            })
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Requested analysis doesn\'t exist in this organization.'
            }, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def destroy(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            pipeline.delete()
            return JsonResponse({
                'status': 'success',
            })
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Requested analysis doesn\'t exist in this organization.'
            }, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['get'])
    def progress_key(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            progress_data = pipeline.get_progress_data(analysis)
            progress_key = progress_data.key if progress_data is not None else None
            return JsonResponse({
                'status': 'success',
                # NOTE: intentionally *not* returning the actual progress here b/c then
                # folks will poll this endpoint which is less efficient than using
                # the /progress/<key> endpoint
                'progress_key': progress_key,
            })
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Requested analysis doesn\'t exist in this organization.'
            }, status=HTTP_409_CONFLICT)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['get'])
    def stats(self, request):
        org_id = self.get_organization(request)
        cycle_id = request.query_params.get('cycle_id')

        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': 'cycle_id parameter is missing'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            Cycle.objects.get(id=cycle_id, organization_id=org_id)
        except Cycle.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cycle does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        views = PropertyView.objects.filter(state__organization_id=org_id, cycle_id=cycle_id)
        states = PropertyState.objects.filter(id__in=views.values_list('state_id', flat=True))

        def get_counts(field_name):
            """Get aggregated count of each unique value for the field

            :param field_name: str, field on property state to aggregate
            :returns: list[dict], each dict has the key "count" containing the count
                of the value stored in the key "<field_name>"
            """
            agg = list(
                states
                .values(field_name)
                .annotate(count=Count(field_name))
                .order_by('-count')
            )
            return [count for count in agg if count[field_name] is not None]

        property_types = get_counts('extra_data__Largest Property Use Type')
        year_built = get_counts('year_built')
        energy = get_counts('site_eui')
        sqftage = get_counts('gross_floor_area')

        from collections import defaultdict

        extra_data_count = defaultdict(int)
        for data in states.values_list('extra_data', flat=True):
            for key, value in data.items():
                if value is not None:
                    extra_data_count[key] += 1

        extra_data = {k: v for k, v in sorted(extra_data_count.items(), key=lambda item: item[1], reverse=True)}

        year_built_agg = []
        for record in year_built:
            dict = record.copy()
            if isinstance(record['year_built'], int):
                if 1800 < record['year_built'] < 1920:
                    dict['year_built'] = "Pre 1920"
                elif record['year_built'] <= 1945:
                    dict['year_built'] = "1920-1945"
                elif record['year_built'] < 1960:
                    dict['year_built'] = "1946-1959"
                elif record['year_built'] < 1970:
                    dict['year_built'] = "1960-1969"
                elif record['year_built'] < 1980:
                    dict['year_built'] = "1970-1979"
                elif record['year_built'] < 1990:
                    dict['year_built'] = "1980-1989"
                elif record['year_built'] < 2000:
                    dict['year_built'] = "1990-1999"
                elif record['year_built'] <= 2003:
                    dict['year_built'] = "2000-2003"
                elif record['year_built'] <= 2007:
                    dict['year_built'] = "2004-2007"
                elif record['year_built'] <= 2012:
                    dict['year_built'] = "2008-2012"
                else:
                    dict['year_built'] = "> 2012"
            year_built_agg.append(dict)

        c = defaultdict(int)
        for d in year_built_agg:
            c[d['year_built']] += d['count']
        year_built_list = [{'year_built': year_built, 'percentage': count / views.count() * 100} for year_built, count in c.items()]

        energy_list = []
        for i in energy:
            dict = i.copy()
            for k, v in i.items():
                if isinstance(v, Quantity):
                    dict[k] = v.to(ureg.kBTU / ureg.sq_ft / ureg.year).magnitude
            energy_list.append(dict)

        energy_agg = []
        for record in energy_list:
            dict = record.copy()
            if isinstance(record['site_eui'], float):
                if 0 < record['site_eui'] <= 50:
                    dict['site_eui'] = "<= 50"
                elif record['site_eui'] <= 75:
                    dict['site_eui'] = "50-75"
                elif record['site_eui'] <= 100:
                    dict['site_eui'] = "75-100"
                elif record['site_eui'] <= 150:
                    dict['site_eui'] = "100-150"
                else:
                    dict['site_eui'] = "> 150"
            energy_agg.append(dict)

        e = defaultdict(int)
        for f in energy_agg:
            e[f['site_eui']] += f['count']
        energy_list2 = [{'site_eui': site_eui, 'percentage': count / views.count() * 100} for site_eui, count in e.items()]

        sqftage_list = []
        for i in sqftage:
            dict = i.copy()
            for k, v in i.items():
                if isinstance(v, Quantity):
                    dict[k] = v.to(ureg.feet**2).magnitude
            sqftage_list.append(dict)

        sqftage_agg = []
        for record in sqftage_list:
            dict = record.copy()
            if isinstance(record['gross_floor_area'], float):
                if 0 < record['gross_floor_area'] <= 1000:
                    dict['gross_floor_area'] = "<= 1,000"
                elif record['gross_floor_area'] <= 5000:
                    dict['gross_floor_area'] = "1,000-5,000"
                elif record['gross_floor_area'] <= 10000:
                    dict['gross_floor_area'] = "5,000-10,000"
                elif record['gross_floor_area'] <= 25000:
                    dict['gross_floor_area'] = "10,000-25,000"
                elif record['gross_floor_area'] <= 50000:
                    dict['gross_floor_area'] = "25,000-50,000"
                elif record['gross_floor_area'] <= 100000:
                    dict['gross_floor_area'] = "50,000-100,000"
                elif record['gross_floor_area'] <= 200000:
                    dict['gross_floor_area'] = "100,000-200,000"
                elif record['gross_floor_area'] <= 500000:
                    dict['gross_floor_area'] = "200,000-500,000"
                elif record['gross_floor_area'] <= 1000000:
                    dict['gross_floor_area'] = "500,000-1,000,000"
                else:
                    dict['gross_floor_area'] = "> 1,000,000"
            sqftage_agg.append(dict)

        g = defaultdict(int)
        for h in sqftage_agg:
            g[h['gross_floor_area']] += h['count']
        sqftage_list2 = [{'gross_floor_area': gross_floor_area, 'percentage': count / views.count() * 100} for gross_floor_area, count in g.items()]

        return JsonResponse({
            'status': 'success',
            'total_records': views.count(),
            'number_extra_data_fields': len(extra_data_count),
            'property_types': property_types,
            'extra_data fields and count': extra_data,
            'year_built': year_built_list,
            'energy': energy_list2,
            'square_footage': sqftage_list2
        })
