"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from collections import defaultdict

from celery import chain, shared_task
from django.db import connection
from django.db.models import Count, Q

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.lib.tkbl.tkbl import scope_one_emission_codes
from seed.lib.uniformat.uniformat import uniformat_data
from seed.models import Analysis, AnalysisPropertyView, Column, Element

logger = logging.getLogger(__name__)


class ElementStatisticsPipeline(AnalysisPipeline):
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
    pipeline = ElementStatisticsPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Element Statistics analysis")

    # here is where errors would be filtered out

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = ElementStatisticsPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Aggregating scope one emissions.")
    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # get/create relevant columns
    existing_columns_names_by_code = _create_element_columns(analysis)
    ddc_count_column = _create_ddc_count_column(analysis)

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

    # calc # of Elements where Component_SubType is D.D.C. Control Panel per Property
    property_ids = analysis_property_views.values("property")
    elements = Element.objects.filter(property__in=property_ids)
    counts = elements.values("property").annotate(
        ddc_control_panel_count=Count("id", filter=Q(extra_data__Component_SubType="D.D.C. Control Panel"))
    )
    ddc_count_by_property_id = {count["property"]: count["ddc_control_panel_count"] for count in counts}

    for analysis_property_view in analysis_property_views:
        # update the property view and analysis_property_view
        analysis_property_view.parsed_results = {}
        mean_condition_index_by_code = mean_condition_index_by_code_and_property_id.get(analysis_property_view.property_id, {})
        property_view = property_views_by_apv_id[analysis_property_view.id]

        # add ddc count by property id
        if ddc_count_column:
            ddc_count = ddc_count_by_property_id[property_view.property_id]
            property_view.state.extra_data[ddc_count_column.column_name] = ddc_count
            if ddc_count:
                analysis_property_view.parsed_results[ddc_count_column.column_name] = ddc_count

        # add mean condition index by code
        for code, col in existing_columns_names_by_code.items():
            mean_condition_index = mean_condition_index_by_code.get(code)
            property_view.state.extra_data[col] = mean_condition_index
            if mean_condition_index:
                analysis_property_view.parsed_results[col] = mean_condition_index

        analysis_property_view.save()
        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_element_columns(analysis):
    existing_columns_names_by_code = {}
    column_meta_by_code = {
        data["code"]: {
            "column_name": data["category"] + " CI",
            "display_name": data["category"].replace(" ", "_") + " CI",
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


def _create_ddc_count_column(analysis):
    try:
        return Column.objects.get(
            column_name="Number of D.D.C Control Panels",
            organization=analysis.organization,
            table_name="PropertyState",
        )

    except Exception:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Number of D.D.C Control Panels",
                organization=analysis.organization,
                table_name="PropertyState",
            )
            column.display_name = "Number of D.D.C Control Panels"
            column.column_description = "Number of D.D.C Control Panels"
            column.save()

            return column

        else:
            return None
