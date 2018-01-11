# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import json

from django.core.urlresolvers import reverse
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.test_helpers.fake import (
    FakePropertyViewFactory,
    FakeNoteFactory,
)


class NoteViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        # Fake Factories
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.note_factory = FakeNoteFactory(organization=self.org)

        self.client.login(**user_details)

        # create a property view with some notes
        self.pv = self.property_view_factory.get_property_view(organization=self.org)
        self.note1 = self.note_factory.get_note()
        self.note2 = self.note_factory.get_log_note()

        self.pv.property.notes.add(self.note1)
        self.pv.property.notes.add(self.note2)
        self.pv.property.save()

    def test_get_notes(self):
        url = reverse('api:v2:notes-list')  # + '?organization_id={}'.format(self.org.pk)
        response = self.client.get(url)
        result = json.loads(response.content)
        results = result['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['note_type'], 'Log')

        # most recent log is displayed first
        expected_log_data = {
            u'property_state': [
                {
                    u'field': u'address_line_1',
                    u'previous_value': u'123 Main Street',
                    u'new_value': u'742 Evergreen Terrace'
                }
            ]
        }
        self.assertEqual(results[0]['log_data'], expected_log_data)
        self.assertEqual(results[1]['note_type'], 'Note')
