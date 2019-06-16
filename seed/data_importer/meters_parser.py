# !/usr/bin/env python
# encoding: utf-8

from config.settings.common import TIME_ZONE

from collections import defaultdict

from datetime import datetime

from django.utils.timezone import make_aware

from pytz import timezone

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Meter,
    PropertyState,
)
from seed.data_importer.utils import kbtu_thermal_conversion_factors


class MetersParser(object):
    """
    This class parses and validates different details about a meter usage
    Import File including meter energy types & units along with a summary of the
    potential records to be created before execution.

    The expected input includes a list of raw meters_and_readings_details. The
    format of these raw details should be a list of dictionaries where the
    dictionaries are of the following formats:
        {
            'Property Id': <pm_property_id>,
            'Month': '<abbr. Month>-YY',
            '<energy_type_name_1> Use  (<units_1>)': <reading>,
            '<energy_type_name_2> Use  (<units_2>)': <reading>,
            ...
        }
    or
        {
            'start_time': <epoch_time>,
            'source_id': <greenbutton_source_id>,
            'duration': <seconds>,
            '<energy_type_name_1> Use  (<units_1>)': <reading>,
            '<energy_type_name_2> Use  (<units_2>)': <reading>,
            ...
        }

    It's able to create a collection of Meter object details and their
    corresponding Meter Reading objects details.
    """

    _tz = timezone(TIME_ZONE)

    def __init__(self, org_id, meters_and_readings_details, source_type=Meter.PORTFOLIO_MANAGER, property_id=None):
        # defaulted to None to show it hasn't been cached yet
        self._cache_meter_and_reading_objs = None
        self._cache_validated_type_units = None
        self._cache_kbtu_thermal_conversion_factors = None

        self._meters_and_readings_details = meters_and_readings_details
        self._org_id = org_id
        self._property_id = property_id
        self._source_type = source_type
        self._unique_meters = {}

        # The following are only relevant/used if property_id isn't explicitly specified
        if property_id is None:
            self._property_link = 'Portfolio Manager ID'
            self._source_to_property_ids = {}  # tracked to reduce the number of database queries
            self._unlinkable_pm_ids = set()  # to avoid duplicates

    @property
    def _kbtu_thermal_conversion_factors(self):
        if self._cache_kbtu_thermal_conversion_factors is None:
            org_preference = Organization.objects.get(pk=self._org_id).get_thermal_conversion_assumption_display()
            self._cache_kbtu_thermal_conversion_factors = kbtu_thermal_conversion_factors(org_preference)

        return self._cache_kbtu_thermal_conversion_factors

    @property
    def unlinkable_pm_ids(self):
        self.meter_and_reading_objs  # provided raw details need to have been parsed first

        return [{"portfolio_manager_id": id} for id in self._unlinkable_pm_ids]

    @property
    def meter_and_reading_objs(self):
        """
        Raw meter usage data is converted into a format that is accepted by the
        two models. The following dictionary is generated, and it's values are
        returned as details of several objects:
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
        readings to a previously parsed meter without creating duplicates.
        """
        if self._cache_meter_and_reading_objs is None:
            for details in self._meters_and_readings_details:
                meter_details = {}

                meter_details['source'] = self._source_type

                # Set source_id and property_id - using source_id to find property_id if necessary
                if self._source_type == Meter.PORTFOLIO_MANAGER and self._property_id is None:
                    meter_details['source_id'] = str(details['Portfolio Manager Meter ID'])

                    # Continue/skip, if no property is found.
                    given_property_id = str(details['Portfolio Manager ID'])
                    if not self._get_property_id(given_property_id, meter_details):
                        continue
                elif self._property_id:
                    meter_details['source_id'] = details['source_id']
                    meter_details['property_id'] = self._property_id

                # Define start_time and end_time
                if self._source_type == Meter.PORTFOLIO_MANAGER:
                    unaware_start = datetime.strptime(details['Start Date'], "%Y-%m-%d %H:%M:%S")
                    start_time = make_aware(unaware_start, timezone=self._tz)

                    unaware_end = datetime.strptime(details['End Date'], "%Y-%m-%d %H:%M:%S")
                    end_time = make_aware(unaware_end, timezone=self._tz)
                else:
                    start_time = datetime.fromtimestamp(details['start_time'], tz=self._tz)
                    end_time = datetime.fromtimestamp((details['start_time'] + details['duration']), tz=self._tz)

                self._parse_meter_readings(details, meter_details, start_time, end_time)

            self._cache_meter_and_reading_objs = list(self._unique_meters.values())

        return self._cache_meter_and_reading_objs

    def _get_property_id(self, source_id, shared_details):
        """
        Find and cache property_ids to avoid querying for the same property_id
        more than once. This assumes a Property model connects like PropertyStates
        across Cycles within an Organization. Return True when a property_id is found.

        If no ProperyStates (and subsequent Properties) are found, flag the
        PM ID as unlinkable, and False is returned.
        """
        property_id = self._source_to_property_ids.get(source_id, None)

        if property_id is not None:
            shared_details['property_id'] = property_id
        else:
            try:
                """
                Filter used because multiple PropertyStates will be found, but the
                underlying Property should be the same, so take the first.
                """
                property_id = PropertyState.objects \
                    .filter(pm_property_id__exact=source_id, organization_id__exact=self._org_id)[0] \
                    .propertyview_set \
                    .first() \
                    .property_id

                shared_details['property_id'] = property_id
                self._source_to_property_ids[source_id] = property_id
            except IndexError:
                self._unlinkable_pm_ids.add(source_id)
                return False

        return True

    def _parse_meter_readings(self, details, meter_details, start_time, end_time):
        """
        Meter types (key/value pairs) of raw meter details are iterated over to
        generate individual meter readings. If a meter has not yet been parsed, it's
        first reading details are saved in a list. If a meter was previously parsed
        and has readings already, any new readings are appended to that list.
        """
        type_name = details['Meter Type']
        unit = details['Usage Units']
        conversion_factor = self._kbtu_thermal_conversion_factors[type_name][unit]

        meter_details['type'] = Meter.type_lookup[type_name]

        meter_reading = {
            'start_time': start_time,
            'end_time': end_time,
            'reading': float(details['Usage/Quantity']) * conversion_factor,
            'source_unit': unit,
            'conversion_factor': conversion_factor
        }

        meter_identifier = '-'.join([str(v) for k, v in meter_details.items()])

        existing_property_meter = self._unique_meters.get(meter_identifier, None)

        if existing_property_meter is None:
            meter_details['readings'] = [meter_reading]

            self._unique_meters[meter_identifier] = meter_details
        else:
            existing_property_meter['readings'].append(meter_reading)

    def validated_type_units(self):
        """

        """
        type_units = {
            (details['Meter Type'], details['Usage Units'])
            for details
            in self._meters_and_readings_details
        }
        return [
            {'parsed_type': type_unit[0], 'parsed_unit': type_unit[1]}
            for type_unit
            in type_units
        ]

    def proposed_imports(self):
        """
        Summarizes meters and readings that will be created via file import.

        If this is a GreenButton import, take the UsagePoint as the source_id.
        """
        id_counts = defaultdict(lambda: 0)

        for obj in self.meter_and_reading_objs:
            id = obj.get("source_id")

            if obj['source'] == Meter.GREENBUTTON:
                id = self.usage_point_id(id)

            id_counts[id] += len(obj.get("readings"))

        return [
            {"source_id": id, "incoming": reading_count}
            for id, reading_count
            in id_counts.items()
        ]

    def usage_point_id(self, raw_source_id):
        id_split = raw_source_id.split('/')
        usage_point_index = next(i for i, substr in enumerate(id_split) if substr == "UsagePoint") + 1
        return id_split[usage_point_index]
