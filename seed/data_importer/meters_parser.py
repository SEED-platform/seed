# !/usr/bin/env python
# encoding: utf-8

from calendar import monthrange

from config.settings.common import TIME_ZONE

from datetime import (
    datetime,
    timedelta,
)
import re

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
from seed.lib.mcm import reader


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

    @classmethod
    def factory(cls, meters_file, org_id, source_type=Meter.PORTFOLIO_MANAGER, property_id=None):
        """Factory function for MetersParser

        :param meters_file: File
        :param org_id: int
        :param source_type: int, type of meter data
        :param property_id: int, id of property - required if meter data is for a specific property (e.g. GreenButton)
        :return: MetersParser
        """
        if source_type == Meter.GREENBUTTON:
            parser = reader.GreenButtonParser(meters_file)
            raw_meter_data = list(parser.data)
            return cls(org_id, raw_meter_data, source_type=Meter.GREENBUTTON, property_id=property_id)

        try:
            # try to parse the file as if it came from "Download your entire portfolio"
            # spreadsheet (the original method for importing PM meter data)
            parser = reader.MCMParser(meters_file, sheet_name='Meter Entries')
            raw_meter_data = list(parser.data)
            return cls(org_id, raw_meter_data)
        except reader.SheetDoesNotExist:
            # try to parse the file as one from a Data Request
            parser = reader.MCMParser(meters_file, sheet_name='Monthly Usage')
            raw_meter_data = cls.preprocess_raw_pm_data_request(parser.data)
            return cls(org_id, raw_meter_data, source_type=Meter.PORTFOLIO_MANAGER_DATA_REQUEST)

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
            # reset _cache_proposed_imports
            self._cache_proposed_imports = None

            if self._source_type == Meter.PORTFOLIO_MANAGER or self._source_type == Meter.PORTFOLIO_MANAGER_DATA_REQUEST:
                self._parse_pm_meter_details()
            elif self._source_type == Meter.GREENBUTTON:
                self._parse_gb_meter_details()

            self._cache_meter_and_reading_objs = list(self._unique_meters.values())

        return self._cache_meter_and_reading_objs

    @property
    def proposed_imports(self):
        """
        Summarizes meters and readings that will be created via file import.

        If this is a GreenButton import, take the UsagePoint as the source_id.
        """
        if self._cache_meter_and_reading_objs is None:
            # Making sure to build out meters and meter readings first
            self.meter_and_reading_objs

        if self._cache_proposed_imports is None:
            self._cache_proposed_imports = []
            energy_type_lookup = dict(Meter.ENERGY_TYPES)

            # Gather info based on property_id - cycles (query) and related pm_property_ids (parsed in different method)
            property_ids_info = {}
            for pm_property_id, property_ids in self._source_to_property_ids.items():
                for property_id in property_ids:
                    property_ids_info[property_id] = {'pm_id': pm_property_id}

                    cycle_names = list(
                        PropertyView.objects.select_related('cycle').
                        order_by('cycle__end').
                        filter(property_id=property_id).
                        values_list('cycle__name', flat=True)
                    )
                    property_ids_info[property_id]['cycles'] = ', '.join(cycle_names)

            # Put summaries together based on source type
            for meter in self.meter_and_reading_objs:
                meter_summary = {
                    'type': energy_type_lookup[meter['type']],
                    'incoming': len(meter.get("readings")),
                    'property_id': meter['property_id'],
                }

                id = meter.get("source_id")
                if meter['source'] == Meter.PORTFOLIO_MANAGER or meter['source'] == Meter.PORTFOLIO_MANAGER_DATA_REQUEST:
                    property_id_info = property_ids_info[meter.get("property_id")]

                    meter_summary['source_id'] = id
                    meter_summary['pm_property_id'] = property_id_info['pm_id']
                    meter_summary['cycles'] = property_id_info['cycles']
                else:
                    meter_summary['source_id'] = usage_point_id(id)

                self._cache_proposed_imports.append(meter_summary)

        return self._cache_proposed_imports

    def _parse_pm_meter_details(self):
        """
        For each given raw meter and reading detail, go through the multi-step
        process to separate and parse details for both meters and related
        meter_readings that will later be used to build the meter and
        meter_reading objects.

        The main difference between PM and GB meter imports are how
        start and end times are read. Also, PM meters have the possibility of
        having cost associated to individual raw details.
        """
        for raw_details in self._meters_and_readings_details:
            meter_details = {
                'source': self._source_type,
            }

            meter_details['source_id'] = str(raw_details['Portfolio Manager Meter ID'])

            # Continue/skip, if no property is found.
            given_property_id = str(raw_details['Portfolio Manager ID'])
            if not self._get_property_id(given_property_id, meter_details):
                continue

            # Define start_time and end_time
            raw_start = raw_details['Start Date']
            if raw_start == 'Not Available':
                """
                In this case, the meter is delivered, so the start and end times
                are set to the first of delivery date month to the first of the
                following month.
                """
                delivery_date = datetime.strptime(raw_details['Delivery Date'], "%Y-%m-%d %H:%M:%S")
                year = delivery_date.year
                month = delivery_date.month
                _start_day, days_in_month = monthrange(year, month)

                unaware_start = datetime(year, month, 1, 0, 0, 0)
                unaware_end = datetime(year, month, days_in_month, 23, 59, 59) + timedelta(seconds=1)
            else:
                unaware_start = datetime.strptime(raw_start, "%Y-%m-%d %H:%M:%S")
                unaware_end = datetime.strptime(raw_details['End Date'], "%Y-%m-%d %H:%M:%S")

            start_time = make_aware(unaware_start, timezone=self._tz)
            end_time = make_aware(unaware_end, timezone=self._tz)

            successful_parse = self._parse_meter_readings(raw_details, meter_details, start_time, end_time)

            # If Cost field is present and value is available, create Cost Meter and MeterReading
            if successful_parse and raw_details.get('Cost ($)', 'Not Available') != 'Not Available':
                carry_overs = ['property_ids', 'source', 'source_id', 'type']
                meter_details_copy = {k: meter_details[k] for k in carry_overs}
                self._parse_cost_meter_reading(raw_details, meter_details_copy, start_time, end_time)

    def _parse_gb_meter_details(self):
        """
        For each given raw meter and reading detail, go through the multi-step
        process to separate and parse details for both meters and related
        meter_readings that will later be used to build the meter and
        meter_reading objects.

        The main difference between PM and GB meter imports are how
        start and end times are read.
        """
        for raw_details in self._meters_and_readings_details:
            meter_details = {
                'source': self._source_type,
                'source_id': raw_details['source_id'],
                'property_ids': [self._property_id],
            }

            # Define start_time and end_time
            start_time = datetime.fromtimestamp(raw_details['start_time'], tz=self._tz)
            end_time = datetime.fromtimestamp((raw_details['start_time'] + raw_details['duration']), tz=self._tz)

            self._parse_meter_readings(raw_details, meter_details, start_time, end_time)

    def _get_property_id(self, source_id, shared_details):
        """
        Using pm_property_id, find and cache property_ids to avoid querying for
        the same property_id more than once. Return True when a property_id is
        found.

        If no ProperyStates (and subsequent Properties) are found, flag the
        PM ID as unlinkable, and False is returned.
        """
        # If the PM ID has been previously found to be unlinkable, return False
        if source_id in self._unlinkable_pm_ids:
            return False

        # Check cached property_ids
        target_property_ids = self._source_to_property_ids.get(source_id, None)
        if target_property_ids is not None:
            shared_details['property_ids'] = target_property_ids
            return True

        # Start looking for possible matches - if some are found, capture all property_ids
        possible_matches = PropertyState.objects.filter(
            pm_property_id=source_id,
            organization_id=self._org_id
        )
        if possible_matches.count() == 0:
            self._unlinkable_pm_ids.add(source_id)
            return False
        else:
            target_property_ids = list(
                PropertyView.objects.
                filter(state_id__in=Subquery(possible_matches.values('pk'))).
                distinct('property_id').
                values_list('property_id', flat=True)
            )

            shared_details['property_ids'] = target_property_ids
            self._source_to_property_ids[source_id] = target_property_ids

            return True

    def _parse_meter_readings(self, raw_details, meter_details, start_time, end_time):
        """
        Build a meter reading object and distribute it to meters according to
        the meter details' property_ids.
        """
        # Parse the conversion factor else return False
        type_name = raw_details['Meter Type']
        unit = raw_details['Usage Units']
        conversion_factor = self._kbtu_thermal_conversion_factors.get(type_name, {}).get(unit, None)
        if conversion_factor is None:
            return False

        meter_details['type'] = Meter.type_lookup[type_name]

        meter_reading = {
            'start_time': start_time,
            'end_time': end_time,
            'reading': float(raw_details['Usage/Quantity']) * conversion_factor,
            'source_unit': unit,
            'conversion_factor': conversion_factor
        }

        self.distribute_meter_reading(meter_reading, meter_details)

        return True

    def _parse_cost_meter_reading(self, raw_details, meter_details, start_time, end_time):
        """
        The logic is very similar to _parse_pm_meter_details, except this is
        specifically for cost. Also, it's assumed all meter_details are
        populated except for type.
        """
        meter_details['type'] = Meter.COST

        unit = '{} Dollars'.format(self._org_country)

        meter_reading = {
            'start_time': start_time,
            'end_time': end_time,
            'reading': float(raw_details['Cost ($)']),
            'source_unit': unit,
            'conversion_factor': 1
        }

        self.distribute_meter_reading(meter_reading, meter_details)

    def distribute_meter_reading(self, meter_reading, meter_details):
        """
        If a meter has not yet been parsed, its first reading details are saved
        in a list. If a meter was previously parsed and has readings already,
        any new readings are appended to that list.
        """
        for property_id in meter_details.get('property_ids', []):
            meter_details_copy = meter_details.copy()
            del meter_details_copy['property_ids']
            meter_details_copy['property_id'] = property_id

            meter_identifier = '-'.join([str(meter_details_copy[k]) for k in sorted(meter_details_copy)])

            existing_property_meter = self._unique_meters.get(meter_identifier, None)

            if existing_property_meter is None:
                meter_details_copy['readings'] = [meter_reading]

                self._unique_meters[meter_identifier] = meter_details_copy
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

    @staticmethod
    def preprocess_raw_pm_data_request(raw_data):
        """Reformats the raw data. Must be called on meter data which comes
        from a Data Request spreadsheet, _before_ intializing the MetersParser
        class with the data.

        :param raw_data: list[dict], `.data` from MCMParser for the Monthly Usage sheet
        :return: list[dict], processed meter readings for initialization of MetersParser
        """
        # kinda lazy but convert the generator to a list
        raw_data = list(raw_data)

        if not raw_data:
            return []

        # check which (if any) meter readings are provided
        # there can be more than one reading type per row (e.g. both electricity
        # and natural gas in the same row)
        provided_reading_types = []
        for field in raw_data[0].keys():
            if field.startswith('Electricity Use') or field.startswith('Natural Gas Use'):
                provided_reading_types.append(field)

        if not provided_reading_types:
            return []

        TYPE_AND_UNITS_REGEX = re.compile(r'(?P<meter_type>.*)\s+\((?P<units>.*)\)')
        METER_TYPE_MAPPING = {
            'Electricity Use': 'Electric - Unknown',
            'Natural Gas Use': 'Natural Gas',
        }
        METER_UNITS_MAPPING = {
            'kBtu': 'kBtu (thousand Btu)',
            'GJ': 'GJ',
        }

        results = []
        for raw_reading in raw_data:
            start_date = datetime.strptime(raw_reading['Month'], '%b-%y')
            _, days_in_month = monthrange(start_date.year, start_date.month)
            end_date = datetime(
                start_date.year,
                start_date.month,
                days_in_month,
                23,
                59,
                59
            ) + timedelta(seconds=1)

            for reading_type in provided_reading_types:
                if not raw_reading[reading_type].strip() or 'not available' in raw_reading[reading_type].lower():
                    continue

                type_and_units_match = TYPE_AND_UNITS_REGEX.match(reading_type)
                if type_and_units_match is None:
                    raise Exception(f'Failed to parse meter type and units from "{reading_type}"')

                meter_type_match = type_and_units_match.group('meter_type').strip()
                meter_type = METER_TYPE_MAPPING.get(meter_type_match)
                if meter_type is None:
                    raise Exception(f'Invalid meter type "{meter_type_match}"')

                units_match = type_and_units_match.group('units').strip()
                units = METER_UNITS_MAPPING.get(units_match)
                if units is None:
                    raise Exception(f'Invalid units "{units_match}"')

                reading = {
                    'Start Date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'End Date': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'Portfolio Manager ID': raw_reading['Property Id'],
                    'Portfolio Manager Meter ID': 'Unknown',
                    'Meter Type': meter_type,
                    'Usage/Quantity': raw_reading[reading_type],
                    'Usage Units': units,
                }
                results.append(reading)

        return results
