from django.test import TestCase

from django.conf import settings
from seed.energy.meter_data_processor import green_button_driver as driver
from seed.energy.meter_data_processor import green_button_data_analyser as analyser
from seed.models import (
    CanonicalBuilding,
)


class GreenButtonRequest(TestCase):
    def test_save_green_button_data(self):
        url = 'https://epo.schneider-electric.com/PEPCO/espi/1_1/resource/Batch/Subscription.aspx?SubscriptionID=C8C25FC1C944B813A5CB790&Published_Min=11/1/2015&Published_Max=11/1/2015'
        new_canonical_bld = CanonicalBuilding(id=99999, active=False)
        new_canonical_bld.save()

        ts_data = driver.get_gb_data(url, 99999)
        self.assertTrue(ts_data)
        analyser.data_analyse(ts_data, 'GreenButton')
