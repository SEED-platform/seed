# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import copy

from django.db.models import Count
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
)
from seed.analysis_pipelines.utils import get_json_path

from seed.models import (
    Analysis,
    AnalysisInputFile,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    Meter,
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
        'min_model_r_squared',
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

    def _prepare_analysis(self, property_view_ids, start_analysis=False):
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

        progress_data = self.get_progress_data(analysis)

        # Steps:
        # 1) ...starting
        # 2) create AnalysisPropertyViews
        # 3) create input files for each property
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _prepare_all_properties.s(self._analysis_id),
            _finish_preparation.si(self._analysis_id, start_analysis)
        ).apply_async()

    def _start_analysis(self):
        """Internal implementation for starting the BETTER analysis"""

        progress_data = self.get_progress_data()

        # Steps:
        # 1) ...starting
        # 2) make requests to better
        # 3) process the results files
        progress_data.total = 3
        progress_data.save()

        chain(
            _start_analysis.si(self._analysis_id),
            _process_results.si(self._analysis_id),
            _finish_analysis.si(self._analysis_id),
        ).apply_async()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _prepare_all_properties(self, analysis_view_ids_by_property_view_id, analysis_id):
    """A Celery task which attempts to make BuildingSync files for all AnalysisPropertyViews.

    :param analysis_view_ids_by_property_view_id: dictionary[int:int]
    :param analysis_id: int
    :returns: void
    """
    analysis = Analysis.objects.get(id=analysis_id)
    pipeline = BETTERPipeline(analysis.id)

    progress_data = pipeline.get_progress_data(analysis)
    progress_data.step('Creating files for analysis')

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
        message = 'No files were able to be prepared for the analysis'
        pipeline.fail(message, logger)
        # stop the task chain
        raise StopAnalysisTaskChain(message)


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_id, start_analysis):
    """A Celery task which finishes the preparation for BETTER analysis

    :param analysis_id: int
    :param start_analysis: bool
    """
    pipeline = BETTERPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready('Analysis is ready to be started')

    if start_analysis:
        pipeline = BETTERPipeline(analysis_id)
        pipeline.start_analysis()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.QUEUED)
def _start_analysis(self, analysis_id):
    """Start better analysis by making requests to the service"""
    pipeline = BETTERPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step('Sending requests to BETTER service')

    analysis = Analysis.objects.get(id=analysis_id)
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

    if better_portfolio_id is not None:
        better_analysis_id = _run_better_portfolio_analysis(
            better_portfolio_id,
            better_building_analyses,
            analysis.configuration,
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
            analysis.configuration,
            context,
        )

    _store_better_building_analysis_results(
        better_building_analyses,
        context,
    )


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _process_results(self, analysis_id):
    """Store results from the analysis in the original PropertyState"""
    pipeline = BETTERPipeline(analysis_id)
    analysis = Analysis.objects.get(id=analysis_id)

    progress_data = pipeline.get_progress_data(analysis)
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
    BETTER_VALID_MODEL_E_COL = 'better_valid_model_electricity'
    BETTER_VALID_MODEL_F_COL = 'better_valid_model_fuel'
    column_data_paths = [
        # Combined Savings
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
        # Energy-specific Savings
        ExtraDataColumnPath(
            BETTER_VALID_MODEL_E_COL,
            'BETTER Valid Electricity Model',
            'assessment.assessment_energy_use.valid_model_e'
        ),
        ExtraDataColumnPath(
            BETTER_VALID_MODEL_F_COL,
            'BETTER Valid Fuel Model',
            'assessment.assessment_energy_use.valid_model_f'
        ),
        ExtraDataColumnPath(
            'better_cost_savings_electricity',
            'BETTER Potential Electricity Cost Savings (USD)',
            'assessment.assessment_energy_use.cost_savings_e'
        ),
        ExtraDataColumnPath(
            'better_cost_savings_fuel',
            'BETTER Potential Fuel Cost Savings (USD)',
            'assessment.assessment_energy_use.cost_savings_f'
        ),
        ExtraDataColumnPath(
            'better_energy_savings_electricity',
            'BETTER Potential Electricity Energy Savings (kWh)',
            'assessment.assessment_energy_use.energy_savings_e'
        ),
        ExtraDataColumnPath(
            'better_energy_savings_fuel',
            'BETTER Potential Fuel Energy Savings (kWh)',
            'assessment.assessment_energy_use.energy_savings_f'
        ),
        ExtraDataColumnPath(
            'better_ghg_reductions_electricity',
            'BETTER Potential Electricity GHG Emissions Reduction (kgCO2e)',
            'assessment.assessment_energy_use.ghg_reductions_e'
        ),
        ExtraDataColumnPath(
            'better_ghg_reductions_fuel',
            'BETTER Potential Fuel GHG Emissions Reduction (kgCO2e)',
            'assessment.assessment_energy_use.ghg_reductions_f'
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
    property_view_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    for analysis_property_view in analysis_property_views:
        raw_better_results = copy.deepcopy(analysis_property_view.parsed_results)
        raw_better_results.update({'better_seed_analysis_id': analysis_id})

        simplified_results = {
            data_path.column_name: get_json_path(data_path.json_path, raw_better_results)
            for data_path in column_data_paths
        }

        electricity_model_is_valid = bool(simplified_results[BETTER_VALID_MODEL_E_COL])
        fuel_model_is_valid = bool(simplified_results[BETTER_VALID_MODEL_F_COL])

        # create a message for the failed models
        warning_messages = []
        if not electricity_model_is_valid:
            warning_messages.append('No reasonable change-point model could be found for this building\'s electricity consumption.')
        if not fuel_model_is_valid:
            warning_messages.append('No reasonable change-point model could be found for this building\'s fossil fuel consumption.')
        for warning_message in warning_messages:
            AnalysisMessage.log_and_create(
                logger,
                AnalysisMessage.WARNING,
                warning_message,
                '',
                analysis_id,
                analysis_property_view.id,
            )

        cleaned_results = {}
        # do some extra cleanup of the results:
        #  - round decimal places of floats
        #  - for fuel-type specific fields, set values to null if the model for
        #    that fuel type wasn't valid (e.g. if electricity model is invalid,
        #    set "potential electricity savings" to null)
        for col_name, value in simplified_results.items():
            value = value if type(value) is not float else round(value, 2)
            if col_name.endswith('_electricity') and col_name != BETTER_VALID_MODEL_E_COL:
                cleaned_results[col_name] = value if electricity_model_is_valid else None
            elif col_name.endswith('_fuel') and col_name != BETTER_VALID_MODEL_F_COL:
                cleaned_results[col_name] = value if fuel_model_is_valid else None
            else:
                cleaned_results[col_name] = value

        original_property_state = property_view_by_apv_id[analysis_property_view.id].state
        original_property_state.extra_data.update(cleaned_results)
        original_property_state.save()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _finish_analysis(self, analysis_id):
    """A Celery task which finishes the analysis run

    :param analysis_id: int
    """
    pipeline = BETTERPipeline(analysis_id)
    pipeline.set_analysis_status_to_completed()
