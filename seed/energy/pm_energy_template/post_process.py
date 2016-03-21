import glob
import json
import logging
import re

_log = logging.getLogger(__name__)


def post_process(json_data):
    for data in json_data:
        meter_type = data['energy_type']
        data['tens'] = 0
        if meter_type == 'Natural Gas':
            data['energy_type_int'] = '1'
        else:
            data['energy_type_int'] = '0'  # default electricity

        uom = data['uom']
        if uom == 'kBtu (thousand Btu)':
            data['uom_int'] = '132'
            data['tens'] = 3
        elif uom == 'KGal (thousand gallons) (US)':
            data['uom_int'] = '134'    # litre
            data['value'] = str(float(data['value']) * 3.78541)
            data['tens'] = 3
        else:
            data['uom_int'] = '72'  # default Wh

        for k, v in data.iteritems():
            data[k] = re.sub('[^\w|\.|]', '_', str(v))

    post_processed = json.dumps(json_data)

    return json.loads(post_processed)
