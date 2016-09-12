# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
#
# Utilities for testing SEED modules.
###

import datetime
import json

from seed.models import (
    PropertyState,
    Column,
    ColumnMapping,
    set_initial_sources,
    Cycle,
)


def make_fake_mappings(mappings, org):
    """Takes a dict and saves a ColumnMapping object for each key"""
    for mapped, raw in mappings.items():
        if not isinstance(raw, list):
            raw = [raw]

        columns_raw = []
        for col in raw:
            column_raw, _ = Column.objects.get_or_create(
                column_name=col, organization=org
            )
            columns_raw.append(column_raw)

        column_mapped, _ = Column.objects.get_or_create(
            column_name=mapped, organization=org
        )

        column_mapping = ColumnMapping.objects.create(
            super_organization=org
        )
        # For some reason the splat operator was causing problems here, just add them one at a time
        for col in columns_raw:
            column_mapping.column_raw.add(col)
        column_mapping.column_mapped.add(column_mapped)


def make_fake_property(import_file, init_data, bs_type, is_canon=False, org=None):
    """For making fake mapped PropertyState to test matching against."""

    if not org:
        raise "no org"

    ps = PropertyState.objects.create(**init_data)
    ps.import_file = import_file
    ps.organization = org
    if import_file is None:
        ps.import_record = None
    else:
        ps.import_record = import_file.import_record
        ps.source_type = bs_type

    # TODO: can we remove set_initial sources? Seems like this is invalid in the new data model world.
    set_initial_sources(ps)
    ps.save()

    # The idea of canon is no longer applicable. The linked property state
    # in the PropertyView is now canon
    if is_canon:
        # need to create a cycle and add it to the PropertyView table
        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Cycle',
            organization=org,
            start=datetime.datetime(2015, 1, 1),
            end=datetime.datetime(2015, 12, 31),
        )

        ps.promote(cycle)

    return ps


class FakeRequest(object):
    """A simple request stub."""
    __name__ = 'FakeRequest'
    META = {'REMOTE_ADDR': '127.0.0.1'}
    path = 'fake_login_path'
    body = None
    GET = POST = {}

    def __init__(
            self, data=None, headers=None, user=None, method='POST', **kwargs
    ):
        if 'body' in kwargs:
            self.body = kwargs['body']
        if data is None:
            data = {}

        setattr(self, method, data)
        if headers:
            self.META.update(headers)
        if user:
            self.user = user


class FakeClient(object):
    """An extremely light-weight test client."""

    def _gen_req(self, view_func, data, headers, method='POST', **kwargs):
        request = FakeRequest(headers)
        if 'user' in kwargs:
            request.user = kwargs.get('user')
        if callable(view_func):
            setattr(request, method, data)
            request.body = json.dumps(data)
            return view_func(request)

        return request

    def get(self, view_func, data, headers=None, **kwargs):
        return self._gen_req(view_func, data, headers, method='GET', **kwargs)

    def post(self, view_func, data, headers=None, **kwargs):
        return self._gen_req(view_func, data, headers, **kwargs)
