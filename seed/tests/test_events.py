# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

import base64

from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import AnalysisEvent, ATEvent, BuildingFile, NoteEvent
from seed.test_helpers.fake import (
    FakeAnalysisFactory,
    FakeCycleFactory,
    FakeNoteFactory,
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

        self.note_factory = FakeNoteFactory(organization=self.org, user=self.user)
        self.note = self.note_factory.get_note()

    def test_get_all_notes(self):
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

        note_event = NoteEvent.objects.create(
            property=self.property,
            cycle=self.cycle,
            note=self.note
        )
        note_event.save()

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
            'end': 3,
            'has_next': False,
            'has_previous': False,
            'num_pages': 1,
            'page': 1,
            'start': 1,
            'total': 3,
        }, response.json()["pagination"])
        self.assertEqual(
            {
                "created",
                "cycle",
                "cycle_end_date",
                "event_type",
                "id",
                "modified",
                "note",
                "property",
                "user_id"
            },
            set(response.json()["data"][0].keys())
        )
        self.assertEqual(
            {
                "analysis",
                "cycle",
                "cycle_end_date",
                "created",
                "event_type",
                "id",
                "modified",
                "property",
                "user_id"
            },
            set(response.json()["data"][1].keys())
        )
        self.assertEqual(
            {
                "audit_date",
                "building_file",
                "created",
                "cycle_end_date",
                "cycle",
                "event_type",
                "id",
                "modified",
                "property",
                "scenarios"
            },
            set(response.json()["data"][2].keys())
        )
