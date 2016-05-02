from django.test import TestCase

from seed.energy.meter_data_processor import green_button_driver as driver
from seed.energy.meter_data_processor import green_button_data_analyser as analyser

from django.db.models.signals import post_save
from django.dispatch import receiver

from seed.models import (
    CanonicalBuilding,
)


class GreenButtonRequest(TestCase):
    def test_save_green_button_data(self):
        url = 'https://epo.schneider-electric.com/PEPCO/espi/1_1/resource/Batch/Subscription.aspx?SubscriptionID=C8C25FC1C944B813A5CB790&Published_Min=11/1/2015&Published_Max=11/1/2015'
        new_canonical_bld = CanonicalBuilding(id=99999, active=True)
        new_canonical_bld.save(force_insert=True)


@receiver(post_save, sender=CanonicalBuilding, dispatch_uid="GreenButtonRequest_cont")
def GreenButtonRequest_cont(sender, instance, **kwargs):
    print "Post save signal captured"
    test_bld = CanonicalBuilding.objects.get(pk=99999)
    self.assertTrue(test_bld)

    if test_bld.active:
        test_bld.active = False

        ts_data = driver.get_gb_data(url, 99999)
        self.assertTrue(ts_data)
        analyser.data_analyse(ts_data, 'GreenButton')
