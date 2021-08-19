# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from celery import chain, shared_task
from django.db.models import Count
from django.utils import timezone as tz

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    task_create_analysis_property_views,
    analysis_pipeline_task
)
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    Analysis,
    AnalysisMessage,
    AnalysisPropertyView,
    Meter,
    MeterReading,
    PropertyState,
    PropertyView
)

logger = logging.getLogger(__name__)

ERROR_INVALID_GROSS_FLOOR_AREA = 0
ERROR_INSUFFICIENT_METER_READINGS = 1
ERROR_INVALID_METER_READINGS = 2
ERROR_NO_VALID_PROPERTIES = 3
WARNING_SOME_INVALID_PROPERTIES = 4

EUI_ANALYSIS_MESSAGES = {
    ERROR_INVALID_GROSS_FLOOR_AREA: 'Property view skipped (invalid Gross Floor Area).',
    ERROR_INSUFFICIENT_METER_READINGS: 'Property view skipped (no linked electricity meters with 12 or more readings).',
    ERROR_INVALID_METER_READINGS: 'Property view skipped (no linked electricity meters with 12 months of consecutive readings).',
    ERROR_NO_VALID_PROPERTIES: 'Analysis found no valid properties.',
    WARNING_SOME_INVALID_PROPERTIES: 'Some properties failed to validate.'
}


def _get_valid_meters(property_view_ids):
    """Performs basic validation of the properties for running EUI and returns any errors.

    :param analysis: property_view_ids
    :returns: dictionary[id:str], dictionary of property_view_ids to error message
    """
    invalid_area = []
    invalid_meter_1 = []
    invalid_meter_2 = []
    meter_readings_by_property_view = {}
    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    for property_view in property_views:

        # ensure we have Gross Floor Area on this property view's state
        if property_view.state.gross_floor_area is None:
            invalid_area.append(property_view.id)
            continue

        # ensure we have at least 1 meter with 12 readings
        meters = (
            Meter.objects
            .annotate(readings_count=Count('meter_readings'))
            .filter(
                property=property_view.property,
                type__in=[Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_SOLAR, Meter.ELECTRICITY_WIND],
                readings_count__gte=12,
            )
        )
        if meters.count() == 0:
            invalid_meter_1.append(property_view.id)
            continue

        # ensure one found meter has at least 12 consecutive monthly readings
        meter_readings = []
        for meter in meters:
            previous_month = 0
            streak = 0
            for meter_reading in MeterReading.objects.filter(meter=meter).order_by('-start_time'):
                current_month = meter_reading.start_time.month

                # if previous month is wrong, start streak over
                if previous_month != 0 and previous_month != current_month + 1:
                    previous_month = 0
                    streak = 0
                    meter_readings = []
                    continue

                # readings are already normalized to kBtu on import so we only need the reading value
                meter_readings.append(meter_reading.reading)
                previous_month = meter_reading.start_time.month
                streak = streak + 1

                # just use the most recent 12 months found
                if streak >= 12:
                    break

            # just use the first meter found
            if streak >= 12:
                break

        if streak < 12:
            invalid_meter_2.append(property_view.id)
            continue
        meter_readings.reverse()
        meter_readings_by_property_view[property_view.id] = meter_readings

    errors_by_property_view_id = {}
    for pid in invalid_area:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_GROSS_FLOOR_AREA])
    for pid in invalid_meter_1:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INSUFFICIENT_METER_READINGS])
    for pid in invalid_meter_2:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_METER_READINGS])

    return meter_readings_by_property_view, errors_by_property_view_id

def _calculate_eui(meter_readings, gross_floor_area):
    return round(sum(meter_readings) / gross_floor_area, 4)


class EUIPipeline(AnalysisPipeline):

    def _prepare_analysis(self, property_view_ids):
        meter_readings_by_property_view, errors_by_property_view_id = _get_valid_meters(property_view_ids)

        if not meter_readings_by_property_view:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=EUI_ANALYSIS_MESSAGES.ERROR_NO_VALID_PROPERTIES,
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

        progress_data = ProgressData('prepare-analysis-eui', self._analysis_id)
        progress_data.total = 3
        progress_data.save()

        chain(
            task_create_analysis_property_views.si(self._analysis_id, property_view_ids, progress_data.key),
            _finish_preparation.s(meter_readings_by_property_view, errors_by_property_view_id, self._analysis_id, progress_data.key),
            _run_analysis.s(self._analysis_id, progress_data.key)
        ).apply_async()

        return progress_data.result()

    def _start_analysis(self):
        return None


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.CREATING)
def _finish_preparation(self, analysis_view_ids_by_property_view_id, meter_readings_by_property_view, errors_by_property_view_id, analysis_id, progress_data_key):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.READY
    analysis.save()

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

    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.finish_with_success()

    return meter_readings_by_analysis_property_view


@shared_task(bind=True)
@analysis_pipeline_task(Analysis.READY)
def _run_analysis(self, meter_readings_by_analysis_property_view, analysis_id, progress_data_key):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = Analysis.RUNNING
    analysis.start_time = tz.now()
    analysis.save()
    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.step('Caclulating EUI')

    for analysis_property_view_id in meter_readings_by_analysis_property_view:
        analysis_property_view = AnalysisPropertyView.objects.get(id=analysis_property_view_id)
        property_state = PropertyState.objects.get(id=analysis_property_view.property_state.id)
        analysis_property_view.parsed_results = {
            'EUI': _calculate_eui(meter_readings_by_analysis_property_view[analysis_property_view_id], property_state.gross_floor_area.magnitude),
            'Total Yearly Meter Reading': sum(meter_readings_by_analysis_property_view[analysis_property_view_id]),
            'Gross Floor Area': property_state.gross_floor_area.magnitude
        }
        analysis_property_view.save()

    # all done!
    analysis.status = Analysis.COMPLETED
    analysis.end_time = tz.now()
    analysis.save()
    progress_data = ProgressData.from_key(progress_data_key)
    progress_data.finish_with_success()
