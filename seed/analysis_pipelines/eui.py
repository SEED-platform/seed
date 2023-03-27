# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import datetime
import logging

from celery import chain, shared_task

from seed.analysis_pipelines.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineException,
    analysis_pipeline_task,
    task_create_analysis_property_views
)
from seed.analysis_pipelines.utils import (
    SimpleMeterReading,
    get_days_in_reading
)
from seed.models import (
    Analysis,
    AnalysisMessage,
    AnalysisPropertyView,
    Column,
    Cycle,
    Meter,
    MeterReading,
    PropertyView
)

logger = logging.getLogger(__name__)

ERROR_INVALID_GROSS_FLOOR_AREA = 0
ERROR_INVALID_METER_READINGS = 1
ERROR_NO_VALID_PROPERTIES = 3
WARNING_SOME_INVALID_PROPERTIES = 4

EUI_ANALYSIS_MESSAGES = {
    ERROR_INVALID_GROSS_FLOOR_AREA: 'Property skipped (invalid Gross Floor Area).',
    ERROR_INVALID_METER_READINGS: 'Property view skipped (no linked electricity meters with readings).',
    ERROR_NO_VALID_PROPERTIES: 'Analysis found no valid properties.',
    WARNING_SOME_INVALID_PROPERTIES: 'Some properties failed to validate.'
}

VALID_METERS = [Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_SOLAR, Meter.ELECTRICITY_WIND, Meter.ELECTRICITY_UNKNOWN]
TIME_PERIOD = datetime.timedelta(days=365)


def _get_valid_meters(property_view_ids, config):
    """Performs basic validation of the properties for running EUI and returns any errors.

    :param analysis: property_view_ids
    :returns: dictionary[id:str], dictionary of property_view_ids to error message
    """
    invalid_area = []
    invalid_meter = []
    meter_readings_by_property_view = {}

    select_meters = config.get("select_meters")
    if select_meters == "all":
        pass  # different for each view
    elif select_meters == "date_range":
        end_time = config["meter"]["end_date"]
        start_time = config["meter"]["start_date"]
    elif select_meters == "select_cycle":
        cycle = Cycle.objects.get(pk=config["cycle_id"])
        end_time = cycle.end
        start_time = cycle.start
    else:
        AnalysisPipelineException("configuration.select_meters must be either 'all', 'date_range', or 'select_cycle'.")

    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    for property_view in property_views:

        # ensure we have Gross Floor Area on this property view's state
        if property_view.state.gross_floor_area is None:
            invalid_area.append(property_view.id)
            continue

        if select_meters == "all":
            # get the most recent electric meter reading's end_time
            try:
                end_time = MeterReading.objects.filter(
                    meter__property=property_view.property,
                    meter__type__in=VALID_METERS
                ).order_by('end_time').last().end_time
                start_time = end_time - TIME_PERIOD
            except Exception:
                invalid_meter.append(property_view.id)
                continue

        # get all readings that started AND ended between end_time and a year prior
        property_meter_readings = [
            SimpleMeterReading(reading.start_time, reading.end_time, reading.reading)
            for reading in MeterReading.objects.filter(
                meter__property=property_view.property,
                meter__type__in=VALID_METERS,
                end_time__lte=end_time,
                start_time__gte=start_time
            ).order_by('start_time')
        ]

        meter_readings_by_property_view[property_view.id] = property_meter_readings

    errors_by_property_view_id = {}
    for pid in invalid_area:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_GROSS_FLOOR_AREA])
    for pid in invalid_meter:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(EUI_ANALYSIS_MESSAGES[ERROR_INVALID_METER_READINGS])

    return meter_readings_by_property_view, errors_by_property_view_id


def _calculate_eui(meter_readings, gross_floor_area):
    """Calculate the total usage of the readings, EUI, and percent
    of TIME_PERIOD covered by the readings.

    :param meter_readings: List[SimpleMeterReading | MeterReading]
    :param gross_floor_area: float
    :return: dict, of the form:
        {
            'eui': float,
            'reading': float, # total usage
            'coverage': float # percent of TIME_PERIOD covered by the readings
        }
    """
    total_reading = 0
    days_affected_by_readings = set()
    for meter_reading in meter_readings:
        total_reading += meter_reading.reading
        for day in get_days_in_reading(meter_reading):
            days_affected_by_readings.add(day)

    total_seconds_covered = len(days_affected_by_readings) * datetime.timedelta(days=1).total_seconds()
    fraction_of_time_covered = total_seconds_covered / TIME_PERIOD.total_seconds()
    return {
        'eui': round(total_reading / gross_floor_area, 2),
        'reading': round(total_reading, 2),
        'coverage': int(fraction_of_time_covered * 100)
    }


class EUIPipeline(AnalysisPipeline):

    def _prepare_analysis(self, property_view_ids, start_analysis=True):
        # current implementation will *always* start the analysis immediately

        analysis = Analysis.objects.get(id=self._analysis_id)
        meter_readings_by_property_view, errors_by_property_view_id = _get_valid_meters(property_view_ids, analysis.configuration)
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
    pipeline = EUIPipeline(analysis_id)
    pipeline.set_analysis_status_to_ready('Ready to run EUI analysis')

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
    pipeline = EUIPipeline(analysis_id)
    progress_data = pipeline.set_analysis_status_to_running()
    progress_data.step('Calculating EUI')
    analysis = Analysis.objects.get(id=analysis_id)

    # make sure we have the extra data columns we need, don't set the
    # displayname and description if the column already exists because
    # the user might have changed them which would re-create new columns
    # here.
    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_eui',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Fractional EUI (kBtu/sqft)'
        column.column_description = 'Fractional EUI (kBtu/sqft)'
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_eui_coverage',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'EUI Coverage (% of the year)'
        column.column_description = 'EUI Coverage (% of the year)'
        column.save()

    # fix the meter readings dict b/c celery messes with it when serializing
    meter_readings_by_analysis_property_view = {
        int(key): [SimpleMeterReading(*serialized_reading) for serialized_reading in serialized_readings]
        for key, serialized_readings in meter_readings_by_analysis_property_view.items()
    }
    analysis_property_view_ids = list(meter_readings_by_analysis_property_view.keys())

    # prefetching property and cycle b/c .get_property_views() uses them (this is not "clean" but whatever)
    analysis_property_views = (
        AnalysisPropertyView.objects.filter(id__in=analysis_property_view_ids)
        .prefetch_related('property', 'cycle', 'property_state')
    )
    property_views_by_apv_id = AnalysisPropertyView.get_property_views(analysis_property_views)

    # create and save EUIs for each property view
    for analysis_property_view in analysis_property_views:
        area = analysis_property_view.property_state.gross_floor_area.magnitude
        meter_readings = meter_readings_by_analysis_property_view[analysis_property_view.id]
        eui = _calculate_eui(meter_readings, area)

        analysis_property_view.parsed_results = {
            'Fractional EUI (kBtu/sqft)': eui['eui'],
            'Annual Coverage %': eui['coverage'],
            'Total Annual Meter Reading (kBtu)': eui['reading'],
            'Gross Floor Area (sqft)': area
        }
        analysis_property_view.save()

        property_view = property_views_by_apv_id[analysis_property_view.id]
        property_view.state.extra_data.update({'analysis_eui': eui['eui']})
        property_view.state.extra_data.update({'analysis_eui_coverage': eui['coverage']})
        property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()
