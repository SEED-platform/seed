# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    Column,
    ColumnListSetting,
)


class TestColumnListSettings(TestCase):
    """Test the clean methods on BuildingSnapshotModel."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org = Organization.objects.create()
        OrganizationUser.objects.create(
            user=self.fake_user,
            organization=self.fake_org
        )

    def test_adding_columns(self):
        """These are simple tests which really only test the m2m part. If these don't work, then django has
        some issues."""
        col1 = Column.objects.create(
            column_name=u'New Column',
            table_name=u'PropertyState',
            organization=self.fake_org
        )
        col2 = Column.objects.create(
            column_name=u'Second Column',
            table_name=u'PropertyState',
            organization=self.fake_org
        )

        new_list_setting = ColumnListSetting.objects.create(name='example list setting')
        new_list_setting.columns.add(col1)
        new_list_setting.columns.add(col2)

        self.assertEqual(new_list_setting.columns.count(), 2)
        self.assertEqual(new_list_setting.columns.first().column_name, 'New Column')

        new_list_setting.columns.remove(col1)
        self.assertEqual(new_list_setting.columns.count(), 1)
        self.assertEqual(new_list_setting.columns.first().column_name, 'Second Column')
