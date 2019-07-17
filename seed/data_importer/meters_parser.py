# !/usr/bin/env python
# encoding: utf-8

from calendar import monthrange

from config.settings.common import TIME_ZONE

from datetime import (
    datetime,
    timedelta,
)

from django.db.models import Subquery
from django.utils.timezone import make_aware

from pytz import timezone

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Meter,
    PropertyState,
    PropertyView,
)
from seed.data_importer.utils import (
    kbtu_thermal_conversion_factors,
    usage_point_id,
)


class MetersParser(object):
    """
    This class parses and validates different details about a meter usage
    Import File including meter energy types & units along with a summary of the
    potential records to be created before execution.

    The expected input includes a list of raw meters_and_readings_details. The
    format of these raw details should be a list of dictionaries where the
    dictionaries are of the following formats:
        {
            'Portfolio Manager ID': "11111111",
            'Portfolio Manager Meter ID': '123-PMMeterID',
            'Start Date': 'YYYY-MM-DD 00:00:00',
            'End Date': 'YYYY-MM-DD 00:00:00',
            'Meter Type': '<energy_type_name_1>',
            'Usage Units': '<units_1>',
            'Usage/Quantity': <reading>,
            ...
        }
    or
        {
            'start_time': <epoch_time>,
            'source_id': <greenbutton_source_id>,
            'duration': <seconds>,
            'Meter Type': '<energy_type_name_1>',
            'Usage Units': '<units_1>',
            'Usage/Quantity': <reading>,
        }

    It's able to create a collection of Meter object details and their
    corresponding MeterReading objects details.
    """

    _tz = timezone(TIME_ZONE)

    def __init__(self, org_id, meters_and_readings_details, source_type=Meter.PORTFOLIO_MANAGER, property_id=None):
        # defaulted to None to show it hasn't been cached yet
        self._cache_meter_and_reading_objs = None
        self._cache_org_country = None
        self._cache_kbtu_thermal_conversion_factors = None

        self._meters_and_readings_details = meters_and_readings_details
        self._org_id = org_id
        self._property_id = property_id
        self._source_type = source_type
        self._unique_meters = {}

        self._source_to_property_ids = {}  # tracked to reduce the number of database queries

        # The following are only relevant/used if property_id isn't explicitly specified
        if property_id is None:
            self._property_link = 'Portfolio Manager ID'
            self._unlinkable_pm_ids = set()  # to avoid duplicates

    @property
    def _kbtu_thermal_conversion_factors(self):
        if self._cache_kbtu_thermal_conversion_factors is None:
            self._cache_kbtu_thermal_conversion_factors = kbtu_thermal_conversion_factors(self._org_country)

        return self._cache_kbtu_thermal_conversion_factors

    @property
    def _org_country(self):
        if self._cache_org_country is None:
            self._cache_org_country = Organization.objects.get(pk=self._org_id).get_thermal_conversion_assumption_display()

        return self._cache_org_country

    @property
    def unlinkable_pm_ids(self):
        self.meter_and_reading_objs  # provided raw details need to have been parsed first

        return [{"portfolio_manager_id": id} for id in self._unlinkable_pm_ids]

    @property
    def meter_and_reading_objs(self):
        """
        Raw meter usage data are converted into a format that is accepted by the
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

        This is used to be able to group and associate MeterReadings to the
        appropriate Meters without duplicates being created. The logic for this
        lives in _parse_<type>_meter_readings().

        The unique identifier of a meter is composed of the values of it's details
        which include property_id, type, etc. This is used to easily associate
        readings to a previously parsed meter without creating duplicates.
        """
        if self._cache_meter_and_reading_objs is None:
            if self._source_type == Meter.PORTFOLIO_MANAGER:
                self._parse_pm_meter_details()
            elif self._source_type == Meter.GREENBUTTON:
                self._parse_gb_meter_details()

            self._cache_meter_and_reading_objs = list(self._unique_meters.values())

        return self._cache_meter_and_reading_objs

    def _parse_pm_meter_details(self):
        for details in self._meters_and_readings_details:
            meter_details = {
                'source': self._source_type,
            }

            meter_details['source_id'] = str(details['Portfolio Manager Meter ID'])

            # Continue/skip, if no property is found.
            given_property_id = str(details['Portfolio Manager ID'])
            if not self._get_property_id(given_property_id, meter_details):
                continue

            # Define start_time and end_time
            raw_start = details['Start Date']
            if raw_start == 'Not Available':
                """
                In this case, the meter is delivered, so the start and end times
                are set to the first of delivery date month to the first of the
                following month.
                """
                delivery_date = datetime.strptime(details['Delivery Date'], "%Y-%m-%d %H:%M:%S")
                year = delivery_date.year
                month = delivery_date.month
                _start_day, days_in_month = monthrange(year, month)

                unaware_start = datetime(year, month, 1, 0, 0, 0)
                unaware_end = datetime(year, month, days_in_month, 23, 59, 59) + timedelta(seconds=1)
            else:
                unaware_start = datetime.strptime(raw_start, "%Y-%m-%d %H:%M:%S")
                unaware_end = datetime.strptime(details['End Date'], "%Y-%m-%d %H:%M:%S")

            start_time = make_aware(unaware_start, timezone=self._tz)
            end_time = make_aware(unaware_end, timezone=self._tz)

            self._parse_meter_readings(details, meter_details, start_time, end_time)

            # If Cost field is present and value is available, create Cost Meter and MeterReading
            if details.get('Cost ($)', 'Not Available') != 'Not Available':
                carry_overs = ['property_id', 'source', 'source_id', 'type']
                meter_details_copy = {k: meter_details[k] for k in carry_overs}
                self._parse_cost_meter_reading(details, meter_details_copy, start_time, end_time)

    def _parse_gb_meter_details(self):
        for details in self._meters_and_readings_details:
            meter_details = {
                'source': self._source_type,
                'source_id': details['source_id'],
                'property_id': self._property_id,
            }

            # Define start_time and end_time
            start_time = datetime.fromtimestamp(details['start_time'], tz=self._tz)
            end_time = datetime.fromtimestamp((details['start_time'] + details['duration']), tz=self._tz)

            self._parse_meter_readings(details, meter_details, start_time, end_time)

    def _get_property_id(self, source_id, shared_details):
        """
        Find and cache property_ids to avoid querying for the same property_id
        more than once. This assumes a Property model connects like PropertyStates
        across Cycles within an Organization. Return True when a property_id is found.

        If no ProperyStates (and subsequent Properties) are found, flag the
        PM ID as unlinkable, and False is returned.
        """
        property_id = self._source_to_property_ids.get(source_id, None)

        # If the PM ID has been previously found to be unlinkable, return False
        if source_id in self._unlinkable_pm_ids:
            return False

        if property_id is not None:
            shared_details['property_id'] = property_id
        else:
            try:
                """
                QuerySet filters() used to find resulting property_id because
                multiple PropertyStates can be found, but the underlying
                Property amongst them should be the same. So take the first.
                """
                possible_matches = PropertyState.objects.filter(
                    pm_property_id__exact=source_id,
                    organization_id__exact=self._org_id
                )

                property_id = PropertyView.objects.filter(
                    state_id__in=Subquery(possible_matches.values('pk'))
                )[0].property_id

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

    def _parse_cost_meter_reading(self, details, meter_details, start_time, end_time):
        """
        Creates details for Meter and MeterReading cost objects.

        The logic is very similar to _parse_pm_meter_details, except this is
        specifically for cost. Also, it's assumed all meter_details are
        populated except for type.
        """
        meter_details['type'] = Meter.COST

        unit = '{} Dollars'.format(self._org_country)

        meter_reading = {
            'start_time': start_time,
            'end_time': end_time,
            'reading': float(details['Cost ($)']),
            'source_unit': unit,
            'conversion_factor': 1
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
        Creates/returns the validated type and unit combinations given in the
        import file.

        This is done by building a set of tuples containing type and unit
        combinations found in the parsed meter details. Since a set is used,
        these are deduplicated.
        """
        type_unit_combinations = set()
        energy_type_lookup = dict(Meter.ENERGY_TYPES)

        for meter in self.meter_and_reading_objs:
            type = energy_type_lookup[meter['type']]
            type_units = {
                (type, reading['source_unit'])
                for reading
                in meter['readings']
            }
            type_unit_combinations = type_unit_combinations.union(type_units)

        return [
            {'parsed_type': type_unit[0], 'parsed_unit': type_unit[1]}
            for type_unit
            in type_unit_combinations
        ]

    def proposed_imports(self):
        """
        Summarizes meters and readings that will be created via file import.

        If this is a GreenButton import, take the UsagePoint as the source_id.
        """
        summaries = []
        energy_type_lookup = dict(Meter.ENERGY_TYPES)
        property_ids_to_pm_ids = {v: k for k, v in self._source_to_property_ids.items()}

        for meter in self.meter_and_reading_objs:
            meter_summary = {
                'type': energy_type_lookup[meter['type']],
                'incoming': len(meter.get("readings")),
            }

            id = meter.get("source_id")
            if meter['source'] == Meter.PORTFOLIO_MANAGER:
                meter_summary['source_id'] = id
                meter_summary['pm_property_id'] = property_ids_to_pm_ids[meter.get("property_id")]
            else:
                meter_summary['source_id'] = usage_point_id(id)

            summaries.append(meter_summary)

        return summaries
