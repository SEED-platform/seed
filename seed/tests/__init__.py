"""
:copyright: (c) 2014 Building Energy Inc
"""
from django.conf import settings

if 'nose' not in settings.TEST_RUNNER:
    from .test_views import DataImporterViewTests
