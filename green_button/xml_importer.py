import xmltodict
from collections import Iterable

from data_importer.models import ROW_DELIMITER
from seed.models import (
    BuildingSnapshot,
    Meter,
    TimeSeries,
    CanonicalBuilding,
    set_initial_sources,
    GREEN_BUTTON_BS,
)
import seed.models
from audit_logs.models import AuditLog
from datetime import datetime


def energy_type(service_category):
    """
    Returns the seed model energy type corresponding to the green button
    service category.

    :param service_category: int that is a green button service_category
    (string args will be converted to ints)
    :returns: int in seed.models.ENERGY_TYPES
    """

    # Valid values include: 0 - electricity 1 - gas 2 - water 4 - pressure
    # 5 - heat 6 - cold 7 - communication 8 - time

    # green_button example data only contains electricity and gas.
    # We will need to add more energy types to support the types
    # not present in seed.models.ENERGY_TYPES
    service_category = int(service_category)
    category_mapping = {
        0: seed.models.ELECTRICITY,
        1: seed.models.NATURAL_GAS,
    }

    if service_category in category_mapping:
        return category_mapping[service_category]
    else:
        return None


def energy_units(uom):
    """
    Returns the seed model energy unit corresponding to the green button uom.

    :param uom: int that is the green button uom number corresponding to the
    energy units supported by the green button schema (string args will be
    converted to ints)
    :returns: int in seed.models.ENERGY_UNITS
    """
    uom = int(uom)

    # example data only contains 72 and 169 (Wattt-hours and Therms)
    # currently only support those types

    # uom types
    # Valid values include: 0 = Not Applicable 5 = A (Current) 29 = Voltage
    # 31 = J (Energy joule) 33 = Hz (Frequency) 38 = Real power (Watts)
    # 42 = m3 (Cubic Meter) 61 = VA (Apparent power) 63 = VAr (Reactive power)
    # 65 = Cos? (Power factor) 67 = V^2 (Volts squared) 69 = A^2 (Amp squared)
    # 71 = VAh (Apparent energy) 72 = Real energy (Watt-hours)
    # 73 = VArh (Reactive energy)
    # 106 = Ah (Ampere-hours / Available Charge) 119 = ft3 (Cubic Feet)
    # 122 = ft3/h (Cubic Feet per Hour) 125 = m3/h (Cubic Meter per Hour)
    # 128 = US gl (US Gallons) 129 = US gl/h (US Gallons per Hour)
    # 130 = IMP gl (Imperial Gallons)
    # 131 = IMP gl/h (Imperial Gallons per Hour)
    # 132 = BTU 133 = BTU/h 134 = Liter 137 = L/h (Liters per Hour)
    # 140 = PA(gauge) 155 = PA(absolute) 169 = Therm

    unit_mapping = {
        72: seed.models.WATT_HOURS,
        169: seed.models.THERMS
    }

    if uom in unit_mapping:
        return unit_mapping[uom]
    else:
        return None


def as_collection(val):
    """
    Takes a value, returns that value if it is not a string and is an
    Iterable, and returns a list containing that value if it is not an
    Iterable or if it is a string. Returns None when val is None.

    :params val: any value
    :returns: list containing val or val if it is Iterable and not a string.
    """
    is_atomic = (
        isinstance(val, basestring) or
        isinstance(val, dict) or
        (not isinstance(val, Iterable))
    )

    if val is None:
        return None
    elif is_atomic:
        return [val]
    else:
        return val


def interval_data(reading_xml_data):
    """
    Takes a dictionary representing the contents of an IntervalReading
    xml node and pulls out data for a single timeseries reading. The
    dictionary will be a sub-dictionary of the dictionary returned by
    xmltodict.parse when called on a green button xml file. Returns a
    flat dictionary containing the interval data.

    :params reading_xml_data: dictionary of IntervalReading xml node
    content in format specified by the xmltodict library.
    :returns: dictionary representing a time series reading with keys
    'cost', 'value', 'start_time', and 'duration'.
    """
    cost = reading_xml_data['cost']
    value = reading_xml_data['value']

    time_period = reading_xml_data['timePeriod']
    start_time = time_period['start']
    duration = time_period['duration']

    result = {
        'cost': cost,
        'value': value,
        'start_time': start_time,
        'duration': duration
    }

    return result


def meter_data(raw_meter_meta):
    """
    Takes a dictionary representing the contents of the entry node in
    a green button xml file that specifies the meta data about the meter
    that was used to record time series data for that file. Returns a
    flat dictionary containing the meter meta data.

    :params raw_meter_meta: dictionary of the contents of the meter
    specification entry node in a green button xml file
    :returns: dictionary containing information about a meter with keys
    'currency', 'power_of_ten_multiplier', amd 'uom'
    """
    params_data = raw_meter_meta['content']['ReadingType']

    # our green button example data ReadingType's only contain
    # currency, powerOfTenMultiplier, and uom.
    # this function currently assumes those types are present and does
    # not check for any other types

    currency = params_data['currency']
    power_of_ten_multiplier = params_data['powerOfTenMultiplier']
    uom = params_data['uom']

    result = {
        'currency': currency,
        'power_of_ten_multiplier': power_of_ten_multiplier,
        'uom': uom
    }

    return result


def interval_block_data(ib_xml_data):
    """
    Takes a dictionary containing the contents of an IntervalBlock node
    from a green button xml file and returns a dictionary containing the
    start_time of the timeseries collection, the duration of the collection,
    and a list of readings containing the time series data from a meter.

    :params ib_xml_data: dictionary of the contents of an IntervalBlock
    from a green button xml file
    :returns: dictionary containing meta data about an entire collection
    period and a list of the specific meter readings
    """
    interval = ib_xml_data['interval']

    raw_readings_data = as_collection(ib_xml_data['IntervalReading'])
    readings_data = [interval_data(data) for data in raw_readings_data]

    block_data = {
        'start_time': interval['start'],
        'duration': interval['duration'],
        'readings': readings_data
    }

    return block_data


def building_data(xml_data):
    """
    Extracts information about a building from a Green Button xml file.

    :params xml_data: dictionary returned by xmltodict.parse when called
    on the contents of a green button xml file
    :returns: dictionary containing:
      - building information for a green button xml file
      - information describing the meter used for collection
      - list of time series meter reading data
    """
    entries = xml_data['feed']['entry']
    info_entry = next(entry for entry in entries)

    meta_data, meter_reading_decl, meter_params, reading_intervals = entries

    address = meta_data['title']['#text']

    # '0' - electricity, '1' - gas
    s_category = info_entry['content']['UsagePoint']['ServiceCategory']['kind']

    # time series data
    raw_interval_block = reading_intervals['content']['IntervalBlock']
    block_data = interval_block_data(raw_interval_block)

    # meter meta data
    m_data = meter_data(meter_params)

    result = {
        'address': address,
        'service_category': s_category,
        'meter': m_data,
        'interval': block_data
    }

    return result


def create_models(data, import_file):
    """
    Create a BuildingSnapshot, a CanonicalBuilding, and a Meter. Then, create
    TimeSeries models for each meter reading in data.

    :params data: dictionary of building data from a green button xml file
    in the form returned by xml_importer.building_data
    :params import_file: ImportFile referencing the original xml file; needed
    for linking to BuildingSnapshot and for determining super_organization
    :returns: the created CanonicalBuilding
    """
    # cache data on import_file; this is a proof of concept and we
    # only have two example files available so we hardcode the only
    # heading present.
    import_file.cached_first_row = ROW_DELIMITER.join(["address"])
    import_file.cached_second_to_fifth_row = ROW_DELIMITER.join(
        [data['address']]
    )
    import_file.save()

    raw_bs = BuildingSnapshot()
    raw_bs.import_file = import_file

    # We require a save to get our PK
    # We save here to set our initial source PKs.
    raw_bs.save()
    super_org = import_file.import_record.super_organization
    raw_bs.super_organization = super_org

    set_initial_sources(raw_bs)
    raw_bs.address_line_1 = data['address']
    raw_bs.source_type = GREEN_BUTTON_BS

    raw_bs.save()

    # create canonical building
    cb = CanonicalBuilding.objects.create(canonical_snapshot=raw_bs)

    raw_bs.canonical_building = cb
    raw_bs.save()

    # log building creation
    AuditLog.objects.create(
        organization=import_file.import_record.super_organization,
        user=import_file.import_record.owner,
        content_object=cb,
        action="create_building",
        action_note="Created building",
    )

    # create meter for this dataset (each dataset is a single energy type)
    e_type = energy_type(data['service_category'])
    e_type_string = next(
        pair[1] for pair in seed.models.ENERGY_TYPES if pair[0] == e_type
    )

    m_name = "gb_{0}[{1}]".format(str(raw_bs.id), e_type_string)
    m_energy_units = energy_units(data['meter']['uom'])
    meter = Meter.objects.create(
        name=m_name, energy_type=e_type, energy_units=m_energy_units
    )

    meter.building_snapshot.add(raw_bs)
    meter.save()

    # now timeseries data for the meter
    for reading in data['interval']['readings']:

        start_time = int(reading['start_time'])
        duration = int(reading['duration'])

        begin_time = datetime.fromtimestamp(start_time)
        end_time = datetime.fromtimestamp(start_time + duration)
        value = reading['value']
        cost = reading['cost']

        new_ts = TimeSeries.objects.create(
            begin_time=begin_time,
            end_time=end_time,
            reading=value,
            cost=cost
        )

        new_ts.meter = meter
        new_ts.save()

    return cb


def import_xml(import_file):
    """
    Given an import_file referencing a raw green button xml file, extracts
    building and timeseries information from the file and constructs
    required database models.

    :params import_file: a seed.models.ImportFile instance representing a
    green button xml file that has been previously uploaded
    :returns: the created CanonicalBuilding Inst.
    """
    xml_file = import_file.local_file
    xml_string = xml_file.read()
    raw_data = xmltodict.parse(xml_string)

    data = building_data(raw_data)
    return create_models(data, import_file)
