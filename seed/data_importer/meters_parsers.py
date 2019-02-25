# !/usr/bin/env python
# encoding: utf-8

from calendar import monthrange

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.utils.timezone import make_aware

from pytz import timezone

from seed.models import (
    Meter,
    PropertyState,
)
from seed.data_importer.utils import kbtu_thermal_conversion_factors


class PMMeterParser(object):
    def __init__(self, org_id, meters_and_readings_details):
        self._org_id = org_id
        self._meters_and_readings_details = meters_and_readings_details
        self._tz = timezone(TIME_ZONE)
        self._source_to_property_ids = {}  # tracked to reduce the number of database queries
        self._us_kbtu_thermal_conversion_factors = {}
        self.result = {}

    @property
    def us_kbtu_thermal_conversion_factors(self):
        if not self._us_kbtu_thermal_conversion_factors:
            self._us_kbtu_thermal_conversion_factors = kbtu_thermal_conversion_factors("US")

        return self._us_kbtu_thermal_conversion_factors

    def validated_type_units(self):
        column_headers = self._find_type_columns(self._meters_and_readings_details[0])

        result = []

        for header in column_headers:
            type, unit, _factor = self._parse_unit_and_factor(header)
            result.append({
                "column_header": header,
                "type": type,
                "unit": unit,
            })


        return result


    def construct_objects_details(self, property_link='Property Id', monthly=True):
        """
        Details for meter and meter reading objects are parsed from meter usage data.
        Specifically, the raw meter usage data is converted into a format that is
        accepted by the two models. The following dictionary is generated, and
        it's values are returned as details of several objects:
        {
            <unique meter identifier>: {
                'property_id': <id>,
                'type': <char>,
                ...(other meter metadata)
                'readings': [
                    {
                        'start_time': <time>,
                        'end_time': <time>,
                        'reading': <float>
                    },
                    ...(more readings)
                ]
            },
            ...(more meters and their readings)
        }

        The unique identifier of a meter is composed of the values of it's details
        which include property_id, type, etc. This is used to easily associate
        readings to a previously parsed meter.
        """
        for details in self._meters_and_readings_details:
            meter_shared_details = {}

            source_id = details[property_link]

            meter_shared_details['source'] = 1  # probably need to be passed in as arg
            meter_shared_details['source_id'] = str(source_id)

            self._get_property_id_from_source(source_id, meter_shared_details)

            if monthly:
                start_time, end_time = self._parse_times(details['Month'])

            self._parse_meter_readings(details, meter_shared_details, start_time, end_time)

        return list(self.result.values())

    def _get_property_id_from_source(self, source_id, shared_details):
        """This is set up to avoid querying for the same property_id more than once"""
        property_id = self._source_to_property_ids.get(source_id, None)

        if property_id is not None:
            shared_details['property_id'] = property_id
        else:
            """
            Filter used because property may exist across multiple cycles within an org.
            If so, multiple property states will be found, but the underlying
            property should be the same, so take the first.
            """
            property_id = PropertyState.objects \
                .filter(pm_property_id__exact=source_id, organization_id__exact=self._org_id)[0] \
                .propertyview_set \
                .first() \
                .property_id

            shared_details['property_id'] = property_id
            self._source_to_property_ids[source_id] = property_id

    def _parse_times(self, month_year):
        unaware_start = datetime.strptime(month_year, '%b-%y')
        start_time = make_aware(unaware_start, timezone=self._tz)

        days_in_month = monthrange(start_time.year, start_time.month)[1]
        unaware_end = datetime(start_time.year, start_time.month, days_in_month, 23, 59, 59)
        end_time = make_aware(unaware_end, timezone=self._tz)

        return start_time, end_time

    def _parse_meter_readings(self, details, meter_shared_details, start_time, end_time):
        """
        Meter types (key/value pairs) of raw meter details are iterated over to
        generate individual meter readings. If a meter has not yet been parsed, it's
        first reading details are saved in a list. If a meter was previously parsed
        and has readings already, any new readings are appended to that list.
        """
        meter_types = self._find_type_columns(details)

        for type in meter_types:
            meter_details = meter_shared_details.copy()

            _type, unit, conversion_factor = self._parse_unit_and_factor(type, meter_details)

            meter_reading = {
                'start_time': start_time,
                'end_time': end_time,
                'reading': details[type] * conversion_factor,
                'source_unit': unit,
                'conversion_factor': conversion_factor
            }

            meter_identifier = '-'.join([str(v) for k, v in meter_details.items()])

            existing_property_meter = self.result.get(meter_identifier, None)

            if existing_property_meter is None:
                meter_details['readings'] = [meter_reading]

                self.result[meter_identifier] = meter_details
            else:
                existing_property_meter['readings'].append(meter_reading)

    def _find_type_columns(self, details):
        return [k for k, v in details.items() if ' Use  (' in k]

    def _parse_unit_and_factor(self, type_unit, meter_details={}):
        use_position = type_unit.find(" Use")
        type = type_unit[:use_position]
        meter_details['type'] = Meter.type_lookup[type]

        unit = type_unit[(type_unit.find('(', use_position) + 1):(type_unit.find(')', use_position))]

        # TODO: If Fuzzy matching is needed, it should be done here
        # TODO; If no conversion exists? skip entry (via try except)?
        factor = self.us_kbtu_thermal_conversion_factors[type][unit]

        return type, unit, factor
