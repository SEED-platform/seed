# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import pathlib
from tempfile import TemporaryDirectory, NamedTemporaryFile

import polling
from django.conf import settings
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
from django.db.models import Count
from django.utils import timezone as tz

from celery import chain, shared_task

from lxml import etree
from lxml.builder import ElementMaker

import json
import requests

logger = logging.getLogger(__name__)

HOST = "https://better-lbnl-development.herokuapp.com"
# BETTER and ESPM use different names for property types than BEDES and BSync
BETTER_TO_BSYNC_PROPERTY_TYPE = {
    'Office': 'Office',
    'Hotel': 'Lodging',
    'K-12 School': 'Education',
    'Hospital (General Medical & Surgical)': 'Health care-Inpatient hospital',
    'Bank Branch': 'Bank',
    'Courthouse': 'Courthouse',
    'Data Center': 'Data Center',
    'Distribution Center': 'Distribution Center',
    'Financial Office': 'Office-Financial',
    'Multifamily Housing': 'Multifamily',
    'Non-Refrigerated Warehouse': 'Warehouse unrefrigerated',
    'Refrigerated Warehouse': 'Warehouse refrigerated',
    'Retail Store': 'Retail',
    'Senior Care Community': 'Health care-Skilled nursing facility',
    'Supermarket/Grocery Store': 'Food sales-Grocery store',
    'Other': 'Other'
}


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
        # 2) make requests to better
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
                type__in=[Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_SOLAR, Meter.ELECTRICITY_WIND, Meter.NATURAL_GAS],
                readings_count__gte=12,
            )
        )
        if meters.count() == 0:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.INFO,
                analysis_id=analysis.id,
                analysis_property_view_id=analysis_property_view.id,
                user_message='Property not used in analysis: Property has no linked electricity or natural gas meters '
                             'with 12 or more readings',
                debug_message=''
            )
            continue

        better_doc, errors = _build_better_input(analysis_property_view, meters)
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


def _build_better_input(analysis_property_view, meters):
    """Constructs a BuildingSync document to be used as input for a BETTER analysis.
    The function returns a tuple, the first value being the XML document as a byte
    string. The second value is a list of error messages.

    :param analysis_property_view: AnalysisPropertyView
    :param meter: Meter
    :returns: tuple(bytes, list[str])
    """
    # TODO Refine ID assignment
    errors = []
    property_state = analysis_property_view.property_state

    if property_state.property_name is None:
        errors.append('Linked PropertyState is missing a name')
    if property_state.city is None:
        errors.append('Linked PropertyState is missing a city')
    if property_state.state is None:
        errors.append('Linked PropertyState is missing a State')
    if property_state.gross_floor_area is None:
        errors.append('Linked PropertyState is missing a gross floor area')
    if property_state.property_type is None:
        errors.append('Linked PropertyState is missing a property type')
    if property_state.property_type not in BETTER_TO_BSYNC_PROPERTY_TYPE:
        errors.append(f'Linked PropertyState must have property type of: {", ".join(BETTER_TO_BSYNC_PROPERTY_TYPE.keys())}')
    for meter in meters:
        for meter_reading in meter.meter_readings.all():
            if meter_reading.reading is None:
                errors.append(f'{meter}: MeterReading starting at {meter_reading.start_time} has no reading value')
    if errors:
        return None, errors

    # clean inputs
    # BETTER will default if eGRIDRegion is not explicitly set
    try:
        eGRIDRegion = property_state.extra_data['eGRIDRegion']
    except KeyError:
        eGRIDRegion = ""

    property_type = BETTER_TO_BSYNC_PROPERTY_TYPE[property_state.property_type]

    gross_floor_area = str(int(property_state.gross_floor_area.magnitude))

    XSI_URI = 'http://www.w3.org/2001/XMLSchema-instance'
    nsmap = {
        'xsi': XSI_URI,
    }
    nsmap.update(NAMESPACES)
    E = ElementMaker(
        namespace=BUILDINGSYNC_URI,
        nsmap=nsmap
    )

    doc = (
        E.BuildingSync(
            {
                etree.QName(XSI_URI,
                            'schemaLocation'): 'http://buildingsync.net/schemas/bedes-auc/2019 https://raw.github.com/BuildingSync/schema/v2.2.0/BuildingSync.xsd',
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
                                    E.PremisesName(property_state.property_name),
                                    E.PremisesIdentifiers(
                                        E.PremisesIdentifier(
                                            E.IdentifierLabel('Custom'),
                                            E.IdentifierCustomName(PREMISES_ID_NAME),
                                            E.IdentifierValue(str(analysis_property_view.id)),
                                        )
                                    ),
                                    E.Address(
                                        E.City(property_state.city),
                                        E.State(property_state.state),
                                        E.PostalCode(property_state.postal_code)
                                    ),
                                    E.eGRIDRegionCode(eGRIDRegion),
                                    E.Longitude(str(analysis_property_view.property_state.longitude)),
                                    E.Latitude(str(analysis_property_view.property_state.latitude)),
                                    E.OccupancyClassification(property_type),
                                    E.FloorAreas(
                                        E.FloorArea(
                                            E.FloorAreaType("Gross"),
                                            E.FloorAreaValue(gross_floor_area)
                                        )
                                    ),
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
                                            {'ID': 'Resource-' + str(11)},
                                            E.EnergyResource('Electricity'),
                                            E.ResourceUnits('kWh'),
                                            E.EndUse('All end uses')
                                        ),
                                        E.ResourceUse(
                                            {'ID': 'Resource-' + str(19)},
                                            E.EnergyResource('Natural gas'),
                                            E.ResourceUnits('MMBtu'),
                                            E.EndUse('Heating')
                                        ),
                                    ),
                                    E.TimeSeriesData(
                                        *[
                                            E.TimeSeries(
                                                {'ID': f'TimeSeries-{meter.type}-{i}'},
                                                E.ReadingType('Total'),
                                                E.StartTimestamp(reading.start_time.isoformat()),
                                                E.EndTimestamp(reading.end_time.isoformat()),
                                                E.IntervalFrequency('Month'),
                                                E.IntervalReading(str(reading.reading)),
                                                E.ResourceUseID({'IDref': 'Resource-' + str(meter.type)}),
                                            )
                                            for meter in meters for i, reading in enumerate(meter.meter_readings.all())
                                        ]
                                    ),
                                    E.LinkedPremises(
                                        E.Building(
                                            E.LinkedBuildingID({'IDref': 'Building-1'})
                                        )

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
        "benchmark_data": analysis.configuration['benchmark_data']['benchmark_data'],
        "savings_target": analysis.configuration['savings_target']['savings_target'],
        "min_model_r_squared": analysis.configuration['min_r_squared']
    }
    output_html_file_ids = []
    for input_file in analysis.input_files.all():
        analysis_property_view_id = _parse_analysis_property_view_id(input_file.file.path)
        better_building_id = _better_building_service_request(input_file.file.path)
        better_analysis_id, errors = _run_better_analysis(better_building_id, analysis_config)
        results_dir, errors = _better_report_service_request(better_analysis_id)

        if errors:
            for error in errors:
                AnalysisMessage.log_and_create(
                    logger=logger,
                    type_=AnalysisMessage.ERROR,
                    analysis_id=analysis.id,
                    analysis_property_view_id=analysis_property_view_id,
                    user_message='Unexpected error from better service',
                    debug_message=error,
                )
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

                if content_type == AnalysisOutputFile.HTML:
                    output_html_file_ids.append(analysis_output_file.id)

    if len(output_html_file_ids) == 0:
        pipeline = BETTERPipeline(analysis.id)
        message = 'Failed to get results for all properties'
        pipeline.fail(message, logger, progress_data_key=progress_data.key)
        # stop the task chain
        raise StopAnalysisTaskChain(message)

    return output_html_file_ids


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


def _better_building_service_request(bsync_xml):
    """Makes request to better building endpoint using the provided file

    :param bsync_xml: BSync xml for property
    :returns: requests.Response building_id
    """
    url = "{host}/api/v1/buildings/".format(host=HOST)

    with open(bsync_xml, 'r') as file:
        bsync_content = file.read()

    headers = {
        'Authorization': settings.BETTER_TOKEN,
        'Content-Type': 'buildingsync/xml',
    }
    try:
        response = requests.request("POST", url, headers=headers, data=bsync_content)
        if response.status_code == 201:
            data = response.json()
            building_id = data['id']
        else:
            raise Exception(f'Received non 2xx status from BETTER: {response.status_code}: {response.content}')
    except Exception as e:
        message = 'BETTER service could not create building with the following message: {e}'.format(e=e)
        raise AnalysisPipelineException(message)

    return building_id


def _better_analysis_service_request(building_id, config):
    """Makes request to better analysis endpoint using the provided configuration

    :params: request body with building_id, savings_target, benchmark_data, min_model_r_squared
    :returns: requests.Response
    """

    url = "{host}/api/v1/buildings/{id}/analytics/".format(host=HOST, id=building_id)

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }

    try:
        response = requests.request("POST", url, headers=headers, data=json.dumps(config))
    except ConnectionError:
        message = 'BETTER service could not create analytics for this building'
        raise AnalysisPipelineException(message)

    return response


def _better_report_service_request(analysis_id):
    """Makes request to better html report endpoint using the provided analysis_id

    :params: analysis id
    :returns: tuple(tempfile.TemporaryDirectory, list[str]), temporary directory containing result files and list of error messages
    """
    url = "{host}/api/v1/standalone_html/building_analytics/{id}/".format(host=HOST, id=analysis_id)

    headers = {
        'accept': '*/*',
        'Authorization': settings.BETTER_TOKEN,
    }
    try:
        response = requests.request("GET", url, headers=headers)
        standalone_html = response.text.encode('utf8').decode()

    except ConnectionError:
        message = 'BETTER service could not find the analysis'
        raise AnalysisPipelineException(message)

    # save the file from the response
    temporary_results_dir = TemporaryDirectory()
    with NamedTemporaryFile(mode='w', suffix='.html', dir=temporary_results_dir.name, delete=False) as file:
        file.write(standalone_html)

    return temporary_results_dir, []


def _run_better_analysis(building_id, config):
    """Runs the better analysis by making a request to a better server with the
    provided configuration. Returns the analysis id for standalone html

    :param building_id: BETTER building id analysis configuration
    :param config: dict
    :returns: better_analysis_pk
    """
    try:
        response = _better_analysis_service_request(building_id, config)
    except Exception as e:
        return None, [f'Failed to make request to better server: {e}']

    if response.status_code != 201:
        return None, ['BETTER analysis could not be completed and got the following response: {message}'.format(
            message=response.text)]

    # Gotta make sure the analysis is done
    url = "{host}/api/v1/buildings/{id}/analytics/".format(host=HOST, id=building_id)

    headers = {
        'accept': 'application/json',
        'Authorization': settings.BETTER_TOKEN,
    }
    try:
        response = polling.poll(
            lambda: requests.request("GET", url, headers=headers),
            check_success=lambda response: response.json()[0]['generation_result'] == 'COMPLETE',
            timeout=60,
            step=1)
    except TimeoutError:
        return None, ['BETTER analysis timed out']

    data = response.json()
    better_analysis_id = data[0]['id']
    return better_analysis_id, []
