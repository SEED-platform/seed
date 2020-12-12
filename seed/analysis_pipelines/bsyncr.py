# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.analysis_pipelines.pipeline import AnalysisPipeline, AnalysisPipelineException, task_create_analysis_property_views
from seed.building_sync.mappings import BUILDINGSYNC_URI, NAMESPACES
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    Analysis,
    AnalysisInputFile,
    AnalysisMessage,
    AnalysisPropertyView,
    Meter
)

from django.core.files.base import ContentFile
from django.db.models import Count

from celery import chain, shared_task

from lxml import etree
from lxml.builder import ElementMaker


class BsyncrPipeline(AnalysisPipeline):
    """
    BsyncrPipeline is a class for preparing, running, and post
    processing the bsyncr analysis by implementing the AnalysisPipeline's abstract
    methods.
    """

    def _prepare_analysis(self, analysis_id, property_view_ids):
        """Internal implementation for preparing bsyncr analysis"""
    
        progress_data = ProgressData('prepare-analysis-bsyncr', analysis_id)

        # Steps:
        # 1) ...starting
        # 2) create AnalysisPropertyViews
        # 3) create input files for each property
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(analysis_id, property_view_ids, progress_data.key),
            _prepare_all_properties.s(analysis_id, progress_data.key),
            _finish_preparation.si(analysis_id, progress_data.key)
        ).apply_async()

        return progress_data.key


@shared_task
def _prepare_all_properties(analysis_property_view_ids, analysis_id, progress_data_key):
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
        try:
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
                AnalysisMessage.objects.create(
                    analysis=analysis,
                    analysis_property_view=analysis_property_view,
                    type=AnalysisMessage.DEFAULT,
                    user_message='Property has no linked electricity meters with 12 or more readings'
                )
                continue

            # arbitrarily choosing the first meter for now
            meter = meters[0]

            bsync_doc, errors = _build_bsyncr_input(analysis_property_view, meter)
            if errors:
                for error in errors:
                    AnalysisMessage.objects.create(
                        analysis=analysis,
                        analysis_property_view=analysis_property_view,
                        type=AnalysisMessage.DEFAULT,
                        user_message=error
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
        except Exception as e:
            AnalysisMessage.objects.create(
                analysis=analysis,
                analysis_property_view=analysis_property_view,
                type=AnalysisMessage.DEFAULT,
                user_message='Unexpected error',
                debug_message=str(e),
            )
            pass

    if len(input_file_paths) == 0:
        pipeline = BsyncrPipeline(analysis.id)
        message = 'No files were able to be prepared for the analysis'
        pipeline.fail(message)
        # stop the task chain
        raise AnalysisPipelineException(message)


@shared_task
def _finish_preparation(analysis_id, progress_data_key):
    """A Celery task which finishes the preparation for bsyncr analysis

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
