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

from celery import chain, shared_task

from lxml import etree
from lxml.builder import ElementMaker

import requests


logger = logging.getLogger(__name__)

# map for translating SEED's model names into bsyncr's model names
# used for communicating with bsyncr service
BSYNCR_MODEL_TYPE_MAP = {
    'Simple Linear Regression': 'SLR',
    'Three Parameter Linear Model Cooling': '3PC',
    'Three Parameter Linear Model Heating': '3PH',
    'Four Parameter Linear Model': '4P',
}


def _validate_bsyncr_config(analysis):
    """Performs basic validation of the analysis for running bsyncr. Returns any
    errors

    :param analysis: Analysis
    :returns: list[str], list of validation error messages
    """
    config = analysis.configuration
    if not isinstance(config, dict):
        return ['Analysis configuration must be a dictionary/JSON']

    if 'model_type' not in config:
        return ['Analysis configuration missing required property "model_type"']

    model_type = config['model_type']
    if model_type not in BSYNCR_MODEL_TYPE_MAP:
        return [f'Analysis configuration.model_type "{model_type}" is invalid. '
                f'Must be one of the following: {", ".join(BSYNCR_MODEL_TYPE_MAP.keys())}']

    return []


class BsyncrPipeline(AnalysisPipeline):
    """
    BsyncrPipeline is a class for preparing, running, and post
    processing the bsyncr analysis by implementing the AnalysisPipeline's abstract
    methods.
    """

    def _prepare_analysis(self, property_view_ids, start_analysis=False):
        """Internal implementation for preparing bsyncr analysis"""
        if not settings.BSYNCR_SERVER_HOST:
            message = 'SEED instance is not configured to run bsyncr analysis. Please contact the server administrator.'
            self.fail(message, logger)
            raise AnalysisPipelineException(message)

        validation_errors = _validate_bsyncr_config(Analysis.objects.get(id=self._analysis_id))
        if validation_errors:
            raise AnalysisPipelineException(f'Unexpected error(s) while validating analysis configuration: {"; ".join(validation_errors)}')

        progress_data = self.get_progress_data()

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
        """Internal implementation for starting the bsyncr analysis"""

        progress_data = self.get_progress_data()

        # Steps:
        # 1) ...starting
        # 2) make requests to bsyncr
        # 3) process the results files
        progress_data.total = 3
        progress_data.save()

        chain(
            _start_analysis.si(self._analysis_id),
            _process_results.s(self._analysis_id),
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
    pipeline = BsyncrPipeline(analysis.id)
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

        bsync_doc, errors = _build_bsyncr_input(analysis_property_view, meter)
        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view.id,
                    user_message=f'Error preparing bsyncr input: {error}',
                    debug_message='',
                )
            continue

        analysis_input_file = AnalysisInputFile(
            content_type=AnalysisInputFile.BUILDINGSYNC,
            analysis=analysis
        )
        analysis_input_file.file.save(f'{analysis_property_view.id}.xml', ContentFile(bsync_doc))
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
    """A Celery task which finishes the preparation for bsyncr analysis

    :param analysis_id: int
    :param start_analysis: bool
    """
    pipeline = BsyncrPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready('Ready to run BSyncr')

    if start_analysis:
        pipeline.start_analysis()


# PREMISES_ID_NAME is the name of the custom ID used within a BuildingSync document
# to link it to SEED's AnalysisPropertyViews
PREMISES_ID_NAME = 'seed_analysis_property_view_id'


def _build_bsyncr_input(analysis_property_view, meter):
    """Constructs a BuildingSync document to be used as input for a bsyncr analysis.
    The function returns a tuple, the first value being the XML document as a byte
    string. The second value is a list of error messages.

    :param analysis_property_view: AnalysisPropertyView
    :param meter: Meter
    :returns: tuple(bytes, list[str])
    """
    errors = []
    property_state = analysis_property_view.property_state
    if property_state.longitude is None:
        errors.append('Linked PropertyState is missing longitude')
    if property_state.latitude is None:
        errors.append('Linked PropertyState is missing latitude')
    for meter_reading in meter.meter_readings.all():
        if meter_reading.reading is None:
            errors.append(f'MeterReading starting at {meter_reading.start_time} has no reading value')
    if errors:
        return None, errors

    XSI_URI = 'http://www.w3.org/2001/XMLSchema-instance'
    nsmap = {
        'xsi': XSI_URI,
    }
    nsmap.update(NAMESPACES)
    E = ElementMaker(
        namespace=BUILDINGSYNC_URI,
        nsmap=nsmap
    )

    elec_resource_id = 'Resource-Elec'
    doc = (
        E.BuildingSync(
            {
                etree.QName(XSI_URI, 'schemaLocation'): 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.2.0/BuildingSync.xsd',
                'version': '2.2.0'
            },
            E.Facilities(
                E.Facility(
                    {'ID': 'Facility-1'},
                    E.Sites(
                        E.Site(
                            {'ID': 'Site-1'},
                            E.Buildings(
                                E.Building(
                                    {'ID': 'Building-1'},
                                    E.PremisesName('My-Building'),
                                    E.PremisesIdentifiers(
                                        E.PremisesIdentifier(
                                            E.IdentifierLabel('Custom'),
                                            E.IdentifierCustomName(PREMISES_ID_NAME),
                                            E.IdentifierValue(str(analysis_property_view.id)),
                                        )
                                    ),
                                    E.Longitude(str(analysis_property_view.property_state.longitude)),
                                    E.Latitude(str(analysis_property_view.property_state.latitude)),
                                )
                            )
                        )
                    ),
                    E.Reports(
                        E.Report(
                            {'ID': 'Report-1'},
                            E.Scenarios(
                                E.Scenario(
                                    {'ID': 'Scenario-Measured'},
                                    E.ScenarioType(
                                        E.CurrentBuilding(
                                            E.CalculationMethod(
                                                E.Measured()
                                            )
                                        )
                                    ),
                                    E.ResourceUses(
                                        E.ResourceUse(
                                            {'ID': elec_resource_id},
                                            E.EnergyResource('Electricity'),
                                            E.ResourceUnits('kWh'),
                                            E.EndUse('All end uses')
                                        )
                                    ),
                                    E.TimeSeriesData(
                                        *[
                                            E.TimeSeries(
                                                {'ID': f'TimeSeries-{i}'},
                                                E.StartTimestamp(reading.start_time.isoformat()),
                                                E.IntervalFrequency('Month'),
                                                E.IntervalReading(str(reading.reading)),
                                                E.ResourceUseID({'IDref': elec_resource_id}),
                                            )
                                            for i, reading in enumerate(meter.meter_readings.all())
                                        ]
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )

    return etree.tostring(doc, pretty_print=True), []


def _parse_analysis_property_view_id(filepath):
    input_file_tree = etree.parse(filepath)
    id_xpath = f'//auc:PremisesIdentifier[auc:IdentifierCustomName = "{PREMISES_ID_NAME}"]/auc:IdentifierValue'
    analysis_property_view_id_elem = input_file_tree.xpath(id_xpath, namespaces=NAMESPACES)

    if len(analysis_property_view_id_elem) != 1:
        raise AnalysisPipelineException(f'Expected BuildlingSync file to have exactly one "{PREMISES_ID_NAME}" PremisesIdentifier')
    return int(analysis_property_view_id_elem[0].text)


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.QUEUED)
def _start_analysis(self, analysis_id):
    """Start bsyncr analysis by making requests to the service

    """
    pipeline = BsyncrPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step('Sending requests to bsyncr service')

    analysis = Analysis.objects.get(id=analysis_id)

    ANALYSIS_STATUS_CHECK_FREQUENCY = 5
    bsyncr_model_type = BSYNCR_MODEL_TYPE_MAP[analysis.configuration['model_type']]
    output_xml_file_ids = []
    for idx, input_file in enumerate(analysis.input_files.all()):
        if idx % ANALYSIS_STATUS_CHECK_FREQUENCY == 0:
            analysis.refresh_from_db()
            if analysis.in_terminal_state():
                raise StopAnalysisTaskChain('Analysis found to be in terminal state, stopping')

        analysis_property_view_id = _parse_analysis_property_view_id(input_file.file.path)
        results_dir, errors = _run_bsyncr_analysis(input_file.file, bsyncr_model_type)

        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view_id,
                    user_message='Unexpected error from bsyncr service',
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
                    raise AnalysisPipelineException(f'Received unhandled file type from bsyncr: {result_file_path.name}')

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
        message = 'Failed to get results for all properties'
        pipeline.fail(message, logger)
        # stop the task chain
        raise StopAnalysisTaskChain(message)

    return output_xml_file_ids


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _process_results(self, analysis_output_xml_file_ids, analysis_id):
    pipeline = BsyncrPipeline(analysis_id)
    progress_data = pipeline.get_progress_data()
    progress_data.step('Processing results')

    analysis_output_files = AnalysisOutputFile.objects.filter(id__in=analysis_output_xml_file_ids)
    for analysis_output_file in analysis_output_files.all():
        parsed_results = _parse_bsyncr_results(analysis_output_file.file.path)
        # assuming each output file is linked to only one analysis property view
        analysis_property_view = analysis_output_file.analysis_property_views.first()
        analysis_property_view.parsed_results = parsed_results
        analysis_property_view.save()


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.RUNNING)
def _finish_analysis(self, analysis_id):
    """A Celery task which finishes the analysis run

    :param analysis_id: int
    """
    pipeline = BsyncrPipeline(analysis_id)
    pipeline.set_analysis_status_to_completed()


def _parse_bsyncr_results(filepath):
    """Parses the XML file for key results

    :param filepath: str
    :returns: dict
    """
    def elem2dict(node):
        """
        Convert an lxml.etree node tree into a dict.
        Source: https://gist.github.com/jacobian/795571#gistcomment-2810160
        """
        result = {}
        for element in node.iterchildren():
            # Remove namespace prefix
            key = element.tag.split('}')[1] if '}' in element.tag else element.tag
            # Process element as tree element if the inner XML contains non-whitespace content
            if element.text and element.text.strip():
                value = element.text
            else:
                value = elem2dict(element)
            result[key] = value
        return result

    tree = etree.parse(filepath)
    parsed_models = []
    model_elems = tree.xpath('//auc:DerivedModel/auc:Models/auc:Model', namespaces=NAMESPACES)
    for model_elem in model_elems:
        parsed_models.append(elem2dict(model_elem))

    return {'models': parsed_models}


def _bsyncr_service_request(file_, model_type):
    """Makes request to bsyncr service using the provided file

    :param file_: File
    :param model_type: str
    :returns: requests.Response
    """
    files = [
        ('file', file_)
    ]

    return requests.request(
        method='POST',
        url=f'http://{settings.BSYNCR_SERVER_HOST}:{settings.BSYNCR_SERVER_PORT}/',
        files=files,
        params={'model_type': model_type},
        timeout=60 * 2,  # timeout after two minutes
    )


def _run_bsyncr_analysis(file_, model_type):
    """Runs the bsyncr analysis by making a request to a bsyncr server with the
    provided file. Returns a tuple, an object representing a temporary directory
    created with tempfile.TemporaryDirectory which contains the files returned by bsyncr
    followed by a list of error messages.

    :param file_: File
    :param model_type: str
    :returns: tuple, (object, list[str])
    """
    try:
        response = _bsyncr_service_request(file_, model_type)
    except requests.exceptions.Timeout:
        return None, ['Request to bsyncr server timed out.']
    except Exception as e:
        return None, [f'Failed to make request to bsyncr server: {e}']

    if response.status_code != 200:
        try:
            response_body = response.json()
            flattened_errors = [error['detail'] for error in response_body['errors']]
            return None, flattened_errors
        except (ValueError, KeyError):
            return None, [f'Expected JSON response with "errors" from bsyncr server but got the following: {response.text}']

    # get the files out of the returned zip
    temporary_results_dir = TemporaryDirectory()
    with TemporaryFile() as zip_fp:
        for chunk in response.iter_content(chunk_size=128):
            zip_fp.write(chunk)

        zip_fp.seek(0)
        with ZipFile(zip_fp) as zip_file:
            zip_file.extractall(path=temporary_results_dir.name)

    return temporary_results_dir, []
