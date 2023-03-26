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
    Meter,
    MeterReading,
    PropertyView
)

logger = logging.getLogger(__name__)

ERROR_INVALID_METER_READINGS = 0
ERROR_NO_VALID_PROPERTIES = 1
WARNING_SOME_INVALID_PROPERTIES = 2
ERROR_NO_REGION_CODE = 3
ERROR_INVALID_REGION_CODE = 4

CO2_ANALYSIS_MESSAGES = {
    ERROR_INVALID_METER_READINGS: 'Property view skipped (no linked electricity meters with readings).',
    ERROR_NO_VALID_PROPERTIES: 'Analysis found no valid properties.',
    WARNING_SOME_INVALID_PROPERTIES: 'Some properties failed to validate.',
    ERROR_NO_REGION_CODE: 'Property is missing eGRID Subregion Code.',
    ERROR_INVALID_REGION_CODE: 'Could not find C02 rate for provided eGRID subregion code.'
}

VALID_METERS = [Meter.ELECTRICITY_GRID, Meter.ELECTRICITY_UNKNOWN]
TIME_PERIOD = datetime.timedelta(days=365)

# These factors represent how much CO2e is emitted per MWh of electricity used
# in a specific year and eGRID Subregion
#
# Sources:
#  https://github.com/NREL/openstudio-common-measures-gem/pull/80/files#diff-9b55886a63bf3970a5d1c55effeb291a3107e00091715e63448ac1983ef89559
#  https://github.com/NREL/openstudio-common-measures-gem/pull/80/files#diff-fd04e84984194976089ec4d90f103e6d68e641a596e2446447d05626057b38ad
EARLIEST_CO2_RATE = 2007
CO2_RATES = {
    EARLIEST_CO2_RATE: {
        'AZNM': 570.57,  'CAMX': 309.98,  'ERCT': 570.18,  'FRCC': 555.85,  'MROE': 771.83,  'MROW': 785.61,  # noqa: E241
        'NEWE': 378.35,  'NWPP': 391.53,  'NYCW': 320.35,  'NYLI': 646.1,   'NYUP': 311.42,  'RFCE': 483.05,  # noqa: E241
        'RFCM': 753,     'RFCW': 707.43,  'RMPA': 868.69,  'SPNO': 820.02,  'SPSO': 739.88,  'SRMV': 457.13,  # noqa: E241
        'SRMW': 811.26,  'SRSO': 681.88,  'SRTV': 702.55,  'SRVC': 510.09                                     # noqa: E241
    }, 2009: {
        'AZNM': 542.65,  'CAMX': 299.85,  'ERCT': 537.91,  'FRCC': 535.87,  'MROE': 725.84,  'MROW': 742.75,  # noqa: E241
        'NEWE': 333,     'NWPP': 373.41,  'NYCW': 277.56,  'NYLI': 613.98,  'NYUP': 226.91,  'RFCE': 432.02,  # noqa: E241
        'RFCM': 756.78,  'RFCW': 693.29,  'RMPA': 831.45,  'SPNO': 827.71,  'SPSO': 728.44,  'SRMV': 456.28,  # noqa: E241
        'SRMW': 797.77,  'SRSO': 604.33,  'SRTV': 618.99,  'SRVC': 472.42                                     # noqa: E241
    }, 2010: {
        'AZNM': 536.44,  'CAMX': 278.12,  'ERCT': 554.58,  'FRCC': 545.01,  'MROE': 734.6,   'MROW': 700.71,  # noqa: E241
        'NEWE': 329.97,  'NWPP': 384.1,   'NYCW': 282.88,  'NYLI': 608.15,  'NYUP': 248.69,  'RFCE': 456.69,  # noqa: E241
        'RFCM': 742.99,  'RFCW': 685.47,  'RMPA': 864.49,  'SPNO': 820.27,  'SPSO': 719.95,  'SRMV': 468.73,  # noqa: E241
        'SRMW': 825.57,  'SRSO': 617.24,  'SRTV': 633.32,  'SRVC': 489.58                                     # noqa: E241
    }, 2012: {
        'AZNM': 525.13,  'CAMX': 296.01,  'ERCT': 520.26,  'FRCC': 512.39,  'MROE': 694.31,  'MROW': 649.98,  # noqa: E241
        'NEWE': 291.49,  'NWPP': 303.5,   'NYCW': 316.58,  'NYLI': 546.88,  'NYUP': 186.08,  'RFCE': 391.23,  # noqa: E241
        'RFCM': 715.32,  'RFCW': 628.8,   'RMPA': 830.73,  'SPNO': 784.78,  'SPSO': 700.8,   'SRMV': 479.19,  # noqa: E241
        'SRMW': 779.87,  'SRSO': 523.48,  'SRTV': 609.49,  'SRVC': 425.34                                     # noqa: E241
    }, 2014: {
        'AZNM': 399.02,  'CAMX': 258.72,  'ERCT': 520.64,  'FRCC': 490.13,  'MROE': 760.31,  'MROW': 623.84,  # noqa: E241
        'NEWE': 261.56,  'NWPP': 414.24,  'NYCW': 302.46,  'NYLI': 546.16,  'NYUP': 166.72,  'RFCE': 378.43,  # noqa: E241
        'RFCM': 699.58,  'RFCW': 630.76,  'RMPA': 793.36,  'SPNO': 719.46,  'SPSO': 673.36,  'SRMV': 465.8,   # noqa: E241
        'SRMW': 809.86,  'SRSO': 521.86,  'SRTV': 610.15,  'SRVC': 391.27                                     # noqa: E241
    }, 2016: {
        'AZNM': 475.74,  'CAMX': 240.3,   'ERCT': 459.88,  'FRCC': 460.92,  'MROE': 761.56,  'MROW': 565.71,  # noqa: E241
        'NEWE': 255.65,  'NWPP': 297.23,  'NYCW': 288.91,  'NYLI': 537.85,  'NYUP': 134.21,  'RFCE': 345.62,  # noqa: E241
        'RFCM': 579.98,  'RFCW': 567.54,  'RMPA': 624.37,  'SPNO': 644.95,  'SPSO': 569.08,  'SRMV': 381.92,  # noqa: E241
        'SRMW': 735.79,  'SRSO': 496.64,  'SRTV': 540.86,  'SRVC': 367.39                                     # noqa: E241
    }, 2018: {
        'AZNM': 465.99,  'CAMX': 226.15,  'ERCT': 424.51,  'FRCC': 424.54,  'MROE': 766.26,  'MROW': 566.51,  # noqa: E241
        'NEWE': 239.25,  'NWPP': 291.77,  'NYCW': 271.09,  'NYLI': 541.07,  'NYUP': 115.14,  'RFCE': 326.51,  # noqa: E241
        'RFCM': 599.16,  'RFCW': 532.42,  'RMPA': 581.36,  'SPNO': 531.32,  'SPSO': 531.84,  'SRMV': 389.27,  # noqa: E241
        'SRMW': 760.42,  'SRSO': 468.68,  'SRTV': 470.79,  'SRVC': 339                                        # noqa: E241
    }, 2019: {
        'AZNM': 433.95,  'CAMX': 206.46,  'ERCT': 395.63,  'FRCC': 392.07,  'MROE': 685.96,  'MROW': 501.78,  # noqa: E241
        'NEWE': 223.95,  'NWPP': 326.46,  'NYCW': 251.72,  'NYLI': 552.78,  'NYUP': 105.69,  'RFCE': 316.76,  # noqa: E241
        'RFCM': 542.84,  'RFCW': 487.24,  'RMPA': 567.12,  'SPNO': 488.69,  'SPSO': 456.55,  'SRMV': 367.15,  # noqa: E241
        'SRMW': 723.76,  'SRSO': 441.7,   'SRTV': 433.36,  'SRVC': 307.99                                     # noqa: E241
    }, 2020: {
        'AZNM': 350.6,   'CAMX': 211.4,   'ERCT': 342.1,   'FRCC': 366.2,   'MROE': 535.3,   'MROW': 381.9,   # noqa: E241
        'NEWE': 134.4,   'NWPP': 175.7,                    'NYLI': 235.9,   'NYUP': 180.1,   'RFCE': 274.5,   # noqa: E241
        'RFCM': 609.5,   'RFCW': 485,     'RMPA': 514.4,   'SPNO': 457.5,   'SPSO': 285.6,   'SRMV': 419,     # noqa: E241
        'SRMW': 606,     'SRSO': 332.3,   'SRTV': 513.9,   'SRVC': 291.6                                      # noqa: E241
    }, 2022: {
        'AZNM': 410,     'CAMX': 215.4,   'ERCT': 340.2,   'FRCC': 375.2,   'MROE': 526.5,   'MROW': 392.6,   # noqa: E241
        'NEWE': 146.3,   'NWPP': 224,                      'NYLI': 248.9,   'NYUP': 198.2,   'RFCE': 282.1,   # noqa: E241
        'RFCM': 629.8,   'RFCW': 500.5,   'RMPA': 571.8,   'SPNO': 443.5,   'SPSO': 276,     'SRMV': 409.5,   # noqa: E241
        'SRMW': 632.1,   'SRSO': 320.5,   'SRTV': 550.4,   'SRVC': 301.1                                      # noqa: E241
    }, 2024: {
        'AZNM': 402.4,   'CAMX': 197.2,   'ERCT': 300.5,   'FRCC': 379.2,   'MROE': 529.5,   'MROW': 361.7,   # noqa: E241
        'NEWE': 131.1,   'NWPP': 183.8,                    'NYLI': 182.1,   'NYUP': 146.9,   'RFCE': 250.7,   # noqa: E241
        'RFCM': 519.3,   'RFCW': 460.4,   'RMPA': 567.2,   'SPNO': 246.9,   'SPSO': 160.2,   'SRMV': 357,     # noqa: E241
        'SRMW': 547.2,   'SRSO': 325.5,   'SRTV': 484.2,   'SRVC': 299.7                                      # noqa: E241
    }, 2026: {
        'AZNM': 387.2,   'CAMX': 178.9,   'ERCT': 300.5,   'FRCC': 397.2,   'MROE': 523.4,   'MROW': 335.3,   # noqa: E241
        'NEWE': 106.9,   'NWPP': 169,                      'NYLI': 162.7,   'NYUP': 128.3,   'RFCE': 247,     # noqa: E241
        'RFCM': 523.9,   'RFCW': 471.6,   'RMPA': 573.1,   'SPNO': 233.7,   'SPSO': 142.5,   'SRMV': 347.7,   # noqa: E241
        'SRMW': 537.9,   'SRSO': 345.6,   'SRTV': 509.9,   'SRVC': 280.6                                      # noqa: E241
    }, 2028: {
        'AZNM': 333,     'CAMX': 158.6,   'ERCT': 270.1,   'FRCC': 353.1,   'MROE': 477.6,   'MROW': 309.3,   # noqa: E241
        'NEWE': 95.4,    'NWPP': 146.9,                    'NYLI': 138.5,   'NYUP': 105.7,   'RFCE': 235.8,   # noqa: E241
        'RFCM': 476.8,   'RFCW': 457.5,   'RMPA': 532,     'SPNO': 226.4,   'SPSO': 133.2,   'SRMV': 327.9,   # noqa: E241
        'SRMW': 472.1,   'SRSO': 262,     'SRTV': 500.2,   'SRVC': 257.6                                      # noqa: E241
    }, 2030: {
        'AZNM': 299.5,   'CAMX': 149.3,   'ERCT': 206.7,   'FRCC': 287.3,   'MROE': 347.1,   'MROW': 195.6,   # noqa: E241
        'NEWE': 80.3,    'NWPP': 136.2,                    'NYLI': 116.5,   'NYUP': 87.8,    'RFCE': 206.9,   # noqa: E241
        'RFCM': 390.9,   'RFCW': 411.4,   'RMPA': 438,     'SPNO': 181.1,   'SPSO': 118.9,   'SRMV': 280.3,   # noqa: E241
        'SRMW': 362.9,   'SRSO': 221.4,   'SRTV': 405.5,   'SRVC': 210.6                                      # noqa: E241
    }, 2032: {
        'AZNM': 286.9,   'CAMX': 146.7,   'ERCT': 168,     'FRCC': 271.6,   'MROE': 302.6,   'MROW': 161.3,   # noqa: E241
        'NEWE': 81,      'NWPP': 136.7,                    'NYLI': 113.9,   'NYUP': 87.4,    'RFCE': 204.9,   # noqa: E241
        'RFCM': 371.6,   'RFCW': 385.9,   'RMPA': 413.1,   'SPNO': 161.3,   'SPSO': 86.6,    'SRMV': 268.4,   # noqa: E241
        'SRMW': 379.6,   'SRSO': 205.2,   'SRTV': 377,     'SRVC': 202.1                                      # noqa: E241
    }, 2034: {
        'AZNM': 277.9,   'CAMX': 139.5,   'ERCT': 157.1,   'FRCC': 275.5,   'MROE': 163.2,   'MROW': 144.8,   # noqa: E241
        'NEWE': 69.3,    'NWPP': 135,                      'NYLI': 98.8,    'NYUP': 74.7,    'RFCE': 198.1,   # noqa: E241
        'RFCM': 354.9,   'RFCW': 356.7,   'RMPA': 341,     'SPNO': 160.6,   'SPSO': 81.2,    'SRMV': 263.3,   # noqa: E241
        'SRMW': 363.1,   'SRSO': 206.9,   'SRTV': 352.8,   'SRVC': 190.1                                      # noqa: E241
    }, 2036: {
        'AZNM': 241.6,   'CAMX': 129.3,   'ERCT': 155.4,   'FRCC': 266.9,   'MROE': 157.4,   'MROW': 138.4,   # noqa: E241
        'NEWE': 71.9,    'NWPP': 134.1,                    'NYLI': 106.9,   'NYUP': 81.7,    'RFCE': 202.1,   # noqa: E241
        'RFCM': 335.9,   'RFCW': 329.1,   'RMPA': 287.9,   'SPNO': 155.4,   'SPSO': 71.8,    'SRMV': 252.2,   # noqa: E241
        'SRMW': 345,     'SRSO': 206.2,   'SRTV': 324.9,   'SRVC': 187.2                                      # noqa: E241
    }, 2038: {
        'AZNM': 207.3,   'CAMX': 111.7,   'ERCT': 140.1,   'FRCC': 258.4,   'MROE': 168.7,   'MROW': 137.6,   # noqa: E241
        'NEWE': 66.3,    'NWPP': 123.3,                    'NYLI': 100.7,   'NYUP': 80.1,    'RFCE': 205.4,   # noqa: E241
        'RFCM': 316.9,   'RFCW': 310,     'RMPA': 286,     'SPNO': 155.5,   'SPSO': 64.1,    'SRMV': 247,     # noqa: E241
        'SRMW': 332.9,   'SRSO': 187.1,   'SRTV': 323.4,   'SRVC': 184.1                                      # noqa: E241
    }, 2040: {
        'AZNM': 178.4,   'CAMX': 100.9,   'ERCT': 145.9,   'FRCC': 250.3,   'MROE': 159.9,   'MROW': 140.8,   # noqa: E241
        'NEWE': 66.5,    'NWPP': 110.7,                    'NYLI': 93.9,    'NYUP': 74.1,    'RFCE': 198,     # noqa: E241
        'RFCM': 289.3,   'RFCW': 281.8,   'RMPA': 284.8,   'SPNO': 153.6,   'SPSO': 59.7,    'SRMV': 239.8,   # noqa: E241
        'SRMW': 281.7,   'SRSO': 183.6,   'SRTV': 307.2,   'SRVC': 178.4                                      # noqa: E241
    }, 2042: {
        'AZNM': 180.9,   'CAMX': 93.9,    'ERCT': 127,     'FRCC': 227.1,   'MROE': 152.3,   'MROW': 120.6,   # noqa: E241
        'NEWE': 57.4,    'NWPP': 107.2,                    'NYLI': 89,      'NYUP': 75.9,    'RFCE': 192,     # noqa: E241
        'RFCM': 285.2,   'RFCW': 254.2,   'RMPA': 245.3,   'SPNO': 151.3,   'SPSO': 55.5,    'SRMV': 222.1,   # noqa: E241
        'SRMW': 243.9,   'SRSO': 160.5,   'SRTV': 279,     'SRVC': 155.4                                      # noqa: E241
    }, 2044: {
        'AZNM': 142.9,   'CAMX': 81.3,    'ERCT': 119.7,   'FRCC': 191.6,   'MROE': 121.2,   'MROW': 99.9,    # noqa: E241
        'NEWE': 59,      'NWPP': 102.5,                    'NYLI': 86.9,    'NYUP': 77.7,    'RFCE': 186.7,   # noqa: E241
        'RFCM': 287.9,   'RFCW': 237.1,   'RMPA': 238.4,   'SPNO': 116.6,   'SPSO': 46.7,    'SRMV': 205.6,   # noqa: E241
        'SRMW': 209.3,   'SRSO': 143.8,   'SRTV': 259.1,   'SRVC': 147.8                                      # noqa: E241
    }, 2046: {
        'AZNM': 135.6,   'CAMX': 76.2,    'ERCT': 104.8,   'FRCC': 191.8,   'MROE': 120.4,   'MROW': 97.8,    # noqa: E241
        'NEWE': 58.4,    'NWPP': 90.8,                     'NYLI': 85.1,    'NYUP': 76.5,    'RFCE': 190.6,   # noqa: E241
        'RFCM': 225.6,   'RFCW': 210.3,   'RMPA': 181,     'SPNO': 121,     'SPSO': 48.5,    'SRMV': 233.5,   # noqa: E241
        'SRMW': 185.6,   'SRSO': 122.1,   'SRTV': 228.4,   'SRVC': 127.1                                      # noqa: E241
    }, 2048: {
        'AZNM': 131.8,   'CAMX': 74.7,    'ERCT': 102.4,   'FRCC': 188.8,   'MROE': 134.6,   'MROW': 87.6,    # noqa: E241
        'NEWE': 57.1,    'NWPP': 86,                       'NYLI': 91.1,    'NYUP': 81.5,    'RFCE': 169.8,   # noqa: E241
        'RFCM': 201.6,   'RFCW': 212.4,   'RMPA': 161.5,   'SPNO': 129,     'SPSO': 57.5,    'SRMV': 232.6,   # noqa: E241
        'SRMW': 184.5,   'SRSO': 125.7,   'SRTV': 207.8,   'SRVC': 120.7                                      # noqa: E241
    }, 2050: {
        'AZNM': 125.7,   'CAMX': 68.8,    'ERCT': 87.7,    'FRCC': 178,     'MROE': 100.1,   'MROW': 78.9,    # noqa: E241
        'NEWE': 58,      'NWPP': 66,                       'NYLI': 89.1,    'NYUP': 81.4,    'RFCE': 161.9,   # noqa: E241
        'RFCM': 155.1,   'RFCW': 193,     'RMPA': 155.6,   'SPNO': 131.2,   'SPSO': 55.4,    'SRMV': 215.5,   # noqa: E241
        'SRMW': 173.4,   'SRSO': 111.8,   'SRTV': 175.4,   'SRVC': 97.7                                       # noqa: E241
    }
}


# currently only getting closest prior year
def _get_co2_rate(year, region_code):
    while year >= EARLIEST_CO2_RATE:
        if year in CO2_RATES and region_code in CO2_RATES[year]:
            return CO2_RATES[year][region_code]
        year -= 1
    return None


def _get_valid_meters(property_view_ids):
    """Performs basic validation of the properties for running CO2 analysis and returns any errors.

    :param analysis: property_view_ids
    :returns: dictionary[id:str], dictionary of property_view_ids to error message
    """
    invalid_meter = []
    meter_readings_by_property_view = {}
    property_views = PropertyView.objects.filter(id__in=property_view_ids)
    for property_view in property_views:

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
        property_meter_readings = [
            SimpleMeterReading(reading.start_time, reading.end_time, reading.reading)
            for reading in MeterReading.objects.filter(
                meter__property=property_view.property,
                meter__type__in=VALID_METERS,
                end_time__lte=end_time,
                start_time__gte=end_time - TIME_PERIOD
            ).order_by('start_time')
        ]

        meter_readings_by_property_view[property_view.id] = property_meter_readings

    errors_by_property_view_id = {}
    for pid in invalid_meter:
        if pid not in errors_by_property_view_id:
            errors_by_property_view_id[pid] = []
        errors_by_property_view_id[pid].append(CO2_ANALYSIS_MESSAGES[ERROR_INVALID_METER_READINGS])

    return meter_readings_by_property_view, errors_by_property_view_id


def _calculate_co2(meter_readings, region_code):
    """Calculate CO2 emissions for the meter readings. Raises an exception if it's
    unable to calculate the emissions (e.g., unable to find eGRID region code for
    a year)

    :param meter_readings: List[SimpleMeterReading | MeterReading], the `.reading`
        value must be in kBtu!
        Assumes the time span of meter_readings is less than or equal to TIME_PERIOD,
        i.e., that they are supposed to be representative of a year.
    :region_code: str, an eGRID Subregion Code
    :return: dict
    """
    total_reading = 0
    total_average = 0
    days_affected_by_readings = set()
    for meter_reading in meter_readings:
        reading_mwh = meter_reading.reading / 3.412 / 1000  # convert from kBtu to MWh
        total_reading += reading_mwh
        year = meter_reading.start_time.year
        rate = _get_co2_rate(year, region_code)
        if rate is None:
            raise Exception(f'Failed to find CO2 rate for {region_code} in {year}')
        total_average += (reading_mwh * rate)
        for day in get_days_in_reading(meter_reading):
            days_affected_by_readings.add(day)
    total_seconds_covered = len(days_affected_by_readings) * datetime.timedelta(days=1).total_seconds()
    fraction_of_time_covered = total_seconds_covered / TIME_PERIOD.total_seconds()
    return {
        'average_annual_kgco2e': round(total_average),
        'total_annual_electricity_mwh': round(total_reading, 2),
        'annual_coverage_percent': int(fraction_of_time_covered * 100),
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
                user_message=CO2_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES],
                debug_message=''
            )
            analysis = Analysis.objects.get(id=self._analysis_id)
            analysis.status = Analysis.FAILED
            analysis.save()
            raise AnalysisPipelineException(CO2_ANALYSIS_MESSAGES[ERROR_NO_VALID_PROPERTIES])

        if errors_by_property_view_id:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.WARNING,
                analysis_id=self._analysis_id,
                analysis_property_view_id=None,
                user_message=CO2_ANALYSIS_MESSAGES[WARNING_SOME_INVALID_PROPERTIES],
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

    # make sure we have the extra data columns we need, don't set the
    # displayname and description if the column already exists because
    # the user might have changed them which would re-create new columns
    # here.
    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_co2',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Average Annual CO2 (kgCO2e)',
        column.column_description = 'Average Annual CO2 (kgCO2e)',
        column.save()

    column, created = Column.objects.get_or_create(
        is_extra_data=True,
        column_name='analysis_co2_coverage',
        organization=analysis.organization,
        table_name='PropertyState',
    )
    if created:
        column.display_name = 'Average Annual CO2 Coverage (% of the year)'
        column.column_description = 'Average Annual CO2 Coverage (% of the year)'
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

    # should we save data to the property?
    save_co2_results = analysis.configuration.get('save_co2_results', False)

    # create and save emissions for each property view
    for analysis_property_view in analysis_property_views:
        meter_readings = meter_readings_by_analysis_property_view[analysis_property_view.id]
        property_view = property_views_by_apv_id[analysis_property_view.id]

        # get the region code
        egrid_subregion_code = property_view.state.egrid_subregion_code
        if not egrid_subregion_code:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_property_view.id,
                user_message=CO2_ANALYSIS_MESSAGES[ERROR_NO_REGION_CODE],
                debug_message=''
            )
            continue

        # get the C02 rate
        try:
            co2 = _calculate_co2(meter_readings, egrid_subregion_code)
        except Exception as e:
            AnalysisMessage.log_and_create(
                logger=logger,
                type_=AnalysisMessage.ERROR,
                analysis_id=analysis_id,
                analysis_property_view_id=analysis_property_view.id,
                user_message=CO2_ANALYSIS_MESSAGES[ERROR_INVALID_REGION_CODE],
                debug_message='Failed to calculate CO2',
                exception=e
            )
            continue

        # save the results
        analysis_property_view.parsed_results = {
            'Average Annual CO2 (kgCO2e)': co2['average_annual_kgco2e'],
            'Annual Coverage %': co2['annual_coverage_percent'],
            'Total Annual Meter Reading (MWh)': co2['total_annual_electricity_mwh'],
            'Total GHG Emissions Intensity (kgCO2e/ft\u00b2/year)': co2['average_annual_kgco2e'] / property_view.state.gross_floor_area.magnitude
        }
        analysis_property_view.save()
        if save_co2_results:
            # Convert the analysis results which reports in kgCO2e to MtCO2e which is the canonical database field units
            property_view.state.total_ghg_emissions = co2['average_annual_kgco2e'] / 1000
            property_view.state.total_ghg_emissions_intensity = co2['average_annual_kgco2e'] / property_view.state.gross_floor_area.magnitude
            property_view.state.save()

    # all done!
    pipeline.set_analysis_status_to_completed()
