# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from datetime import datetime
from io import BytesIO

from lxml import etree

from pytz import timezone

from django.db.models import Q
from django.test import TestCase
from django.utils.timezone import make_aware

from config.settings.common import TIME_ZONE

from seed.landing.models import SEEDUser as User
from seed.models import (
    Meter,
    MeterReading,
    Analysis,
    PropertyState,
    AnalysisInputFile,
    AnalysisMessage,
    AnalysisPropertyView,
)
from seed.test_helpers.fake import (
    FakeAnalysisFactory,
    FakeAnalysisPropertyView,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.utils.organizations import create_organization
from seed.analysis_pipelines.pipeline import AnalysisPipelineException
from seed.analysis_pipelines.bsyncr import _build_bsyncr_input, BsyncrPipeline
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

        property_state = (
            FakePropertyStateFactory(organization=self.org).get_property_state(
                # fields required for analysis
                latitude=39.76550841416409,
                longitude=-104.97855661401148
            )
        )
        self.analysis_property_view = (
            FakeAnalysisPropertyView(organization=self.org, user=self.user).get_analysis_property_view(
                property_state=property_state,
                # analysis args
                name='Quite neat',
                service=Analysis.BSYNCR,
            )
        )

        self.meter = Meter.objects.create(
            property=self.analysis_property_view.property,
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

        #
        # Setup more properties with linked meters with 12 valid meter readings.
        # These properties, unmodified, should successfully run thorugh the bsyncr pipeline
        #
        property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.good_property_views = []
        self.num_good_property_views = 3
        for i in range(self.num_good_property_views):
            pv = property_view_factory.get_property_view(
                # fields required for analysis
                latitude=39.76550841416409,
                longitude=-104.97855661401148
            )
            # TODO: remove these lines saving the state once fixed, see issue #2493
            PropertyState.objects.get(id=pv.state.id).save()
            pv.refresh_from_db()
            self.good_property_views.append(pv)

        self.analysis_b = (
            FakeAnalysisFactory(organization=self.org, user=self.user)
            .get_analysis(
                name='Good Analysis',
                service=Analysis.BSYNCR
            )
        )

        self.good_meters = []
        for i in range(self.num_good_property_views):
            self.good_meters.append(
                Meter.objects.create(
                    property=self.good_property_views[i].property,
                    source=Meter.PORTFOLIO_MANAGER,
                    source_id="Source ID",
                    type=Meter.ELECTRICITY_GRID,
                )
            )
            tz_obj = timezone(TIME_ZONE)
            for j in range(1, 13):
                MeterReading.objects.create(
                    meter=self.good_meters[i],
                    start_time=make_aware(datetime(2019, j, 1, 0, 0, 0), timezone=tz_obj),
                    end_time=make_aware(datetime(2019, j, 28, 0, 0, 0), timezone=tz_obj),
                    reading=12345,
                    source_unit='kWh',
                    conversion_factor=1.00
                )

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

    def test_pipeline_is_successful_when_properly_setup(self):
        # Act
        pipeline = BsyncrPipeline(self.analysis_b.id)
        pipeline.prepare_analysis([pv.id for pv in self.good_property_views])

        # Assert
        self.analysis_b.refresh_from_db()
        self.assertEqual(Analysis.READY, self.analysis_b.status)

        # check an input file was created for each property
        input_files = AnalysisInputFile.objects.filter(analysis=self.analysis_b)
        self.assertEqual(len(self.good_property_views), input_files.count())

        # verify there were no messages
        messages = AnalysisMessage.objects.filter(
            Q(analysis=self.analysis_b) | Q(analysis_property_view__analysis_id=self.analysis_b)
        )
        self.assertEqual(0, messages.count())

    def test_pipeline_creates_message_for_view_when_no_meter(self):
        # Setup
        # unlink a meter from its property to make the property view Bad
        target_meter = self.good_meters[0]
        original_meter_property_id = target_meter.property.id
        target_meter.property = None
        target_meter.save()

        # Act
        pipeline = BsyncrPipeline(self.analysis_b.id)
        pipeline.prepare_analysis([pv.id for pv in self.good_property_views])

        # Assert
        self.analysis_b.refresh_from_db()
        self.assertEqual(Analysis.READY, self.analysis_b.status)

        # verify a message was linked to the Bad analysis property view
        analysis_property_view = AnalysisPropertyView.objects.get(
            analysis=self.analysis_b,
            property=original_meter_property_id,
        )
        messages = AnalysisMessage.objects.filter(analysis_property_view=analysis_property_view)
        self.assertEqual(1, messages.count())
        self.assertTrue('Property has no linked electricity meters with 12 or more readings' in messages[0].user_message)

    def test_pipeline_fails_when_it_fails_to_make_at_least_one_input_file(self):
        # Setup
        # unlink _all_ meters to the properties, making them all Bad
        for meter in self.good_meters:
            meter.property = None
            meter.save()

        # Act
        pipeline = BsyncrPipeline(self.analysis_b.id)
        property_view_ids = [pv.id for pv in self.good_property_views]

        # it should raise an exception b/c no input files were created
        with self.assertRaises(AnalysisPipelineException):
            pipeline.prepare_analysis(property_view_ids)

        # Assert
        self.analysis_b.refresh_from_db()
        self.assertEqual(Analysis.FAILED, self.analysis_b.status)

        # there should be a message for every property, saying it's Bad
        analysis_property_view_ids = AnalysisPropertyView.objects.filter(
            analysis=self.analysis_b,
        ).values_list('id', flat=True)
        messages = AnalysisMessage.objects.filter(
            analysis_property_view_id__in=analysis_property_view_ids
        )
        self.assertEqual(len(self.good_property_views), messages.count())

        # there should also be a message at analysis level saying things are Bad
        # because no input files were created
        analysis_message = AnalysisMessage.objects.get(
            analysis=self.analysis_b,
            analysis_property_view=None,
        )
        self.assertTrue('No files were able to be prepared for the analysis', analysis_message.user_message)
