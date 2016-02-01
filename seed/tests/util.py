# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
#
## Utilities for testing SEED modules.
###

import json

from seed.models import (
    BuildingSnapshot,
    CanonicalBuilding,
    Column,
    ColumnMapping,
    set_initial_sources,
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


def make_fake_snapshot(import_file, init_data, bs_type, is_canon=False, org=None):
    """For making fake mapped BuildingSnapshots to test matching against."""
    snapshot = BuildingSnapshot.objects.create(**init_data)
    snapshot.import_file = import_file
    snapshot.super_organization = org
    if import_file is None:
        snapshot.import_record = None
    else:
        snapshot.import_record = import_file.import_record
    snapshot.source_type = bs_type
    set_initial_sources(snapshot)
    snapshot.save()
    if is_canon:
        canonical_building = CanonicalBuilding.objects.create(
            canonical_snapshot=snapshot
        )
        snapshot.canonical_building = canonical_building
        snapshot.save()

    return snapshot


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
