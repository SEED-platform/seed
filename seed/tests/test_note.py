# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author nicholas.long@nrel.gov
"""
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakeNoteFactory, FakePropertyViewFactory
from seed.utils.organizations import create_organization


class TestNotes(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('test_user@demo.com', 'test_user@demo.com', 'test_pass')
        self.org, _, _ = create_organization(self.user)

        # Fake Factories
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.note_factory = FakeNoteFactory(organization=self.org, user=self.user)

    def test_note_assignments(self):
        """Make sure that properties can contain notes"""
        pv = self.property_view_factory.get_property_view(organization=self.org)
        note1 = self.note_factory.get_note()
        note2 = self.note_factory.get_note()

        pv.notes.add(note1)
        pv.notes.add(note2)

        self.assertTrue(pv)
        self.assertIn(note1, pv.notes.all())
        self.assertIn(note2, pv.notes.all())
