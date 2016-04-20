import logging

from seed.energy.pm_energy_template import pm_to_template as pm
_log = logging.getLogger(__name__)


def parse_pm_energy_file(pm_file_path):
    return pm.read_pm(pm_file_path)
