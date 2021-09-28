from collections import namedtuple
import logging
import pathlib

from django.core.files.base import File as BaseFile

from seed.analysis_pipelines.pipeline import StopAnalysisTaskChain, AnalysisPipelineException
from seed.analysis_pipelines.better.buildingsync import _parse_analysis_property_view_id
from seed.models import (
    AnalysisMessage,
    AnalysisOutputFile,
    AnalysisPropertyView,
)

logger = logging.getLogger(__name__)


class BuildingAnalysis:
    """Used to track AnalysisPropertyViews and BETTER Building and Analysis IDs"""
    def __init__(self, analysis_property_view_id, better_building_id, better_analysis_id):
        self.analysis_property_view_id = analysis_property_view_id
        self.better_building_id = better_building_id
        self.better_analysis_id = better_analysis_id


class BETTERPipelineContext:
    """Datastructure to avoid multiple pass-through variables"""
    def __init__(self, analysis, progress_data, better_client):
        """
        :param analysis: Analysis
        :param progress_data, ProgressData
        :param better_client: BETTERClient
        """
        self.analysis = analysis
        self.progress_data = progress_data
        self.client = better_client


# Used to define json paths to parse from analysis results, which are linked to an extra data column
# column_name: Column.column_name (also the extra_data key)
# column_display_name: Column.display_name
# json_path: naive json path -- dot separated keys into the parsed analysis results dict
ExtraDataColumnPath = namedtuple('ExtraDataColumnPath', ['column_name', 'column_display_name', 'json_path'])


def _check_errors(errors, what_failed_desc, context, analysis_property_view_id=None, fail_on_error=False):
    """Creates error messages for the analysis if any are found.

    :param analysis: Analysis
    :param progress_data: ProgressData
    :param errors: list[str], list of debug error messages
    :param what_failed_desc: str, description of what was happening when failure occurred
        e.g. what were you trying to do
    :param analysis_property_view_id: int, optional, if provided, the error messages will be linked
        to this property view
    :param fail_on_error: bool, optional, if True and errors were found, this fails the pipeline
        and stops the celery task chain
    """
    if not errors:
        return

    for error in errors:
        AnalysisMessage.log_and_create(
            logger=logger,
            type_=AnalysisMessage.ERROR,
            analysis_id=context.analysis.id,
            analysis_property_view_id=analysis_property_view_id,
            user_message='Unexpected error from BETTER service. Please confirm your Organization\'s API token is correct and try again or contact the SEED administrators.',
            debug_message=f'{what_failed_desc}: {error}',
        )

    if fail_on_error:
        # avoid circular import
        from seed.analysis_pipelines.better.pipeline import BETTERPipeline

        pipeline = BETTERPipeline(context.analysis.id)
        pipeline.fail(what_failed_desc, logger, progress_data_key=context.progress_data.key)
        # stop the task chain
        raise StopAnalysisTaskChain(what_failed_desc)


def _run_better_portfolio_analysis(better_portfolio_id, better_building_analyses, analysis_config, context):
    """Create and run an analysis for a BETTER portfolio. Updates all BuildingAnalysis
    objects in better_building_analyses to store their individual building analysis IDs.

    :param better_portfolio_id: int
    :param better_building_analyses: list[BuildingAnalysis]
    :param analysis_config: dict, config for the analysis API
    :param analysis: Analysis
    :param progress_data: ProgressData
    :returns: int, better_analysis_id, ID of the analysis which was created and run
    """
    better_analysis_id, errors = context.client.create_portfolio_analysis(
        better_portfolio_id,
        analysis_config,
    )
    _check_errors(
        errors,
        'Failed to create BETTER portfolio analysis',
        context,
        fail_on_error=True
    )

    errors = context.client.run_portfolio_analysis(
        better_portfolio_id,
        better_analysis_id
    )
    if errors:
        _check_errors(
            errors,
            'Failed to generate BETTER portfolio analysis',
            context,
            fail_on_error=True,
        )

    # find and store all individual building analysis IDs for the portfolio
    # so we can fetch and save those individual analysis results later
    better_portfolio_analysis, errors = context.client.get_portfolio_analysis(better_portfolio_id, better_analysis_id)
    _check_errors(
        errors,
        'Failed to get BETTER portfolio analysis as JSON',
        context,
        fail_on_error=True
    )

    api_building_analytics = better_portfolio_analysis.get('building_analytics_set', [])
    for api_building_analysis in api_building_analytics:
        # find the corresponding BuildingAnalysis
        building_analysis = next(
            (ba for ba in better_building_analyses if ba.better_building_id == api_building_analysis['building_id']),
            None
        )
        building_analysis.better_analysis_id = api_building_analysis['id']

    return better_analysis_id


def _store_better_portfolio_analysis_results(better_analysis_id, better_building_analyses, context):
    """Stores results for portfolio analysis. Analysis should be completed before calling.

    :param better_analysis_id: int
    :param better_building_analyses: list[BuildingAnalysis]
    :param analysis: Analysis
    :param progress_data: ProgressData
    """
    results_dir, errors = context.client.get_portfolio_analysis_standalone_html(better_analysis_id)
    _check_errors(
        errors,
        'Failed to get BETTER portfolio analysis standalone HTML',
        context,
        fail_on_error=True
    )
    for result_file_path in pathlib.Path(results_dir.name).iterdir():
        with open(result_file_path, 'r') as f:
            if result_file_path.suffix != '.html':
                raise AnalysisPipelineException(
                    f'Received unhandled file type from BETTER: {result_file_path.name}'
                )

            content_type = AnalysisOutputFile.HTML
            file_ = BaseFile(f)
            analysis_output_file = AnalysisOutputFile(
                content_type=content_type,
            )
            padded_id = f'{context.analysis.id:06d}'
            analysis_output_file.file.save(f'better_portfolio_output_{padded_id}_{result_file_path.name}', file_)
            analysis_output_file.clean()
            analysis_output_file.save()
            # Since this is a portfolio analysis, add the result to all properties
            analysis_output_file.analysis_property_views.set([b.analysis_property_view_id for b in better_building_analyses])


def _run_better_building_analyses(better_building_analyses, analysis_config, context):
    """Runs building analysis for each building. Updates the BuildingAnalysis objects
    in better_building_analyses with the IDs of BETTER analyses created.

    :param better_building_analyses: list[BuildingAnalysis]
    :param analysis_config: dict, dictionary of required BETTER API body
    :param analysis: Analysis
    :param progress_data: ProgressData
    """
    for building_analysis in better_building_analyses:
        better_building_id = building_analysis.better_building_id
        analysis_property_view_id = building_analysis.analysis_property_view_id

        better_analysis_id, errors = context.client.create_and_run_building_analysis(
            better_building_id,
            analysis_config
        )
        if errors:
            _check_errors(
                errors,
                'Failed to run BETTER building analysis',
                context,
                analysis_property_view_id=analysis_property_view_id,
                fail_on_error=False,
            )
            # continue to next building
            continue

        # save the analysis ID so we can fetch and store the analysis results later
        building_analysis.better_analysis_id = better_analysis_id


def _store_better_building_analysis_results(better_building_analyses, context):
    """Stores results for building analysis. Analysis should be completed before calling.

    Specifically, it stores each building's standalone HTML file and links it to
    the analysis property view.
    It also stores each building's JSON analysis results in the analysis property view.

    :param better_building_analyses: list[BuildingAnalysis]
    :param analysis: Analysis
    :param progress_data: ProgressData
    """
    for building_analysis in better_building_analyses:
        better_building_id = building_analysis.better_building_id
        better_analysis_id = building_analysis.better_analysis_id
        analysis_property_view_id = building_analysis.analysis_property_view_id

        #
        # Store the standalone HTML
        #
        results_dir, errors = context.client.get_building_analysis_standalone_html(better_analysis_id)
        if errors:
            _check_errors(
                errors,
                'Failed to get BETTER building analysis standalone HTML',
                context,
                analysis_property_view_id=analysis_property_view_id,
                fail_on_error=False,
            )
            # continue to next building analysis
            continue

        for result_file_path in pathlib.Path(results_dir.name).iterdir():
            with open(result_file_path, 'r') as f:
                if result_file_path.suffix == '.html':
                    content_type = AnalysisOutputFile.HTML
                    file_ = BaseFile(f)
                else:
                    raise AnalysisPipelineException(
                        f'Received unhandled file type from better: {result_file_path.name}')

                analysis_output_file = AnalysisOutputFile(
                    content_type=content_type,
                )
                padded_id = f'{analysis_property_view_id:06d}'
                analysis_output_file.file.save(f'better_output_{padded_id}_{result_file_path.name}', file_)
                analysis_output_file.clean()
                analysis_output_file.save()
                analysis_output_file.analysis_property_views.set([analysis_property_view_id])

        #
        # Store the JSON results into the AnalysisPropertyView
        #
        results_dict, errors = context.client.get_building_analysis(better_building_id, better_analysis_id)
        if errors:
            _check_errors(
                errors,
                'Failed to get BETTER building analysis results',
                context,
                analysis_property_view_id=analysis_property_view_id,
                fail_on_error=False,
            )
            # continue to next building analysis
            continue

        analysis_property_view = AnalysisPropertyView.objects.get(id=analysis_property_view_id)
        analysis_property_view.parsed_results = results_dict
        analysis_property_view.save()


def _create_better_buildings(better_portfolio_id, context):
    """Create a BETTER building

    :param analysis: Analysis
    :param better_portfolio_id: int | None
    :return: list[BuildingAnalysis]
    """
    better_building_analyses = []
    for input_file in context.analysis.input_files.all():
        analysis_property_view_id = _parse_analysis_property_view_id(input_file.file.path)
        better_building_id, errors = context.client.create_building(input_file.file.path, better_portfolio_id)
        if errors:
            _check_errors(
                errors,
                f'Failed to create building for analysis property view {analysis_property_view_id}',
                context,
                analysis_property_view_id,
                fail_on_error=False
            )
            # go to next building
            continue

        better_building_analyses.append(
            BuildingAnalysis(
                analysis_property_view_id,
                better_building_id,
                None
            )
        )
        logger.info(f'Created BETTER building ({better_building_id}) for AnalysisPropertyView ({analysis_property_view_id})')

    return better_building_analyses
