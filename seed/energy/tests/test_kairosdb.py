from django.test import TestCase

from seed.energy.tsdb.kairosdb import kairosdb_detector


class KairosDB(TestCase):
    def test_detect_kairosdb(self):
        if kairosdb_detector.detect():
            print 'KairosDB found'
        else:
            print 'KairosDB not found'
