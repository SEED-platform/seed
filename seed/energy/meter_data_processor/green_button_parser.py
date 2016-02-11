import logging

from seed.energy.meter_data_processor import green_button_maps
_log = logging.getLogger(__name__)

root_ns = '{http://www.w3.org/2005/Atom}'
gb_ns = '{http://naesb.org/espi}'


def get_link_href_head(link):
    href = link.get('href')
    if href[0:1] == '/':
        href = href[1:]
    first_slash = href.find('/')
    return href[0:first_slash]


def get_link_href_tail(link):
    href = link.get('href')
    last_slash = href.rfind('/')
    return href[(last_slash + 1):]


def parse_usage(up_type):
    '''
    Return {kind}
    '''

    sc = up_type.find(root_ns + 'content').find(gb_ns + 'UsagePoint').find(gb_ns + 'ServiceCategory')
    # TODO may need more ServiceCategory info
    sc_info = {}
    sc_info['kind'] = sc.find(gb_ns + 'kind').text
    return sc_info


def parse_reading_type(rt_entry):
    '''
    Return {kind, tens, uom}
    '''

    rt = rt_entry.find(root_ns + 'content').find(gb_ns + 'ReadingType')
    # TODO may need more ReadingType info
    rt_info = {}
    rt_info['kind'] = rt.find(gb_ns + 'kind').text
    rt_info['tens'] = rt.find(gb_ns + 'powerOfTenMultiplier').text
    rt_info['uom'] = rt.find(gb_ns + 'uom').text
    return rt_info


def get_reading_type_id_of_meter(mr_entry):
    '''
    Return ReadingType id or NULL if failed
    '''

    links = mr_entry.findall(root_ns + 'link[@rel="related"]')
    for link in links:
        head = get_link_href_head(link)
        if head == 'ReadingType':
            return link.get('href')
    return None


def parse_interval_reading(reading):
    '''
    Return {ts_start, value}
    '''

    time_period = reading.find(gb_ns + 'timePeriod')

    res = {}
    res['ts_start'] = time_period.find(gb_ns + 'start').text
    res['interval'] = time_period.find(gb_ns + 'duration').text
    res['value'] = reading.find(gb_ns + 'value').text

    return res


def clean_up_for_key(key):
    '''
    Replace undesired special characters for key
    '''

    return key.replace(key, '/', '_')


def gb_xml_parser(root, building_id):
    entries = root.findall(root_ns + 'entry')

    usage_info_map = {}
    reading_type_map = {}
    interval_block_array = []

    # Sequence requirements: UsagePoint->MeterReading->IntervalBlock
    for entry in entries:
        up_link = entry.find(root_ns + 'link[@rel="up"]')
        self_link = entry.find(root_ns + 'link[@rel="self"]')

        if up_link is None or self_link is None:
            _log.error('GreenButton XML format is not valid ' + str(building_id))
            return None

        type = get_link_href_tail(up_link)
        if type == 'UsagePoint':
            usage_point_id = get_link_href_tail(self_link)

            # Parse UsagePoint, get service category kind
            usage_info = parse_usage(entry)
            usage_info_map[usage_point_id] = usage_info
        elif type == 'MeterReading':
            meter_id = get_link_href_tail(self_link)

            # Get corresponding ReadingType
            ref_reading_type_id = get_reading_type_id_of_meter(entry)
        elif type == 'IntervalBlock':
            interval_block_id = get_link_href_tail(self_link)

            interval_block_cell = {}
            interval_block_cell['usage_point_id'] = usage_point_id
            interval_block_cell['meter_id'] = meter_id
            interval_block_cell['ref_reading_type_id'] = ref_reading_type_id
            interval_block_cell['interval_block_id'] = interval_block_id
            interval_block_cell['element'] = entry

            interval_block_array.append(interval_block_cell)
        elif type == 'ReadingType':
            reading_type_id = self_link.get('href')

            # Parse ReadingType
            reading_type_info = parse_reading_type(entry)
            reading_type_map[reading_type_id] = reading_type_info

    # Extract data from interval blocks
    ts_data = []
    for interval_block_cell in interval_block_array:
        usage_point_id = interval_block_cell['usage_point_id']
        meter_id = interval_block_cell['meter_id']
        interval_block_id = interval_block_cell['interval_block_id']
        ref_reading_type_id = interval_block_cell['ref_reading_type_id']
        entry = interval_block_cell['element']

        usage_info = usage_info_map[usage_point_id]
        reading_info = reading_type_map[ref_reading_type_id]

        blocks = entry.find(root_ns + 'content').findall(gb_ns + 'IntervalBlock')
        for block in blocks:
            interval_readings = block.findall(gb_ns + 'IntervalReading')
            for interval_reading in interval_readings:
                interval_reading_info = parse_interval_reading(interval_reading)

                ts_cell = {}
                ts_cell['start'] = interval_reading_info['ts_start']
                ts_cell['value'] = interval_reading_info['value']

                ts_cell['interval'] = interval_reading_info['interval']

                ts_cell['canonical_id'] = building_id
                ts_cell['custom_meter_id'] = usage_point_id
                ts_cell['meter_id'] = meter_id
                ts_cell['interval_block_id'] = interval_block_id
                # TODO add new data here

                usage_kind_string = green_button_maps.map_usage_kind(usage_info['kind'])
                ts_cell['energy_type'] = usage_kind_string
                ts_cell['energy_type_int'] = usage_info['kind']

                reading_kind_string = green_button_maps.map_reading_kind(reading_info['kind'])
                ts_cell['reading_kind'] = reading_kind_string
                ts_cell['reading_kind_int'] = reading_info['kind']

                ts_cell['tens'] = reading_info['tens']

                uom_string = green_button_maps.map_uom(reading_info['uom'])
                ts_cell['uom'] = uom_string
                ts_cell['uom_int'] = reading_info['uom']

                ts_data.append(ts_cell)

    return ts_data
