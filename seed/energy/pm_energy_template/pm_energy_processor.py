import os

from seed.energy.pm_energy_template import pm_to_template as pm
from seed.energy.pm_energy_template import energy_template_process as pe

import logging
_log = logging.getLogger(__name__)

def parse_pm_energy_file(pm_file_path):
    pm.read_pm(pm_file_path)
    _log.info('\nend converting pm to template')

