import logging
import xml.etree.ElementTree as ET

import requests
import tempfile

from seed.energy.meter_data_processor import green_button_parser as parser


_log = logging.getLogger(__name__)


def request_green_button_by_url(url):
    # TODO SSL Verification is disabled
    response = requests.get(url, verify=False)
    if(response.status_code == 200):
        _log.info('Get GreenButton XML file successfully')
        xml_data = response.text

        # save the file in a tmp directory -- based on ENV variables
        f = tempfile.NamedTemporaryFile(prefix='green_button_', suffix='.xml', delete=False)
        f.write(xml_data)
        f.close()

        root = ET.fromstring(xml_data)
        return root
    else:
        _log.error('Request GreenButton Data Error '.response.status_code)
        return None


def request_green_button_by_file(path):
    root = ET.parse(path).getroot()
    return root


def get_gb_data(url, building_id):
    root = request_green_button_by_url(url)

    if root is None:
        return None

    ts_data = parser.gb_xml_parser(root, building_id)
    return ts_data
