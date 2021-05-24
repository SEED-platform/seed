# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from tempfile import TemporaryFile, TemporaryDirectory
import logging
import pathlib
from zipfile import ZipFile

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    task_create_analysis_property_views,
    analysis_pipeline_task,
    StopAnalysisTaskChain
)
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    Analysis,
    AnalysisInputFile,
    AnalysisMessage,
    AnalysisOutputFile,
    AnalysisPropertyView,
    Meter
)

from django.core.files.base import ContentFile, File as BaseFile
from django.core.files.images import ImageFile
from django.db.models import Count
from django.conf import settings
from django.utils import timezone as tz

from celery import chain, shared_task

from lxml import etree
from lxml.builder import ElementMaker

import requests

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

    if 'min_r_squared' not in config:
        return ['Analysis configuration missing required property "min_r_squared"']

    return []


class BETTERPipeline(AnalysisPipeline):
    """
    BETTERPipeline is a class for preparing, running, and post
    processing BETTER analysis by implementing the AnalysisPipeline's abstract
    methods.
    """

    def _prepare_analysis(self, property_view_ids):
        """Internal implementation for preparing better analysis"""

        validation_errors = _validate_better_config(Analysis.objects.get(id=self._analysis_id))
        if validation_errors:
            raise AnalysisPipelineException(
                f'Unexpected error(s) while validating analysis configuration: {"; ".join(validation_errors)}')

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
        # 2) make requests to bsyncr
        # 3) process the results files
        progress_data.total = 3
        progress_data.save()

        chain(
            _start_analysis.si(self._analysis_id, progress_data.key),
            _finish_analysis.si(self._analysis_id, progress_data.key),
        ).apply_async()

        return progress_data.result()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _prepare_all_properties(self, analysis_property_view_ids, analysis_id, progress_data_key):
    """A Celery task which attempts to make BuildingSync files for all AnalysisPropertyViews.

    :param analysis_property_view_ids: list[int]
    :param analysis_id: int
    :param progress_data_key: str
    :returns: void
    """
    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Creating files for analysis')

    analysis = Analysis.objects.get(id=analysis_id)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
    input_file_paths = []
    for analysis_property_view in analysis_property_views:
        meters = (
            Meter.objects
                .annotate(readings_count=Count('meter_readings'))
                .filter(
                property=analysis_property_view.property,
                type__in=[Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_SOLAR, Meter.ELECTRICITY_WIND],
                readings_count__gte=12,
            )
        )
        if meters.count() == 0:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.INFO,
                analysis_id=analysis.id,
                analysis_property_view_id=analysis_property_view.id,
                user_message='Property not used in analysis: Property has no linked electricity meters with 12 or more readings',
                debug_message=''
            )
            continue

        # arbitrarily choosing the first meter for now
        meter = meters[0]

        better_doc, errors = _build_better_input(analysis_property_view, meter)
        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view.id,
                    user_message=f'Error preparing better input: {error}',
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


# PREMISES_ID_NAME is the name of the custom ID used within a BuildingSync document
# to link it to SEED's AnalysisPropertyViews
PREMISES_ID_NAME = 'seed_analysis_property_view_id'


def _build_better_input(analysis_property_view, meter):
    """Constructs a BuildingSync document to be used as input for a BETTER analysis.
    The function returns a tuple, the first value being the XML document as a byte
    string. The second value is a list of error messages.

    :param analysis_property_view: AnalysisPropertyView
    :param meter: Meter
    :returns: tuple(bytes, list[str])
    """
    # TODO Build BETTER bsync input xml
    return True

def _parse_analysis_property_view_id(filepath):
    input_file_tree = etree.parse(filepath)
    id_xpath = f'//auc:PremisesIdentifier[auc:IdentifierCustomName = "{PREMISES_ID_NAME}"]/auc:IdentifierValue'
    analysis_property_view_id_elem = input_file_tree.xpath(id_xpath, namespaces=NAMESPACES)

    if len(analysis_property_view_id_elem) != 1:
        raise AnalysisPipelineException(
            f'Expected BuildlingSync file to have exactly one "{PREMISES_ID_NAME}" PremisesIdentifier')
    return int(analysis_property_view_id_elem[0].text)


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.QUEUED)
def _start_analysis(self, analysis_id, progress_data_key):
    """Start better analysis by making requests to the service

    """
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.RUNNING
    analysis.start_time = tz.now()
    analysis.save()

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Sending requests to BETTER service')

    analysis_config = {
        'benchmark_data': analysis.configuration['benchmark_data'],
        'savings_target': analysis.configuration['savings_target'],
        'min_r_squared': analysis.configuration['min_r_squared']
    }

    output_xml_file_ids = []
    for input_file in analysis.input_files.all():
        analysis_property_view_id = _parse_analysis_property_view_id(input_file.file.path)
        better_building_id = _better_building_service_request(input_file.file.path)
        results_dir, errors = _run_better_analysis(better_building_id, analysis_config)

        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view_id,
                    user_message='Unexpected error from BETTER service',
                    debug_message=error,
                )
            continue

        for result_file_path in pathlib.Path(results_dir.name).iterdir():
            with open(result_file_path, 'rb') as f:
                if result_file_path.suffix == '.xml':
                    content_type = AnalysisOutputFile.BUILDINGSYNC
                    file_ = BaseFile(f)
                elif result_file_path.suffix == '.png':
                    content_type = AnalysisOutputFile.IMAGE_PNG
                    file_ = ImageFile(f)
                else:
                    raise AnalysisPipelineException(
                        f'Received unhandled file type from bsyncr: {result_file_path.name}')

                analysis_output_file = AnalysisOutputFile(
                    content_type=content_type,
                )
                padded_id = f'{analysis_property_view_id:06d}'
                analysis_output_file.file.save(f'bsyncr_output_{padded_id}_{result_file_path.name}', file_)
                analysis_output_file.clean()
                analysis_output_file.save()
                analysis_output_file.analysis_property_views.set([analysis_property_view_id])

                if content_type == AnalysisOutputFile.BUILDINGSYNC:
                    output_xml_file_ids.append(analysis_output_file.id)

    if len(output_xml_file_ids) == 0:
        pipeline = BETTERPipeline(analysis.id)
        message = 'Failed to get results for all properties'
        pipeline.fail(message, logger, progress_data_key=progress_data.key)
        # stop the task chain
        raise StopAnalysisTaskChain(message)

    return output_xml_file_ids


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


def _better_analysis_service_request(building_id, config):
    """Makes request to better analysis endpoint using the provided configuration

    :params: request body with building_id, savings_target, benchmark_data, min_model_r_squared
    :returns: requests.Response
    """

    # TODO: Add actual BETTER endpoint here
    return True


def _better_building_service_request(file_):
    """Makes request to better building endpoint using the provided file

    :param file_: File
    :returns: requests.Response building_id
    """
    files = [
        ('file', file_)
    ]
    # TODO: Add actual BETTER endpoint here

    return True


def _run_better_analysis(building_id, config):
    """Runs the better analysis by making a request to a better server with the
    provided configuration. Returns a self contained html file

    :param building_id: BETTER building id analysis configuration
    :param config: dict
    :returns: TBD
    """
    try:
        response = _better_analysis_service_request(building_id, config)
    except requests.exceptions.Timeout:
        return None, ['Request to better server timed out.']
    except Exception as e:
        return None, [f'Failed to make request to better server: {e}']

    if response.status_code != 200:
        try:
            response_body = response.json()
            flattened_errors = [error['detail'] for error in response_body['errors']]
            return None, flattened_errors
        except (ValueError, KeyError):
            return None, [
                f'Expected JSON response with "errors" from better server but got the following: {response.text}']

    # TODO get the self contained html file from the response
    return response
