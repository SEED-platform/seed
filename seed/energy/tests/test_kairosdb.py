from django.test import TestCase

from seed.energy.tsdb.kairosdb import kairosdb_detector

class DetectKairosDB(TestCase):
    if kairosdb_detector.detect():
        print 'KairosDB found'
    else:
        print 'KairosDB not found'
