# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import datetime
import json

from django.test import TestCase
from django.utils import timezone

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    Column,
    ColumnMapping,
    Cycle,
    DerivedColumn,
    Property,
    PropertyState,
    PropertyView,
    PropertyAuditLog,
    Note,
    Scenario,
    StatusLabel,
    TaxLotAuditLog,
    TaxLotState,
    TaxLot,
    TaxLotView,
    TaxLotProperty,
    GreenAssessment,
    GreenAssessmentProperty,
    GreenAssessmentURL,
)
from seed.models import (
    DATA_STATE_IMPORT,
    ASSESSED_RAW,
)
from seed.models.data_quality import DataQualityCheck
from seed.utils.organizations import create_organization


class DeleteModelsTestCase(TestCase):
    def _delete_models(self):
        # Order matters here
        DerivedColumn.objects.all().delete()
        Column.objects.all().delete()
        ColumnMapping.objects.all().delete()
        DataQualityCheck.objects.all().delete()
        ImportFile.objects.all().delete()
        ImportRecord.objects.all().delete()
        Property.objects.all().delete()
        PropertyState.objects.all().delete()
        PropertyView.objects.all().delete()
        PropertyAuditLog.objects.all().delete()
        Note.objects.all().delete()
        Scenario.objects.all().delete()
        StatusLabel.objects.all().delete()
        TaxLot.objects.all().delete()
        TaxLotState.objects.all().delete()
        TaxLotView.objects.all().delete()
        TaxLotAuditLog.objects.all().delete()
        TaxLotProperty.objects.all().delete()
        GreenAssessmentURL.objects.all().delete()
        GreenAssessmentProperty.objects.all().delete()
        GreenAssessment.objects.all().delete()

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


class DataMappingBaseTestCase(DeleteModelsTestCase):
    """Base Test Case Class to handle data import"""

    def set_up(self, import_file_source_type):
        # default_values
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        if not User.objects.filter(username='test_user@demo.com').exists():
            user = User.objects.create_user('test_user@demo.com', password='test_pass')
        else:
            user = User.objects.get(username='test_user@demo.com')

        org, _, _ = create_organization(user, "test-organization-a")

        cycle, _ = Cycle.objects.get_or_create(
            name='Test Hack Cycle 2015',
            organization=org,
            start=datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2015, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        import_record, import_file = self.create_import_file(
            user, org, cycle, import_file_source_type, import_file_data_state
        )

        return user, org, import_file, import_record, cycle

    def create_import_file(self, user, org, cycle, source_type=ASSESSED_RAW,
                           data_state=DATA_STATE_IMPORT):
        import_record = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file = ImportFile.objects.create(import_record=import_record, cycle=cycle)
        import_file.source_type = source_type
        import_file.data_state = data_state
        import_file.save()

        return import_record, import_file


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


class AssertDictSubsetMixin:
    def assertDictContainsSubset(self, subset, dictionary):
        """Checks whether dictionary is a superset of subset

        This is a necessary polyfill b/c assertDictContainsSubset was deprecated
        and I believe it's much more readable compared to the implementation below
        """
        # source: https://stackoverflow.com/a/59777678
        self.assertEqual(dictionary, dictionary | subset)
