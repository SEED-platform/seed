import logging

import pandas as pd
from seed.energy.pm_energy_template import post_process as ps
from seed.energy.pm_energy_template import template_to_json as tm

_log = logging.getLogger(__name__)


def parse_energy_template_file(template_file_path):
    meter_con_df = pd.read_excel(template_file_path, sheetname=0)
    return parse_energy_template(meter_con_df)


def parse_energy_template(template_file_path):
    processed_json = tm.pm_to_json(template_file_path)
    json_data = ps.post_process(processed_json)

    return json_data
