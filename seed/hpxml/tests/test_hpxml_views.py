# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.models import (
    PropertyView,
    StatusLabel,
)
from seed.test_helpers.fake import (
    FakeCycleFactory, FakeColumnFactory,
    FakePropertyFactory, FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class InventoryViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.status_label = StatusLabel.objects.create(
            name='test', super_organization=self.org
        )

        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org,
                                              user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone())
        )

        self.client.login(**user_details)

    def test_get_hpxml(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        pv = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )

        # go to hpxml endpoint
        params = {
            'organization_id': self.org.pk
        }
        url = reverse('api:v3:properties-hpxml', args=[pv.id])
        response = self.client.get(url, params)
        self.assertIn('<GrossFloorArea>%s.0</GrossFloorArea>' % state.gross_floor_area,
                      response.content.decode('utf-8'))
