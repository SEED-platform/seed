import glob
import json
import logging
import re

_log = logging.getLogger(__name__)


def ns2s(string):
    '''
    Convert unit of time from 'ns' to 's'
    '''

    return string.replace('000000000,', ',')


def post_process(file_path):
    json_file_path = file_path[len(file_path):-5] + '_json.txt'
    filelist = glob.glob(json_file_path)
    for file_in in filelist:
        _log.info('post process {0}'.format(file_in))
        _log.debug('debuging')
        with open(file_in, 'r+') as r_in:
            json_data = json.loads(r_in.read())
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

                if not data['custom_id']:
                    data['custom_id'] = '1'  # default custom id is 1

                for k, v in data.iteritems():
                    data[k] = re.sub('[^\w|\.|]', '_', str(v))

            post_processed = json.dumps(json_data)
            post_processed = ns2s(post_processed)

        file_out = file_path[len(file_path):-5] + '_post.txt'
        with open(file_out, 'w') as out:
            out.write(post_processed)

        return json.loads(post_processed)
