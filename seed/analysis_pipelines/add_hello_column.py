"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    analysis_pipeline_task,
    task_create_analysis_property_views,
)
from seed.models import Analysis, AnalysisPropertyView, Column

logger = logging.getLogger(__name__)


class AddHelloColumnPipeline(AnalysisPipeline):
    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # current implementation will *always* start the analysis immediately

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
    pipeline = AddHelloColumnPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready("Ready to add hello column")

    return list(analysis_view_ids_by_property_view_id.values())


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, analysis_property_view_ids, analysis_id):
    pipeline = AddHelloColumnPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step("Adding hello column to properties.")
    
    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # Create the hello column if it doesn't exist
    hello_column = _create_hello_column(analysis)

    for analysis_property_view in analysis_property_views:
        # update the property view and analysis_property_view
        analysis_property_view.parsed_results = {}
        property_view = property_views_by_apv_id[analysis_property_view.id]

        # Add "hello" to the property
        if hello_column:
            property_view.state.extra_data[hello_column.column_name] = "hello"
            analysis_property_view.parsed_results[hello_column.column_name] = "hello"

        analysis_property_view.save()
        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()


def _create_hello_column(analysis):
    """Create a hello column if it doesn't exist."""
    try:
        return Column.objects.get(
            column_name="Hello Column",
            organization=analysis.organization,
            table_name="PropertyState",
        )
    except Exception:
        if analysis.can_create():
            column = Column.objects.create(
                is_extra_data=True,
                column_name="Hello Column",
                organization=analysis.organization,
                table_name="PropertyState",
            )
            column.display_name = "Hello Column"
            column.column_description = "A simple hello column"
            column.save()
            return column
        else:
            return None
