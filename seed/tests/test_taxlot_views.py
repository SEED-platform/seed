# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from datetime import datetime

from django.core.urlresolvers import reverse
from django.utils.timezone import get_current_timezone

from seed.landing.models import SEEDUser as User
from seed.models import (
    TaxLot,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class TaxLotUnmergeViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.cycle = cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.client.login(**user_details)

        self.state_1 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_1 = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=self.taxlot_1, cycle=self.cycle, state=self.state_1
        )

        self.state_2 = self.taxlot_state_factory.get_taxlot_state()
        self.taxlot_2 = self.taxlot_factory.get_taxlot()
        TaxLotView.objects.create(
            taxlot=self.taxlot_2, cycle=self.cycle, state=self.state_2
        )

        # Merge the taxlots
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [self.state_2.pk, self.state_1.pk]  # priority given to state_1
        })
        self.client.post(url, post_params, content_type='application/json')

    def test_unmerging_assigns_new_canonical_records_to_each_resulting_records(self):
        # Capture old taxlot_ids
        view = TaxLotView.objects.first()  # There's only one TaxLotView
        old_taxlot_ids = [
            view.taxlot_id,
            self.taxlot_1.id,
            self.taxlot_2.id,
        ]

        # Unmerge the taxlots
        url = reverse('api:v2:taxlots-unmerge', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(url, content_type='application/json')

        self.assertFalse(TaxLotView.objects.filter(taxlot_id__in=old_taxlot_ids).exists())
        self.assertFalse(TaxLot.objects.filter(pk__in=old_taxlot_ids).exists())
