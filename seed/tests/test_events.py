# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import base64

from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import AnalysisEvent, ATEvent, BuildingFile
from seed.test_helpers.fake import (
    FakeAnalysisFactory,
    FakeCycleFactory,
    FakePropertyFactory
)
from seed.utils.organizations import create_organization


class EventTests(TransactionTestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',  # the username needs to be in the form of an email.
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jaqen',
            'last_name': 'H\'ghar'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org, _, _ = create_organization(self.user)
        self.other_org, _, _ = create_organization(self.user)

        auth_string = base64.urlsafe_b64encode(bytes(
            '{}:{}'.format(self.user.username, self.user.api_key), 'utf-8'
        ))
        self.auth_string = 'Basic {}'.format(auth_string.decode('utf-8'))
        self.headers = {'Authorization': self.auth_string}

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property = self.property_factory.get_property()

        self.analysis = (
            FakeAnalysisFactory(organization=self.org, user=self.user)
            .get_analysis()
        )

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = cycle_factory.get_cycle(name="Cycle A")

    def test_get_all_filter_group(self):
        # Setup
        at_event = ATEvent.objects.create(
            property=self.property,
            cycle=self.cycle,
            building_file=BuildingFile.objects.create()
        )
        at_event.save()

        analysis_event = AnalysisEvent.objects.create(
            property=self.property,
            cycle=self.cycle,
            analysis=self.analysis
        )
        analysis_event.save()

        # wrong property, should not be included
        analysis_event = AnalysisEvent.objects.create(
            property=self.property_factory.get_property(),
            cycle=self.cycle,
            analysis=self.analysis
        )
        analysis_event.save()

        # Action
        response = self.client.get(
            reverse('api:v3:property-events-list', kwargs={'property_pk': self.property.id}),
            **self.headers
        )

        # Assertion
        self.assertEqual(200, response.status_code)
        self.assertEqual('success', response.json()["status"])
        self.assertDictEqual({
            'end': 2,
            'has_next': False,
            'has_previous': False,
            'num_pages': 1,
            'page': 1,
            'start': 1,
            'total': 2
        }, response.json()["pagination"])
        self.assertEqual(
            {
                "building_file",
                "created",
                "id",
                "modified",
                "property",
                "cycle",
            },
            set(response.json()["data"][0].keys())
        )
        self.assertEqual(
            {
                "analysis",
                "created",
                "id",
                "modified",
                "property",
                "cycle",
            },
            set(response.json()["data"][1].keys())
        )
