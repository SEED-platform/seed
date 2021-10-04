# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
import logging
from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    task_create_analysis_property_views,
    analysis_pipeline_task
)
from seed.models import (
    Analysis,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    Meter,
    MeterReading,
    PropertyView
)

logger = logging.getLogger(__name__)

ERROR_INVALID_METER_READINGS = 0
ERROR_OVERLAPPING_METER_READINGS = 1
ERROR_NO_VALID_PROPERTIES = 2
WARNING_SOME_INVALID_PROPERTIES = 3

EUI_ANALYSIS_MESSAGES = {
    ERROR_INVALID_METER_READINGS: 'Property view skipped (no linked electricity meters with readings).',
    ERROR_OVERLAPPING_METER_READINGS: 'Property view skipped (meter has overlapping readings).',
    ERROR_NO_VALID_PROPERTIES: 'Analysis found no valid properties.',
    WARNING_SOME_INVALID_PROPERTIES: 'Some properties failed to validate.'
}

VALID_METERS = [Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_SOLAR, Meter.ELECTRICITY_WIND]
TIME_PERIOD = datetime.timedelta(days=365)


def _get_valid_meters(property_view_ids):
    """Performs basic validation of the properties for running Average Annual CO2 and returns any errors.

    :param analysis: property_view_ids
    :returns: dictionary[id:str], dictionary of property_view_ids to error message
    """
    invalid_area = []
    invalid_meter = []
    overlapping_meter = []
    meter_readings_by_property_view = {}
    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    for property_view in property_views:

        # ensure we have Gross Floor Area on this property view's state
        if property_view.state.gross_floor_area is None:
            invalid_area.append(property_view.id)
            continue

        # get the most recent electric meter reading's end_time
        try:
            end_time = MeterReading.objects.filter(
                meter__property=property_view.property,
                meter__type__in=VALID_METERS
            ).order_by('end_time').last().end_time
        except Exception:
            invalid_meter.append(property_view.id)
            continue

        # get all readings that started AND ended between end_time and a year prior
        meter_readings_by_meter = {}
        for meter_reading in MeterReading.objects.filter(
            meter__property=property_view.property,
            meter__type__in=VALID_METERS,
            end_time__lte=end_time,
            start_time__gte=end_time - TIME_PERIOD
        ).order_by('start_time'):
            if meter_reading.meter.id not in meter_readings_by_meter:
                meter_readings_by_meter[meter_reading.meter.id] = []
            meter_readings_by_meter[meter_reading.meter.id].append(meter_reading)

        # generate summary per meter
        done = False
        readings_by_meter = {}
        for meter_id in meter_readings_by_meter:
            last_reading = None
            total_time = 0
            total_reading = 0
            for reading in meter_readings_by_meter[meter_id]:

                # ensure no overlapping readings per meter
                if last_reading is not None:
                    if last_reading.end_time > reading.start_time:
                        overlapping_meter.append(property_view.id)
                        done = True
                        break

                last_reading = reading
                total_time += (reading.end_time - reading.start_time).total_seconds()
                total_reading += reading.reading
            if done:
                continue
            readings_by_meter[meter_id] = {'time': total_time, 'reading': total_reading}

        # done with this property_view
        if readings_by_meter:
            meter_readings_by_property_view[property_view.id] = readings_by_meter

    errors_by_property_view_id = {}
    for pid in invalid_area:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_GROSS_FLOOR_AREA])
    for pid in invalid_meter:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_METER_READINGS])
    for pid in overlapping_meter:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_OVERLAPPING_METER_READINGS])

    return meter_readings_by_property_view, errors_by_property_view_id


def _calculate_co2(meter_readings):
    return {
        'average': 0,
        'reading': 0,
        'coverage': 0
    }

class CO2Pipeline(AnalysisPipeline):

    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # current implemtation will *always* start the analysis immediately

        meter_readings_by_property_view, errors_by_property_view_id = _get_valid_meters(property_view_ids)
        if not meter_readings_by_property_view:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=EUI_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES],
                debug_message=''
            )
            analysis = Analysis.objects.get(id=self._analysis_id)
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineException(EUI_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES])

        if errors_by_property_view_id:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.WARNING,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=EUI_ANALYSIS_MESSAGES[WARNING_SOME_INVALID_PROPERTIES],
                debug_message=''
            )

        progress_data = self.get_progress_data()
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids),
            _finish_preparation.s(meter_readings_by_property_view, errors_by_property_view_id, self._analysis_id),
            _run_analysis.s(self._analysis_id)
        ).apply_async()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, meter_readings_by_property_view, errors_by_property_view_id, analysis_id):
    pipeline = CO2Pipeline(analysis_id)
    pipeline.set_analysis_status_to_ready('Ready to run Average Annual CO2 analysis')

    # attach errors to respective analysis_property_views
    if errors_by_property_view_id:
        for pid in errors_by_property_view_id:
            analysis_view_id = analysis_view_ids_by_property_view_id[pid]
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_view_id,
                user_message="  ".join(errors_by_property_view_id[pid]),
                debug_message=''
            )

    # replace property_view id with analysis_property_view id in meter lookup
    meter_readings_by_analysis_property_view = {}
    for property_view in meter_readings_by_property_view:
        analysis_view_id = analysis_view_ids_by_property_view_id[property_view]
        meter_readings_by_analysis_property_view[analysis_view_id] = meter_readings_by_property_view[property_view]

    return meter_readings_by_analysis_property_view


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, meter_readings_by_analysis_property_view, analysis_id):
    pipeline = CO2Pipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step('Calculating Average Annual CO2')
    analysis = Analysis.objects.get(id=analysis_id)

    # make sure we have the extra data columns we need
    Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_co2',
        display_name='Average Annual CO2 (kgCO2e)',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_co2_coverage',
        display_name='Average Annual CO2 Coverage (% of the year)',
        organization=analysis.organization,
        table_name='PropertyState',
    )

    # for some reason the keys, which should be ids (ie integers), get turned into strings... let's fix that here
    meter_readings_by_analysis_property_view = {int(key): value for key, value in meter_readings_by_analysis_property_view.items()}
    analysis_property_view_ids = list(meter_readings_by_analysis_property_view.keys())

    # prefetching property and cycle b/c .get_property_views() uses them (this is not "clean" but whatever)
    analysis_property_views = AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids).prefetch_related('property', 'cycle', 'property_state')
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # create and save EUIs for each property view
    for analysis_property_view in analysis_property_views:
        area = analysis_property_view.property_state.gross_floor_area.magnitude
        meter_readings = meter_readings_by_analysis_property_view[analysis_property_view.id]
        co2 = _calculate_co2(meter_readings)

        analysis_property_view.parsed_results = {
            'Average Annual CO2 (kgCO2e)': co2['average'],
            'Annual Coverage %': co2['coverage'],
            'Total Annual Meter Reading (kBtu)': co2['reading']
        }
        analysis_property_view.save()

        property_view = property_views_by_apv_id[analysis_property_view.id]
        property_view.state.extra_data.update({'analysis_co2': co2['average']})
        property_view.state.extra_data.update({'analysis_co2_coverage': co2['coverage']})
        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()
