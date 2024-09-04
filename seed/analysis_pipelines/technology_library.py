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
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


class TechnologyLibraryPipeline(AnalysisPipeline):
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
    pipeline = TechnologyLibraryPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to run Technology Library analysis")

    # here is where errors would be filtered out

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = TechnologyLibraryPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Aggregating scope one emissions.")
    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # get/create relevant columns
    existing_columns_names, element_columns_to_extract = _create_element_columns(analysis)

    for analysis_property_view in analysis_property_views:
        # update the property view and analysis_property_view
        analysis_property_view.parsed_results = {}
        property_view = property_views_by_apv_id[analysis_property_view.id]

        elements = Element.objects.filter(property=property_view.property_id)
        lowest_RSL = elements.filter(code__code__in=scope_one_emission_codes).order_by("remaining_service_life")[:3]

        for rank, element in enumerate(lowest_RSL):

            for element_column, column_name in existing_columns_names.items():

                analysis_property_view.parsed_results[column_name] = getattr(element, element_column)



        for code, col in existing_columns_names.items():
            mean_condition_index = mean_condition_index_by_code.get(code)
            property_view.state.extra_data[col] = mean_condition_index
            if mean_condition_index:
                analysis_property_view.parsed_results[col] = mean_condition_index

        analysis_property_view.save()
        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_element_columns(analysis):
    existing_columns_names = []

    # list of tuples where 0 is the element column name and 1 is the display name
    element_columns_to_extract = [
        ("remaining_service_life", "Remaining Service Life") # element canonical field
        , ("condition_index", "Condition Index") # element canonical field
        , ("replacement_cost", "Component Replacement Value") # element canonical field
        , ("Component_SubType", "Component SubType") # element extra data
        , ("CAPACITY_HEATING", "Heating Capacity") # element extra data
        , ("CAPACITY_HEATING_UNITS", "Heating Capacity Units") # element extra data
        , ("CAPACITY_COOLING", "Cooling Capacity") # element extra data
        , ("CAPACITY_COOLING_UNITS", "Cooling Capacity Units") # element extra data
        , ("sftool_links", "SFTool Links") # from TKBL API
        , ("estcp_links", "ESTCP Links") # from TKBL API
    ]

    rank_columns = [
        "Lowest RSL"
        , "2nd Lowest RSL"
        , "3rd Lowest RSL"
    ]

    column_meta_by_code = [
        {
            "column_name": rank.replace(" ", "_") + "__" + column[0],
            "display_name": rank + ": " + column[1],
            "description": rank + ": " + column[1],
        }
        for rank in rank_columns
        for column in element_columns_to_extract
    ]

    for col in column_meta_by_code:
        try:
            Column.objects.get(
                column_name=col["column_name"],
                organization=analysis.organization,
                table_name="PropertyState",
            )
            existing_columns_names += [col]
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
                existing_columns_names += [col]

    return existing_columns_names, element_columns_to_extract
