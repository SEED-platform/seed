# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging

from celery import chain, shared_task
from tkbl import filter_by_uniformat_code

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.lib.tkbl.tkbl import scope_one_emission_codes
from seed.models import Analysis, AnalysisPropertyView, Column, Element

logger = logging.getLogger(__name__)

rank_columns = ["Lowest RSL", "2nd Lowest RSL", "3rd Lowest RSL"]

element_columns_to_extract = [
    {"column_name": "remaining_service_life", "display_name": "Remaining Service Life", "is_extra_data": False},
    {"column_name": "condition_index", "display_name": "Condition Index", "is_extra_data": False},
    {"column_name": "replacement_cost", "display_name": "Component Replacement Value", "is_extra_data": False},
    {"column_name": "Component_SubType", "display_name": "Component SubType", "is_extra_data": True},
    {"column_name": "CAPACITY_HEATING", "display_name": "Heating Capacity", "is_extra_data": True},
    {"column_name": "CAPACITY_HEATING_UNITS", "display_name": "Heating Capacity Units", "is_extra_data": True},
    {"column_name": "CAPACITY_COOLING", "display_name": "Cooling Capacity", "is_extra_data": True},
    {"column_name": "CAPACITY_COOLING_UNITS", "display_name": "Cooling Capacity Units", "is_extra_data": True},
]

links_to_extract = [
    {"column_name": "sftool_links", "display_name": "Sftool Links"},
    {"column_name": "condition_index", "display_name": "Condition Index"},
]


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
    progress_data.step("Generating Numbers")
    analysis = Analysis.objects.get(id=analysis_id)

    # get/create relevant columns
    existing_columns = _create_technology_library_analysis_columns(analysis)

    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)
    for analysis_property_view in analysis_property_views:
        property_view = property_views_by_apv_id[analysis_property_view.id]
        elements = Element.objects.filter(property=property_view.property_id)
        lowest_RSL = elements.filter(code__code__in=scope_one_emission_codes).order_by("remaining_service_life")[:3]

        for rank, element in zip(rank_columns, lowest_RSL):
            links = [x["url"] for x in json.loads(filter_by_uniformat_code(element.code.code))]
            sftool_links = [x for x in links if "https://sftool.gov" in x]
            estcp_links = [x for x in links if "https://sftool.gov" not in x]

            column_name = rank.replace(" ", "_") + "_sftool_links"
            analysis_property_view.parsed_results[column_name] = sftool_links
            if column_name in existing_columns:
                property_view.state.extra_data[column_name] = sftool_links

            column_name = rank.replace(" ", "_") + "_estcp_links"
            analysis_property_view.parsed_results[column_name] = estcp_links
            if column_name in existing_columns:
                property_view.state.extra_data[column_name] = estcp_links

            for element_column in element_columns_to_extract:
                column_name = rank.replace(" ", "_") + "_" + element_column["column_name"]
                if element_column["is_extra_data"]:
                    column_data = getattr(element.extra_data, element_column["column_name"], None)
                else:
                    column_data = getattr(element, element_column["column_name"])

                analysis_property_view.parsed_results[column_name] = column_data
                if column_name in existing_columns:
                    property_view.state.extra_data[column_name] = column_data

        property_view.state.save()
        analysis_property_view.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_technology_library_analysis_columns(analysis):
    existing_columns = []
    column_meta = [
        {
            "column_name": rank.replace(" ", "_") + "_" + column["column_name"],
            "display_name": rank + ": " + column["display_name"],
            "description": rank + ": " + column["display_name"],
        }
        for rank in rank_columns
        for column in element_columns_to_extract + links_to_extract
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
