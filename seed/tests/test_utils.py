# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed.utils.generic import split_model_fields
from seed.utils.time import convert_datestr
import pytz
from datetime import datetime
from django.utils.timezone import make_aware


class DummyClass(object):
    "A simple class that has two fields"
    field_one = "field_one"
    field_two = "field_two"


class TestGenericUtils(TestCase):

    def test_split_model_fields(self):
        """
        Tests splitting a list of field names based on what fields an
        object has.
        """
        f1 = 'field_one'
        f2 = 'field_two'
        f3 = 'no_field_three'
        f4 = 'no_field_four'

        obj = DummyClass()

        fields_to_split = [f1, f2, f3, f4]
        obj_fields, non_obj_fields = split_model_fields(obj, fields_to_split)
        self.assertEqual(obj_fields, [f1, f2])
        self.assertEqual(non_obj_fields, [f3, f4])

        fields_to_split = [f1]
        obj_fields, non_obj_fields = split_model_fields(obj, fields_to_split)
        self.assertEqual(obj_fields, [f1])
        self.assertEqual(non_obj_fields, [])

        fields_to_split = [f4]
        obj_fields, non_obj_fields = split_model_fields(obj, fields_to_split)
        self.assertEqual(obj_fields, [])
        self.assertEqual(non_obj_fields, [f4])


class TestTime(TestCase):

    def test_date_conversion(self):
        dt = datetime(2016, 0o7, 15, 12, 30)
        self.assertEqual(convert_datestr(dt.strftime("%Y-%m-%d %H:%M")), dt)

        # with TZ info
        dt = make_aware(datetime(2016, 0o7, 15, 12, 30), pytz.UTC)
        self.assertEqual(convert_datestr(dt.strftime("%Y-%m-%d %H:%M"), True), dt)
