# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django.test import TestCase

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    Column,
    ColumnMapping,
    Cycle,
    Property,
    PropertyState,
    PropertyView,
    PropertyAuditLog,
    StatusLabel,
    TaxLotAuditLog,
    TaxLotState,
    TaxLot,
    TaxLotView,
    TaxLotProperty,
)
from seed.models.data_quality import DataQualityCheck


class DeleteModelsTestCase(TestCase):
    def _delete_models(self):
        # Order matters here
        Column.objects.all().delete()
        ColumnMapping.objects.all().delete()
        DataQualityCheck.objects.all().delete()
        ImportFile.objects.all().delete()
        ImportRecord.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        PropertyAuditLog.objects.all().delete()
        StatusLabel.objects.all().delete()
        TaxLot.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()
        TaxLotAuditLog.objects.all().delete()
        TaxLotProperty.objects.all().delete()

        # Now delete the cycle after all the states and views have been removed
        Cycle.objects.all().delete()

        # Delete users last
        User.objects.all().delete()
        Organization.objects.all().delete()
        OrganizationUser.objects.all().delete()

    def setUp(self):
        self._delete_models()

    def tearDown(self):
        self._delete_models()


class FakeRequest(object):
    """A simple request stub."""
    __name__ = 'FakeRequest'
    META = {'REMOTE_ADDR': '127.0.0.1'}
    path = 'fake_login_path'
    body = None
    GET = POST = {}

    def __init__(self, data=None, headers=None, user=None, method='POST', **kwargs):
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
