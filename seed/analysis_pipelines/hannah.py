# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from collections import defaultdict

from celery import chain, shared_task
from django.db import connection

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.lib.tkbl.tkbl import scope_one_emission_codes
from seed.lib.uniformat.uniformat import uniformat_data
from seed.models import Analysis, AnalysisMessage, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)

ERROR_INVALID_LOCATION = 0
ERROR_RETRIEVING_CENSUS_TRACT = 1
ERROR_NO_VALID_PROPERTIES = 2
WARNING_SOME_INVALID_PROPERTIES = 3
ERROR_NO_TRACT_OR_LOCATION = 4

EEEJ_ANALYSIS_MESSAGES = {
    ERROR_INVALID_LOCATION: "Property missing Lat/Lng (High, Census, or Manually geocoded) or one of: Address Line 1, City & State, or Postal Code.",
    ERROR_RETRIEVING_CENSUS_TRACT: "Unable to retrieve Census Tract for this property.",
    ERROR_NO_TRACT_OR_LOCATION: "Property missing location or Census Tract",
    ERROR_NO_VALID_PROPERTIES: "Analysis found no valid properties to analyze.",
    WARNING_SOME_INVALID_PROPERTIES: "Some properties failed to validate.",
}


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


class HannahPipeline(AnalysisPipeline):
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
    pipeline = HannahPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Hannah analysis")

    # here is where errors would be filtered out

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = HannahPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Aggregating scope one emissions.")
    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # get/create relevant columns
    existing_columns_names_by_code = _create_hannah_analysis_columns(analysis)

    # creates a dict where the first key is a property we are analyzing, the second key is a scope_one_emission_code in that property (should there in )
    query = f"""
    SELECT
        "seed_element"."property_id", "seed_uniformat"."code", AVG("seed_element"."condition_index") AS "mean_condition_index"
    FROM
        "seed_element"
    INNER JOIN
        "seed_uniformat" ON ("seed_element"."code_id" = "seed_uniformat"."id")
    WHERE (
        "seed_uniformat"."code" IN ({", ".join("'" + str(x) + "'" for x in existing_columns_names_by_code)})
        AND
        "seed_element"."property_id" IN (
            SELECT
            U0."property_id"
            FROM
                "seed_analysispropertyview" U0
            WHERE
                U0."id" IN ({", ".join("'" + str(x) + "'" for x in  analysis_property_view_ids)})
        )
    )
    GROUP BY
        "seed_element"."property_id", "seed_uniformat"."code"
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

    mean_condition_index_by_code_and_property_id = defaultdict(dict)
    for property_id, code, mean_condition_index in result:
        mean_condition_index_by_code_and_property_id[property_id][code] = mean_condition_index

    for analysis_property_view in analysis_property_views:
        # update the analysis_property_view
        analysis_property_view.parsed_results = {}
        analysis_property_view.save()

        # update the property view
        mean_condition_index_by_code = mean_condition_index_by_code_and_property_id.get(analysis_property_view.property_id, {})
        property_view = property_views_by_apv_id[analysis_property_view.id]
        for code, col in existing_columns_names_by_code.items():
            property_view.state.extra_data[col] = mean_condition_index_by_code.get(code)

        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_hannah_analysis_columns(analysis):
    existing_columns_names_by_code = {}
    column_meta_by_code = {
        data["code"]: {
            "column_name": data["category"],
            "display_name": data["category"].replace(" ", "_"),
            "description": data["code"] if "definition" not in data else data["code"] + ": " + data["definition"],
        }
        for data in uniformat_data
        if data["code"] in scope_one_emission_codes
    }

    for code, col in column_meta_by_code.items():
        try:
            Column.objects.get(
                column_name=col["column_name"],
                organization=analysis.organization,
                table_name="PropertyState",
            )
            existing_columns_names_by_code[code] = col["column_name"]
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
                existing_columns_names_by_code[code] = col["column_name"]

    return existing_columns_names_by_code
