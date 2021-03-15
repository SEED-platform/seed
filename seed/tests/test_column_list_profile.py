# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
)
from seed.utils.organizations import create_organization
from past.builtins import basestring


class TestColumnListProfile(TestCase):

    def setUp(self):
        self.fake_user = User.objects.create(username='test')
        self.fake_org, _, _ = create_organization(self.fake_user)

    def test_adding_columns(self):
        """These are simple tests which really only test the m2m part. If these don't work,
        then django has some issues."""
        col1 = Column.objects.create(
            column_name='New Column',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )
        col2 = Column.objects.create(
            column_name='Second Column',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )

        new_list_profile = ColumnListProfile.objects.create(name='example list profile')
        ColumnListProfileColumn.objects.create(column=col1, column_list_profile=new_list_profile, order=1, pinned=False)
        ColumnListProfileColumn.objects.create(column=col2, column_list_profile=new_list_profile, order=2, pinned=True)

        self.assertEqual(new_list_profile.columns.count(), 2)
        self.assertEqual(new_list_profile.columns.first().column_name, 'New Column')

        ColumnListProfileColumn.objects.filter(column=col1, column_list_profile=new_list_profile).delete()
        self.assertEqual(new_list_profile.columns.count(), 1)
        self.assertEqual(new_list_profile.columnlistprofilecolumn_set.count(), 1)
        self.assertEqual(new_list_profile.columnlistprofilecolumn_set.first().column.column_name, 'Second Column')

    def test_returning_columns_no_profile(self):
        # do not set up a profile and return the columns, should be all columns
        ids, name_mappings, objs = ColumnListProfile.return_columns(self.fake_org, None)

        # not the most robust tests, but they are least check for non-zero results
        self.assertIsInstance(ids[0], int)
        self.assertIsInstance(list(name_mappings.keys())[0], basestring)
        self.assertIsInstance(list(name_mappings.values())[0], basestring)

    def test_returning_columns_with_profile(self):
        col1 = Column.objects.create(
            column_name='New Column',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )
        col2 = Column.objects.create(
            column_name='Second Column',
            table_name='PropertyState',
            organization=self.fake_org,
            is_extra_data=True,
        )

        new_list_profile = ColumnListProfile.objects.create(name='example list profile')
        ColumnListProfileColumn.objects.create(column=col1, column_list_profile=new_list_profile, order=1, pinned=False)
        ColumnListProfileColumn.objects.create(column=col2, column_list_profile=new_list_profile, order=2, pinned=True)

        # do not set up a profile and return the columns, should be all columns
        ids, name_mappings, objs = ColumnListProfile.return_columns(self.fake_org, new_list_profile.id)

        # not the most robust tests, but they are least check for non-zero results
        self.assertIsInstance(ids[0], int)
        self.assertIsInstance(list(name_mappings.keys())[0], basestring)
        self.assertIsInstance(list(name_mappings.values())[0], basestring)
