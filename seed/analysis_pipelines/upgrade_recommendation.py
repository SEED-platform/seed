# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from celery import chain, shared_task
from django.db.models import Count, Q
from pint import (
    util as pintutils,
    Quantity
)

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.lib.tkbl.tkbl import scope_one_emission_codes
from seed.models import Analysis, AnalysisMessage, AnalysisPropertyView, Column, Element

logger = logging.getLogger(__name__)


def _log_errors(errors_by_apv_id, analysis_id):
    """Log individual analysis property view errors to the analysis"""
    if errors_by_apv_id:
        for av_id in errors_by_apv_id:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=av_id,
                user_message="  ".join(errors_by_apv_id[av_id]),
                debug_message="",
            )


class UpgradeRecommendationPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # current implementation will *always* start the analysis immediately

        # here's where you would do preprocessing

        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(self._analysis_id),
            _run_analysis.s(self._analysis_id),
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, analysis_id):
    pipeline = UpgradeRecommendationPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Building Upgrade Recommendation analysis")

    # here is where errors would be filtered out

    return list(analysis_view_ids_by_property_view_id.values())


def _get_views_upgrade_recommendation_category(property_view, config):
    # TODO: make these configurable (they can be defaulted if that helps)
    sum_of_modeled_mdms_total_eui = property_view.state.extra_data.get("Sum of Modeled/MDMS Total EUI")
    sum_of_modeled_mdms_gas_eui = property_view.state.extra_data.get("Sum of Modeled/MDMS Gas EUI")
    sum_of_modeled_mdms_electric_eui = property_view.state.extra_data.get("Sum of Modeled/MDMS Electric EUI")
    ashrae_target_gas_eui = property_view.state.extra_data.get("ASHRAE Target Gas EUI")
    ashrae_target_electric_eui = property_view.state.extra_data.get("ASHRAE Target Electric EUI")
    CI = property_view.state.extra_data.get("CI")
    year_built = property_view.state.year_built
    gross_floor_area = property_view.state.gross_floor_area
    elements = Element.objects.filter(property=property_view.property_id)

    # check if this is a pint, if so get value
    if isinstance(gross_floor_area, Quantity):
        gross_floor_area = gross_floor_area.to_base_units().magnitude 

    # calc eui
    if sum_of_modeled_mdms_total_eui:
        eui = float(sum_of_modeled_mdms_total_eui)
    elif sum_of_modeled_mdms_gas_eui and sum_of_modeled_mdms_electric_eui:
        eui = float(sum_of_modeled_mdms_gas_eui) + float(sum_of_modeled_mdms_electric_eui)
    else:
        return "Missing Data (EUI)"

    # If eui greater than total_eui_goal
    total_eui_goal = config.get("total_eui_goal")
    if eui < total_eui_goal:
        return "NO DER project recommended"

    # For these next steps, we will need ashrae_target_gas_eui, ashrae_target_electric_eui, and year_built
    if not year_built:
        return "Missing Data (Year Built)"

    if ashrae_target_gas_eui is None or ashrae_target_electric_eui is None:
        return "Missing Data (ASHRAE Target Gas EUI/ASHRAE Target Electric EUI)"
    else:
        benchmark = (float(ashrae_target_gas_eui) + float(ashrae_target_electric_eui)) / 0.8

    # if young building:
    retrofit_threshold_year = config.get("year_built_threshold")
    if year_built > retrofit_threshold_year:
        # if has BAS and actual to benchmark eui ratio is "fair"
        ddc_control_panel_count = elements.annotate(
            ddc_control_panel_count=Count("id", filter=Q(extra_data__Component_SubType="D.D.C. Control Panel"))
        )
        has_bas = False
        if ddc_control_panel_count:
            has_bas = ddc_control_panel_count.order_by("ddc_control_panel_count").first().ddc_control_panel_count > 0

        fair_actual_to_benchmark_eui_ratio = config.get("fair_actual_to_benchmark_eui_ratio")
        if ((eui / benchmark) > fair_actual_to_benchmark_eui_ratio) and has_bas:
            return "Re-tuning"
        else:
            return "NO DER project recommended"

    # for this next step, we will need gross_floor_area
    if gross_floor_area is None:
        return "Missing Data (Gross Floor Area)"

    # if big and actual to benchmark eui ratio is "poor"
    poor_actual_to_benchmark_eui_ratio = config.get("poor_actual_to_benchmark_eui_ratio")
    building_sqft_threshold = config.get("building_sqft_threshold")
    if ((eui / benchmark) > poor_actual_to_benchmark_eui_ratio) and gross_floor_area > building_sqft_threshold:
        return "Deep Energy Retrofit"

    # for this next step, we will need CI
    if CI is None:
        return "NO DER project recommended"

    # if did not hit ff_fired_equipment_rsl_threshold and ff_fired_equipment_rsl_threshold or condition_index_threshold
    lowest_RSL = elements.filter(code__code__in=scope_one_emission_codes).order_by("remaining_service_life").first()
    if lowest_RSL is None:
        return "NO DER project recommended"
    lowest_RSL = lowest_RSL.remaining_service_life

    if sum_of_modeled_mdms_gas_eui is None:
        return "NO DER project recommended"

    ff_eui_goal = config.get("ff_eui_goal")
    ff_fired_equipment_rsl_threshold = config.get("ff_fired_equipment_rsl_threshold")
    condition_index_threshold = config.get("condition_index_threshold")
    if sum_of_modeled_mdms_gas_eui > ff_eui_goal and (float(lowest_RSL) < ff_fired_equipment_rsl_threshold or condition_index_threshold > CI):
        return "Equipment replacement"
    else:
        return "NO DER project recommended"


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = UpgradeRecommendationPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Generating Numbers")
    analysis = Analysis.objects.get(id=analysis_id)

    # get/create relevant columns
    existing_columns = _create_upgrade_recommendation_analysis_columns(analysis)

    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    for analysis_property_view in analysis_property_views:
        # run the analysis
        property_view = property_views_by_apv_id[analysis_property_view.id]
        upgrade_rec = _get_views_upgrade_recommendation_category(property_view, analysis.configuration)

        # update the analysis_property_view
        analysis_property_view.parsed_results = {
            "Building Upgrade Recommendation": upgrade_rec,
        }
        analysis_property_view.save()

        # update the property view
        if "building_upgrade_recommendation" in existing_columns:
            property_view.state.extra_data.update({"building_upgrade_recommendation": upgrade_rec})
            property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_upgrade_recommendation_analysis_columns(analysis):
    existing_columns = []
    column_meta = [
        {
            "column_name": "building_upgrade_recommendation",
            "display_name": "Building Upgrade Recommendation",
            "description": "Upgrade recommendation as determined by the building upgrade recommendation analysis",
        },
    ]

    for col in column_meta:
        try:
            Column.objects.get(
                column_name=col["column_name"],
                organization=analysis.organization,
                table_name="PropertyState",
            )
            existing_columns.append(col["column_name"])
        except Exception:
            if analysis.can_create():
                column = Column.objects.create(
                    is_extra_data=True,
                    column_name=col["column_name"],
                    organization=analysis.organization,
                    table_name="PropertyState",
                )
                column.display_name = col["display_name"]
                column.column_description = col["description"]
                column.save()
                existing_columns.append(col["column_name"])

    return existing_columns
