"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import copy
import logging
from datetime import timedelta

import dateutil.parser
from celery import chain, shared_task
from django.core.files.base import ContentFile
from django.db.models import Count
from django.utils.timezone import make_aware

from seed.analysis_pipelines.better.buildingsync import SEED_TO_BSYNC_RESOURCE_TYPE, _build_better_input
from seed.analysis_pipelines.better.client import BETTERClient
from seed.analysis_pipelines.better.helpers import (
    BETTERPipelineContext,
    ExtraDataColumnPath,
    _check_errors,
    _create_better_buildings,
    _run_better_building_analyses,
    _run_better_portfolio_analysis,
    _store_better_building_analysis_results,
    _store_better_portfolio_analysis_results,
    _store_better_portfolio_building_analysis_results,
)
from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    StopAnalysisTaskChainError,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.analysis_pipelines.utils import calendarize_and_extrapolate_meter_readings, get_json_path
from seed.models import Analysis, AnalysisInputFile, AnalysisMessage, AnalysisPropertyView, Column, Cycle, Meter

logger = logging.getLogger(__name__)


def _validate_better_config(analysis):
    """Performs basic validation of the analysis for running a BETTER analysis. Returns any
    errors

    :param analysis: Analysis
    :returns: list[str], list of validation error messages
    """
    config = analysis.configuration
    if not isinstance(config, dict):
        return ["Analysis configuration must be a dictionary/JSON"]

    # print(f"ANALYSIS CONFIG IN PIPELINE: {config}")

    REQUIRED_CONFIG_PROPERTIES = [
        "min_model_r_squared",
        "savings_target",
        "benchmark_data_type",
        "portfolio_analysis",
        "preprocess_meters",
    ]

    return [
        f'Analysis configuration missing required property "{required_prop}"'
        for required_prop in REQUIRED_CONFIG_PROPERTIES
        if required_prop not in config
    ]


class BETTERPipeline(AnalysisPipeline):
    """
    BETTERPipeline is a class for preparing, running, and post-processing
    BETTER analysis by implementing the AnalysisPipeline's abstract
    methods.
    """

    def _prepare_analysis(self, property_view_ids, start_analysis=False):
        """Internal implementation for preparing better analysis"""
        analysis = Analysis.objects.get(id=self._analysis_id)
        organization = analysis.organization
        if not organization.better_analysis_api_key:
            message = (
                f'Organization "{organization.name}" is missing the required BETTER Analysis API Key. '
                "Please update your organization's settings or contact your organization administrator."
            )
            self.fail(message, logger)
            raise AnalysisPipelineError(message)

        # ping BETTER to verify the token is valid
        client = BETTERClient(organization.better_analysis_api_key)
        validity, message = client.token_is_valid()
        if not validity:
            self.fail(message, logger)
            raise AnalysisPipelineError(message)

        # validate the configuration
        validation_errors = _validate_better_config(analysis)
        if validation_errors:
            raise AnalysisPipelineError(f"Analysis configuration is invalid: {'; '.join(validation_errors)}")

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
            _finish_preparation.si(self._analysis_id, start_analysis),
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


def get_meter_readings(property_id, preprocess_meters, config):
    """Returns meters and readings which should meet BETTER's requirements

    :param property_id: int
    :param preprocess_meters: bool, if true aggregate and interpolate readings
        into monthly readings. If false, don't do any preprocessing of the property's
        meters and readings.
    :param config: dict
    :return: List[dict], list of dictionaries of the form:
        { 'meter_type': <Meter.type>, 'readings': List[SimpleMeterReading | MeterReading] }
    """
    selected_meters_and_readings = []
    meters = Meter.objects.filter(
        property_id=property_id,
        type__in=list(SEED_TO_BSYNC_RESOURCE_TYPE.keys()),
    )

    # check if dates are ok

    try:
        if config.get("select_meters") == "date_range":
            value1 = dateutil.parser.parse(config["meter"]["start_date"])
            value2 = dateutil.parser.parse(config["meter"]["end_date"])
            # add a day to get the timestamps to include the last day otherwise timestamp is 00:00:00
            value2 = value2 + timedelta(days=1)
        elif config.get("select_meters") == "select_cycle":
            cycle = Cycle.objects.get(pk=config["cycle_id"])
            value1 = make_aware(dateutil.parser.parse(cycle.start.isoformat()))
            value2 = make_aware(dateutil.parser.parse(cycle.end.isoformat())) + timedelta(days=1)

    except Exception as err:
        raise AnalysisPipelineError(f"Analysis configuration error: invalid dates selected for meter readings: {err}")

    if preprocess_meters:
        for meter in meters:
            if config.get("select_meters") == "date_range":
                try:
                    meter_readings = meter.meter_readings.filter(start_time__range=[value1, value2])
                except Exception as err:
                    logger.error(f"!!! Error retrieving meter readings: {err}")
                    # continue but analysis will fail
                    continue
            else:
                meter_readings = meter.meter_readings
            if meter_readings.count() == 0:
                continue
            monthly_readings = calendarize_and_extrapolate_meter_readings(meter_readings.all())
            # filtering on readings >= 1.0 b/c BETTER flails when readings are less than 1 currently
            monthly_readings = [reading for reading in monthly_readings if reading.reading >= 1.0]
            if len(monthly_readings) >= 12:
                selected_meters_and_readings.append({"meter_type": meter.type, "readings": monthly_readings})
    else:
        meters = meters.annotate(readings_count=Count("meter_readings")).filter(
            readings_count__gte=12,
        )
        for meter in meters:
            # filtering on readings >= 1.0 b/c BETTER flails when readings are less than 1 currently
            readings = []

            if config.get("select_meters") in {"date_range", "select_cycle"}:
                try:
                    readings = meter.meter_readings.filter(start_time__range=[value1, value2], reading__gte=1.0).order_by("start_time")
                except Exception as err:
                    logger.error(f"!!! Error retrieving meter readings: {err}")
                    # continue but analysis will fail
                    continue
            else:
                readings = meter.meter_readings.filter(reading__gte=1.0).order_by("start_time")

            if readings.count() >= 12:
                selected_meters_and_readings.append(
                    {
                        "meter_type": meter.type,
                        "readings": readings,
                    }
                )
    return selected_meters_and_readings


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
    progress_data.step("Creating files for analysis")

    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_view_ids_by_property_view_id.values())
    input_file_paths = []
    for analysis_property_view in analysis_property_views:
        selected_meters_and_readings = get_meter_readings(
            analysis_property_view.property_id, analysis.configuration.get("preprocess_meters", False), analysis.configuration
        )

        if len(selected_meters_and_readings) == 0:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.INFO,
                analysis_id=analysis.id,
                analysis_property_view_id=analysis_property_view.id,
                user_message="Property not included in analysis: Property has no meters "
                "meeting BETTER's requirements. See the analysis documentation for more info.",
                debug_message="",
            )
            continue

        better_doc, errors = _build_better_input(analysis_property_view, selected_meters_and_readings)
        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view.id,
                    user_message=f"Error preparing BETTER input: {error}",
                    debug_message="",
                )
            continue

        analysis_input_file = AnalysisInputFile(content_type=AnalysisInputFile.BUILDINGSYNC, analysis=analysis)
        analysis_input_file.file.save(f"{analysis_property_view.id}.xml", ContentFile(better_doc))
        analysis_input_file.clean()
        analysis_input_file.save()
        input_file_paths.append(analysis_input_file.file.path)

    if len(input_file_paths) == 0:
        message = "No files were able to be prepared for the analysis"
        pipeline.fail(message, logger)
        # stop the task chain
        raise StopAnalysisTaskChainError(message)


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_id, start_analysis):
    """A Celery task which finishes the preparation for BETTER analysis

    :param analysis_id: int
    :param start_analysis: bool
    """
    pipeline = BETTERPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Analysis is ready to be started")

    if start_analysis:
        pipeline = BETTERPipeline(analysis_id)
        pipeline.start_analysis()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.QUEUED)
def _start_analysis(self, analysis_id):
    """Start better analysis by making requests to the service"""
    pipeline = BETTERPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Sending requests to BETTER service")
    analysis = Analysis.objects.get(id=analysis_id)
    client = BETTERClient(analysis.organization.better_analysis_api_key)
    context = BETTERPipelineContext(analysis, progress_data, client)

    better_portfolio_id = None
    if analysis.configuration.get("portfolio_analysis", False):
        better_portfolio_id, errors = client.create_portfolio(f"SEED Analysis {analysis.name} ({analysis.id})")
        if errors:
            _check_errors(
                errors,
                "Failed to create BETTER portfolio",
                context,
                fail_on_error=True,
            )
    better_building_analyses, better_portfolio_building_analyses = _create_better_buildings(better_portfolio_id, context)
    if better_portfolio_id is not None:
        better_portfolio_building_analyses = _run_better_portfolio_analysis(
            better_portfolio_id,
            better_portfolio_building_analyses,
            analysis.configuration,
            context,
        )

        _store_better_portfolio_analysis_results(
            better_portfolio_building_analyses,
            context,
        )

        _store_better_portfolio_building_analysis_results(
            better_portfolio_building_analyses,
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
    progress_data.step("Processing results")

    # store all (LEVEL 1) measure recommendations

    # Updated measure list 05/20/2024 - BETTER workflow has changed in v1.7: The json data returned from the BA and PBA
    # endpoints used to have a ee_measures key in the "assessments" dictionary with a dictionary of true / false values
    # for every measure. Now, that same ee_measures key points to a list with the tokens for each measure that applies.
    # There is no need to check for true or false...if the measure is in the list, it applies.

    # switch to a list of "Level 1 measure" tokens here. Tokens can be found here (grab the top level "token" in each dictionary):
    # https://better-lbnl-development.herokuapp.com/api/v1/measures/
    # updating this list to a list of dictionary to keep the column names as close to the existing ones as possible
    ee_measure_names = [
        {"token": "REDUCE_EQUIPMENT_SCHEDULES", "name": "Reduce Equipment Schedules"},
        {"token": "REDUCE_LIGHTING_LOAD", "name": "Reduce Lighting Load"},
        {"token": "REDUCE_PLUG_LOADS", "name": "Reduce Plug Loads"},
        {"token": "INCREASE_COOLING_SYSTEM_EFFICIENCY", "name": "Increase Cooling System Efficiency"},
        {"token": "DECREASE_HEATING_SETPOINTS", "name": "Decrease Heating Setpoints"},
        {"token": "ENSURE_ADEQUATE_VENTILATION_RATE", "name": "Ensure Adequate Ventilation Rate"},
        {"token": "DECREASE_INFILTRATION", "name": "Decrease Infiltration"},
        {"token": "INCREASE_HEATING_SYSTEM_EFFICIENCY", "name": "Increase Heating System Efficiency"},
        {"token": "ADD_WALL_CEILING_ROOF_INSULATION", "name": "Add Wall/Ceiling/Roof Insulation"},
        {"token": "UPGRADE_TO_SUSTAINABLE_RESOURCES_FOR_WATER_HEATING", "name": "Upgrade to Sustainable Resources for Water Heating"},
        {"token": "UPGRADE_WINDOWS_TO_REDUCE_SOLAR_HEAT_GAIN", "name": "Upgrade Windows to Reduce Solar Heat Gain"},
        {"token": "USE_HIGH_EFFICIENCY_HEAT_PUMP_FOR_HEATING", "name": "Use High Efficiency Heat Pump for Heating"},
        {"token": "INCREASE_COOLING_SETPOINTS", "name": "Increase Cooling Setpoints"},
        {"token": "ADD_FIX_ECONOMIZERS", "name": "Add/Fix Economizers"},
        {"token": "UPGRADE_WINDOWS_TO_IMPROVE_THERMAL_EFFICIENCY", "name": "Upgrade Windows to Improve Thermal Efficiency"},
        {"token": "OTHER_AREAS", "name": "Other Areas"},
    ]

    ee_measure_column_data_paths = [
        ExtraDataColumnPath(
            f"better_recommendation_{ee_measure_name['name'].lower().replace(' ', '_')}",
            f"BETTER Recommendation: {ee_measure_name['name']}",
            1,
            f"assessment.ee_measures.{ee_measure_name['token']}",
        )
        for ee_measure_name in ee_measure_names
    ]

    # gather all columns to store
    BETTER_VALID_MODEL_E_COL = "better_valid_model_electricity"
    BETTER_VALID_MODEL_F_COL = "better_valid_model_fuel"

    # if user is at root level and has role member or owner, columns can be created
    # otherwise set the 'missing_columns' flag for later
    missing_columns = False
    column_data_paths = [
        # Combined Savings
        ExtraDataColumnPath(
            "better_cost_savings_combined",
            "BETTER Potential Cost Savings (USD)",
            1,
            "assessment.assessment_results.assessment_energy_use.cost_savings_combined",
        ),
        ExtraDataColumnPath(
            "better_energy_savings_combined",
            "BETTER Potential Energy Savings (kWh)",
            1,
            "assessment.assessment_results.assessment_energy_use.energy_savings_combined",
        ),
        ExtraDataColumnPath(
            "better_ghg_reductions_combined",
            "BETTER Potential GHG Emissions Reduction (MtCO2e)",
            0.001,
            "assessment.assessment_results.assessment_energy_use.ghg_reductions_combined",
        ),
        # Energy-specific Savings
        ExtraDataColumnPath(
            BETTER_VALID_MODEL_E_COL,
            "BETTER Valid Electricity Model",
            1,
            "assessment.assessment_results.assessment_energy_use.valid_model_e",
        ),
        ExtraDataColumnPath(
            BETTER_VALID_MODEL_F_COL, "BETTER Valid Fuel Model", 1, "assessment.assessment_results.assessment_energy_use.valid_model_f"
        ),
        ExtraDataColumnPath(
            "better_cost_savings_electricity",
            "BETTER Potential Electricity Cost Savings (USD)",
            1,
            "assessment.assessment_results.assessment_energy_use.cost_savings_e",
        ),
        ExtraDataColumnPath(
            "better_cost_savings_fuel",
            "BETTER Potential Fuel Cost Savings (USD)",
            1,
            "assessment.assessment_results.assessment_energy_use.cost_savings_f",
        ),
        ExtraDataColumnPath(
            "better_energy_savings_electricity",
            "BETTER Potential Electricity Energy Savings (kWh)",
            1,
            "assessment.assessment_results.assessment_energy_use.energy_savings_e",
        ),
        ExtraDataColumnPath(
            "better_energy_savings_fuel",
            "BETTER Potential Fuel Energy Savings (kWh)",
            1,
            "assessment.assessment_results.assessment_energy_use.energy_savings_f",
        ),
        ExtraDataColumnPath(
            "better_ghg_reductions_electricity",
            "BETTER Potential Electricity GHG Emissions Reduction (MtCO2e)",
            0.001,
            "assessment.assessment_results.assessment_energy_use.ghg_reductions_e",
        ),
        ExtraDataColumnPath(
            "better_ghg_reductions_fuel",
            "BETTER Potential Fuel GHG Emissions Reduction (MtCO2e)",
            0.001,
            "assessment.assessment_results.assessment_energy_use.ghg_reductions_f",
        ),
        ExtraDataColumnPath(
            # we will manually add this to the data later (it's not part of BETTER's results)
            # Provides info so user knows which SEED analysis last updated these stored values
            "better_seed_analysis_id",
            "BETTER Analysis Id",
            1,
            "better_seed_analysis_id",
        ),
        ExtraDataColumnPath(
            # we will manually add this to the data later (it's not part of BETTER's results)
            # Provides info so user knows which SEED analysis last updated these stored values
            "better_seed_run_id",
            "BETTER Run Id",
            1,
            "better_seed_run_id",
        ),
        ExtraDataColumnPath("better_min_model_r_squared", "BETTER Min Model R^2", 1, "min_model_r_squared"),
        ExtraDataColumnPath(
            "better_inverse_r_squared_electricity", "BETTER Inverse Model R^2 (Electricity)", 1, "inverse_model.ELECTRICITY.r2"
        ),
        ExtraDataColumnPath(
            "better_inverse_r_squared_fossil_fuel", "BETTER Inverse Model R^2 (Fossil Fuel)", 1, "inverse_model.FOSSIL_FUEL.r2"
        ),
        *ee_measure_column_data_paths,
    ]

    for column_data_path in column_data_paths:
        # check if the column exists with the bare minimum required pieces of data. For example,
        # don't check column_description and display_name because they may be changed by
        # the user at a later time.
        # if column doesn't exist, and user has permission to create, then create
        try:
            Column.objects.get(
                is_extra_data=True,
                column_name=column_data_path.column_name,
                organization=analysis.organization,
                table_name="PropertyState",
            )
        except Exception:
            if analysis.can_create():
                Column.objects.create(
                    is_extra_data=True,
                    column_name=column_data_path.column_name,
                    organization=analysis.organization,
                    table_name="PropertyState",
                    display_name=column_data_path.column_display_name,
                    column_description=column_data_path.column_display_name,
                )
            else:
                missing_columns = True

    # Update the original PropertyView's PropertyState with analysis results of interest
    analysis_property_views = analysis.analysispropertyview_set.prefetch_related("property", "cycle").all()
    property_view_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    for analysis_property_view in analysis_property_views:
        raw_better_results = copy.deepcopy(analysis_property_view.parsed_results)
        raw_better_results.update({"better_seed_analysis_id": analysis_id})
        raw_better_results.update({"better_seed_run_id": analysis_property_view.id})
        simplified_results = {}
        for data_path in column_data_paths:
            value = get_json_path(data_path.json_path, raw_better_results)
            if value is not None:
                # some of the ee_measures return an empty string, which should be falsy
                if "ee_measures" in data_path.json_path and value == "":
                    value = 0.0 * data_path.unit_multiplier  # to be consistent
                else:
                    value = float(value) * data_path.unit_multiplier
            simplified_results[data_path.column_name] = value

        electricity_model_is_valid = bool(simplified_results[BETTER_VALID_MODEL_E_COL])
        fuel_model_is_valid = bool(simplified_results[BETTER_VALID_MODEL_F_COL])

        # create a message for the failed models
        warning_messages = []
        if not electricity_model_is_valid:
            r2_electricity = simplified_results["better_inverse_r_squared_electricity"]
            if r2_electricity is not None:
                r2_electricity = round(r2_electricity, 4)
            warning_messages.append(
                f"No reasonable change-point model could be found for this building's electricity consumption. Model R^2 was {r2_electricity}"
            )
        if not fuel_model_is_valid:
            r2_fossil_fuel = simplified_results["better_inverse_r_squared_fossil_fuel"]
            if r2_fossil_fuel is not None:
                r2_fossil_fuel = round(r2_fossil_fuel, 4)
            warning_messages.append(
                f"No reasonable change-point model could be found for this building's fossil fuel consumption. Model R^2 was {r2_fossil_fuel}"
            )
        for warning_message in warning_messages:
            AnalysisMessage.log_and_create(
                logger,
                AnalysisMessage.WARNING,
                warning_message,
                "",
                analysis_id,
                analysis_property_view.id,
            )

        cleaned_results = {}
        # do some extra cleanup of the results:
        #  - round decimal places of floats
        #  - for fuel-type specific fields, set values to null if the model for
        #    that fuel type wasn't valid (e.g., if electricity model is invalid,
        #    set "potential electricity savings" to null)
        for col_name, value in simplified_results.items():
            updated_value = value if not isinstance(value, float) else round(value, 2)
            if col_name.endswith("_electricity") and col_name != BETTER_VALID_MODEL_E_COL:
                cleaned_results[col_name] = updated_value if electricity_model_is_valid else None
            elif col_name.endswith("_fuel") and col_name != BETTER_VALID_MODEL_F_COL:
                cleaned_results[col_name] = updated_value if fuel_model_is_valid else None
            else:
                cleaned_results[col_name] = updated_value

        # if no columns are missing, save back to property
        if not missing_columns:
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
