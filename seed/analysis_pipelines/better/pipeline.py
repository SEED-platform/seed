# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import copy

from django.db.models import Q, Count
from django.utils import timezone as tz
from django.core.files.base import ContentFile
from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    task_create_analysis_property_views,
    analysis_pipeline_task,
    StopAnalysisTaskChain
)
from seed.analysis_pipelines.better.buildingsync import (
    SEED_TO_BSYNC_RESOURCE_TYPE,
    _build_better_input,
)
from seed.analysis_pipelines.better.client import (
    BETTERClient,
)
from seed.analysis_pipelines.better.helpers import (
    BETTERPipelineContext,
    ExtraDataColumnPath,
    _check_errors,
    _create_better_buildings,
    _run_better_building_analyses,
    _run_better_portfolio_analysis,
    _store_better_building_analysis_results,
    _store_better_portfolio_analysis_results,
    _update_original_property_state,
)

from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    Analysis,
    AnalysisInputFile,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    Meter,
    PropertyView
)


logger = logging.getLogger(__name__)


def _validate_better_config(analysis):
    """Performs basic validation of the analysis for running a BETTER analysis. Returns any
    errors

    :param analysis: Analysis
    :returns: list[str], list of validation error messages
    """
    config = analysis.configuration
    if not isinstance(config, dict):
        return ['Analysis configuration must be a dictionary/JSON']

    REQUIRED_CONFIG_PROPERTIES = [
        'min_r_squared',
        'savings_target',
        'benchmark_data',
        'portfolio_analysis',
    ]

    return [
        f'Analysis configuration missing required property "{required_prop}"'
        for required_prop in REQUIRED_CONFIG_PROPERTIES if required_prop not in config
    ]


class BETTERPipeline(AnalysisPipeline):
    """
    BETTERPipeline is a class for preparing, running, and post
    processing BETTER analysis by implementing the AnalysisPipeline's abstract
    methods.
    """

    def _prepare_analysis(self, property_view_ids):
        """Internal implementation for preparing better analysis"""
        analysis = Analysis.objects.get(id=self._analysis_id)
        organization = analysis.organization
        if not organization.better_analysis_api_key:
            message = (f'Organization "{organization.name}" is missing the required BETTER Analysis API Key. '
                       'Please update your organization\'s settings or contact your organization administrator.')
            self.fail(message, logger)
            raise AnalysisPipelineException(message)

        # ping BETTER to verify the token is valid
        client = BETTERClient(organization.better_analysis_api_key)
        _, errors = client.get_buildings()
        if errors:
            message = '; '.join(errors)
            self.fail(message, logger)
            raise AnalysisPipelineException(message)

        # validate the configuration
        validation_errors = _validate_better_config(analysis)
        if validation_errors:
            raise AnalysisPipelineException(
                f'Analysis configuration is invalid: {"; ".join(validation_errors)}')

        progress_data = ProgressData('prepare-analysis-better', self._analysis_id)

        # Steps:
        # 1) ...starting
        # 2) create AnalysisPropertyViews
        # 3) create input files for each property
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids, progress_data.key),
            _prepare_all_properties.s(self._analysis_id, progress_data.key),
            _finish_preparation.si(self._analysis_id, progress_data.key)
        ).apply_async()

        return progress_data.result()

    def _start_analysis(self):
        """Internal implementation for starting the BETTER analysis"""

        progress_data = ProgressData('start-analysis-better', self._analysis_id)

        # Steps:
        # 1) ...starting
        # 2) make requests to better
        # 3) process the results files
        progress_data.total = 3
        progress_data.save()

        chain(
            _start_analysis.si(self._analysis_id, progress_data.key),
            _process_results.si(self._analysis_id, progress_data.key),
            _finish_analysis.si(self._analysis_id, progress_data.key),
        ).apply_async()

        return progress_data.result()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _prepare_all_properties(self, analysis_view_ids_by_property_view_id, analysis_id, progress_data_key):
    """A Celery task which attempts to make BuildingSync files for all AnalysisPropertyViews.

    :param analysis_view_ids_by_property_view_id: dictionary[int:int]
    :param analysis_id: int
    :param progress_data_key: str
    :returns: void
    """
    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Creating files for analysis')

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_view_ids_by_property_view_id.values())
    input_file_paths = []
    for analysis_property_view in analysis_property_views:
        meters = (
            Meter.objects
            .annotate(readings_count=Count('meter_readings'))
            .filter(
                property=analysis_property_view.property,
                type__in=list(SEED_TO_BSYNC_RESOURCE_TYPE.keys()),
                readings_count__gte=12,
            )
        )
        if meters.count() == 0:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.INFO,
                analysis_id=analysis.id,
                analysis_property_view_id=analysis_property_view.id,
                user_message='Property not used in analysis: Property has no linked electricity or natural gas meters '
                             'with 12 or more readings',
                debug_message=''
            )
            continue

        better_doc, errors = _build_better_input(analysis_property_view, meters)
        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view.id,
                    user_message=f'Error preparing BETTER input: {error}',
                    debug_message='',
                )
            continue

        analysis_input_file = AnalysisInputFile(
            content_type=AnalysisInputFile.BUILDINGSYNC,
            analysis=analysis
        )
        analysis_input_file.file.save(f'{analysis_property_view.id}.xml', ContentFile(better_doc))
        analysis_input_file.clean()
        analysis_input_file.save()
        input_file_paths.append(analysis_input_file.file.path)

    if len(input_file_paths) == 0:
        pipeline = BETTERPipeline(analysis.id)
        message = 'No files were able to be prepared for the analysis'
        pipeline.fail(message, logger, progress_data_key=progress_data.key)
        # stop the task chain
        raise StopAnalysisTaskChain(message)


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_id, progress_data_key):
    """A Celery task which finishes the preparation for BETTER analysis

    :param analysis_id: int
    :param progress_data_key: str
    """
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.READY
    analysis.save()

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.finish_with_success()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.QUEUED)
def _start_analysis(self, analysis_id, progress_data_key):
    """Start better analysis by making requests to the service"""
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.RUNNING
    analysis.start_time = tz.now()
    analysis.save()

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Sending requests to BETTER service')

    client = BETTERClient(analysis.organization.better_analysis_api_key)
    context = BETTERPipelineContext(analysis, progress_data, client)

    better_portfolio_id = None
    if analysis.configuration.get('portfolio_analysis', False):
        better_portfolio_id, errors = client.create_portfolio(f'SEED Analysis {analysis.name} ({analysis.id})')
        if errors:
            _check_errors(
                errors,
                'Failed to create BETTER portfolio',
                context,
                fail_on_error=True,
            )

    better_building_analyses = _create_better_buildings(better_portfolio_id, context)

    analysis_config = {
        "benchmark_data": analysis.configuration['benchmark_data']['benchmark_data'],
        "savings_target": analysis.configuration['savings_target']['savings_target'],
        "min_model_r_squared": analysis.configuration['min_r_squared']
    }
    if better_portfolio_id is not None:
        better_analysis_id = _run_better_portfolio_analysis(
            better_portfolio_id,
            better_building_analyses,
            analysis_config,
            context,
        )

        _store_better_portfolio_analysis_results(
            better_analysis_id,
            better_building_analyses,
            context,
        )

    else:
        _run_better_building_analyses(
            better_building_analyses,
            analysis_config,
            context,
        )

    _store_better_building_analysis_results(
        better_building_analyses,
        context,
    )


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _process_results(self, analysis_id, progress_data_key):
    """Store results from the analysis in the original PropertyState"""
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.RUNNING
    analysis.save()

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Processing results')

    # store all measure recommendations
    ee_measure_names = [
        'Upgrade Windows',
        'Reduce Plug Loads',
        'Add/Fix Economizers',
        'Decrease Ventilation',
        'Reduce Lighting Load',
        'Check Fossil Baseload',
        'Decrease Infiltration',
        'Decrease Heating Setpoints',
        'Eliminate Electric Heating',
        'Increase Cooling Setpoints',
        'Reduce Equipment Schedules',
        'Add Wall/Ceiling Insulation',
        'Increase Cooling System Efficiency',
        'Increase Heating System Efficiency'
    ]
    ee_measure_column_data_paths = [
        ExtraDataColumnPath(
            f'better_recommendation_{ee_measure_name.lower().replace(" ", "_")}',
            f'BETTER Recommendation: {ee_measure_name}',
            f'assessment.ee_measures.{ee_measure_name}'
        ) for ee_measure_name in ee_measure_names
    ]

    # gather all columns to store
    column_data_paths = [
        ExtraDataColumnPath(
            'better_cost_savings_combined',
            'BETTER Potential Cost Savings (USD)',
            'assessment.assessment_energy_use.cost_savings_combined'
        ),
        ExtraDataColumnPath(
            'better_energy_savings_combined',
            'BETTER Potential Energy Savings (kWh)',
            'assessment.assessment_energy_use.energy_savings_combined'
        ),
        ExtraDataColumnPath(
            'better_ghg_reductions_combined',
            'BETTER Potential GHG Emissions Reduction (kgCO2e)',
            'assessment.assessment_energy_use.ghg_reductions_combined'
        ),
        ExtraDataColumnPath(
            # we will manually add this to the data later (it's not part of BETTER's results)
            # Provides info so user knows which SEED analysis last updated these stored values
            'better_seed_analysis_id',
            'BETTER Analysis Id',
            'better_seed_analysis_id'
        ),
        ExtraDataColumnPath(
            'better_min_model_r_squared',
            'BETTER Min Model R^2',
            'min_model_r_squared'
        ),
    ] + ee_measure_column_data_paths

    # create columns if they don't already exist
    for column_data_path in column_data_paths:
        Column.objects.get_or_create(
            is_extra_data=True,
            column_name=column_data_path.column_name,
            display_name=column_data_path.column_display_name,
            organization=analysis.organization,
            table_name='PropertyState',
        )

    # Update the original PropertyView's PropertyState with analysis results of interest
    analysis_property_views = analysis.analysispropertyview_set.prefetch_related('property', 'cycle').all()
    property_view_query = Q()
    for analysis_property_view in analysis_property_views:
        property_view_query |= (
            Q(property=analysis_property_view.property)
            & Q(cycle=analysis_property_view.cycle)
        )
    # get original property views keyed by canonical property id and cycle
    property_views_by_property_cycle_id = {
        (pv.property.id, pv.cycle.id): pv
        for pv in PropertyView.objects.filter(property_view_query).prefetch_related('state')
    }

    for analysis_property_view in analysis_property_views:
        property_cycle_id = (analysis_property_view.property.id, analysis_property_view.cycle.id)
        property_view = property_views_by_property_cycle_id[property_cycle_id]
        data = copy.deepcopy(analysis_property_view.parsed_results)
        data.update({'better_seed_analysis_id': analysis_id})
        _update_original_property_state(
            property_view.state,
            data,
            column_data_paths
        )


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _finish_analysis(self, analysis_id, progress_data_key):
    """A Celery task which finishes the analysis run

    :param analysis_id: int
    :param progress_data_key: str
    """
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.COMPLETED
    analysis.end_time = tz.now()
    analysis.save()

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.finish_with_success()
