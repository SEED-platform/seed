# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    ColumnListSetting,
    ColumnListSettingColumn,
)
from seed.utils.organizations import create_organization


class TestColumnListSettings(TestCase):
    """Test the clean methods on BuildingSnapshotModel."""

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _, _ = create_organization(self.fake_user)

    def test_adding_columns(self):
        """These are simple tests which really only test the m2m part. If these don't work, then django has
        some issues."""
        col1 = Column.objects.create(
            column_name=u'New Column',
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )
        col2 = Column.objects.create(
            column_name=u'Second Column',
            table_name=u'PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )

        new_list_setting = ColumnListSetting.objects.create(name='example list setting')
        ColumnListSettingColumn.objects.create(column=col1, column_list_setting=new_list_setting, order=1, pinned=False)
        ColumnListSettingColumn.objects.create(column=col2, column_list_setting=new_list_setting, order=2, pinned=True)

        self.assertEqual(new_list_setting.columns.count(), 2)
        self.assertEqual(new_list_setting.columns.first().column_name, 'New Column')

        ColumnListSettingColumn.objects.filter(column=col1, column_list_setting=new_list_setting).delete()
        self.assertEqual(new_list_setting.columns.count(), 1)
        self.assertEqual(new_list_setting.columnlistsettingcolumn_set.count(), 1)
        self.assertEqual(new_list_setting.columnlistsettingcolumn_set.first().column.column_name, 'Second Column')
