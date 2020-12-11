# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from datetime import datetime
from io import BytesIO

from lxml import etree
from xmlschema.validators.exceptions import XMLSchemaValidationError

from pytz import timezone

from django.test import TestCase
from django.utils.timezone import make_aware

from config.settings.common import TIME_ZONE

from seed.landing.models import SEEDUser as User
from seed.models import Meter, MeterReading, Analysis, AnalysisPropertyView
from seed.test_helpers.fake import (
    FakePropertyViewFactory
)
from seed.utils.organizations import create_organization
from seed.analysis_pipelines.bsyncr import _build_bsyncr_input
from seed.building_sync.building_sync import BuildingSync
from seed.building_sync.mappings import NAMESPACES


class TestBsyncrPipeline(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user)

        self.property_view = FakePropertyViewFactory(organization=self.org).get_property_view(
            latitude=39.76550841416409,
            longitude=-104.97855661401148
        )

        self.meter = Meter.objects.create(
            property=self.property_view.property,
            source=Meter.PORTFOLIO_MANAGER,
            source_id="Source ID",
            type=Meter.ELECTRICITY_GRID,
        )
        tz_obj = timezone(TIME_ZONE)
        self.meter_reading = MeterReading.objects.create(
            meter=self.meter,
            start_time=make_aware(datetime(2018, 1, 1, 0, 0, 0), timezone=tz_obj),
            end_time=make_aware(datetime(2018, 1, 2, 0, 0, 0), timezone=tz_obj),
            reading=12345,
            source_unit='kWh',
            conversion_factor=1.00
        )

        self.analysis = Analysis.objects.create(
            name='Quite neat',
            service=Analysis.BSYNCR,
            status=Analysis.CREATING,
            user=self.user,
            organization=self.org
        )

        analysis_view_ids, _ = AnalysisPropertyView.batch_create(self.analysis.id, [self.property_view.id])
        self.analysis_property_view = AnalysisPropertyView.objects.get(id=analysis_view_ids[0])

    def test_build_bsyncr_input_returns_valid_bsync_document(self):
        # Act
        doc, errors = _build_bsyncr_input(self.analysis_property_view, self.meter)
        tree = etree.parse(BytesIO(doc))

        # Assert
        self.assertEqual(0, len(errors))

        ts_elems = tree.xpath('//auc:TimeSeries', namespaces=NAMESPACES)
        self.assertEqual(self.meter.meter_readings.count(), len(ts_elems))

        # throws exception if document is not valid
        schema = BuildingSync.get_schema(BuildingSync.BUILDINGSYNC_V2_2_0)
        schema.validate(tree)

    def test_build_bsyncr_input_returns_errors_if_state_missing_info(self):
        # Setup
        # remove some required fields
        property_state = self.analysis_property_view.property_state
        property_state.latitude = None
        property_state.longitude = None
        property_state.save()

        # Act
        doc, errors = _build_bsyncr_input(self.analysis_property_view, self.meter)

        # Assert
        self.assertIsNone(doc)
        self.assertEqual(2, len(errors))
        self.assertTrue('Linked PropertyState is missing longitude' in errors)
        self.assertTrue('Linked PropertyState is missing latitude' in errors)

    def test_build_bsyncr_input_returns_error_if_reading_missing_value(self):
        # Setup
        # remove some required fields
        self.meter_reading.reading = None
        self.meter_reading.save()

        # Act
        doc, errors = _build_bsyncr_input(self.analysis_property_view, self.meter)

        # Assert
        self.assertIsNone(doc)
        self.assertEqual(1, len(errors))
        self.assertTrue('has no reading value' in errors[0])
