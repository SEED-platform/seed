import os

from seed.energy.pm_energy_template import template_to_json as tm
from seed.energy.pm_energy_template import post_process as ps

import logging
_log = logging.getLogger(__name__)

def parse_energy_template(template_file_path):
    tm.pm_to_json(template_file_path)
    json_data = ps.post_process(template_file_path)

    return json_data
