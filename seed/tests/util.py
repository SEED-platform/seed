# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import date
from typing import Any, Dict

from django.test import TestCase

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, Organization, OrganizationUser
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_IMPORT,
    SEED_DATA_SOURCES,
    Column,
    ColumnMapping,
    Cycle,
    DataLogger,
    DerivedColumn,
    GreenAssessment,
    GreenAssessmentProperty,
    GreenAssessmentURL,
    Meter,
    Note,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    Scenario,
    StatusLabel,
    TaxLot,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    TaxLotView,
)
from seed.models.data_quality import DataQualityCheck
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakeNoteFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory,
)
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

        # Delete all the meters and sensors, but they should have already been removed
        Meter.objects.all().delete()
        DataLogger.objects.all().delete()

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


class AccessLevelBaseTestCase(TestCase):
    """Base Test Case Class to handle Access Levels
    Creates a root owner user, a root member user,
    and a child member user
    Useful for testing "setup" API endpoints
    as well as "data" endpoints
    Provides methods for logging in as different
    users
    Sets up the factories
    """

    def setUp(self):
        """SUPERUSER"""
        self.superuser_details = {
            'username': 'test_superuser@demo.com',
            'password': 'test_pass',
            'email': 'test_superuser@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.superuser = User.objects.create_superuser(**self.superuser_details)
        self.org, _, _ = create_organization(self.superuser, 'test-organization-a')
        # add ALI to org (2 levels)
        self.org.access_level_names = ['root', 'child']
        self.root_level_instance = self.org.root
        self.child_level_instance = self.org.add_new_access_level_instance(self.org.root.id, 'child')

        # default login as superuser/org owner
        self.client.login(**self.superuser_details)

        """ ROOT-LEVEL OWNER USER """
        self.root_owner_user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Jane',
            'last_name': 'Energy',
        }
        self.root_owner_user = User.objects.create_user(**self.root_owner_user_details)
        self.org.add_member(self.root_owner_user, self.org.root.id, ROLE_OWNER)
        self.org.save()

        """ ROOT-LEVEL MEMBER USER """
        self.root_member_user_details = {
            'username': 'root_member@demo.com',
            'password': 'test_pass',
        }
        self.root_member_user = User.objects.create_user(**self.root_member_user_details)
        self.org.add_member(self.root_member_user, self.org.root.id, ROLE_MEMBER)
        self.org.save()

        """ CHILD-LEVEL MEMBER USER """
        self.child_member_user_details = {
            'username': 'child_member@demo.com',
            'password': 'test_pass',
        }
        self.child_member_user = User.objects.create_user(**self.child_member_user_details)
        # add user to org
        self.org.add_member(self.child_member_user, self.child_level_instance.pk, ROLE_MEMBER)
        self.org.save()

        # setup factories
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_factory = FakeTaxLotFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)
        self.note_factory = FakeNoteFactory(organization=self.org, user=self.root_owner_user)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def login_as_root_owner(self):
        """Login to client as Root-Level owner user"""
        self.client.login(**self.root_owner_user_details)

    def login_as_root_member(self):
        """Login to client as Root-Level member user"""
        self.client.login(**self.root_member_user_details)

    def login_as_child_member(self):
        """Login to client as Child-Level member user"""
        self.client.login(**self.child_member_user_details)


class DataMappingBaseTestCase(DeleteModelsTestCase):
    """Base Test Case Class to handle data import"""

    def set_up(self, import_file_source_type, user_name='test_user@demo.com', user_password='test_pass'):
        # default_values
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        if not User.objects.filter(username=user_name).exists():
            user = User.objects.create_user(user_name, password=user_password)
        else:
            user = User.objects.get(username=user_name)

        org, _, _ = create_organization(user, 'test-organization-a')

        cycle, _ = Cycle.objects.get_or_create(
            name='Test Hack Cycle 2015',
            organization=org,
            start=date(2015, 1, 1),
            end=date(2015, 12, 31),
        )

        import_record, import_file = self.create_import_file(
            user,
            org,
            cycle,
            import_file_source_type,
            import_file_data_state,
        )

        return user, org, import_file, import_record, cycle

    def create_import_file(self, user, org, cycle, source_type=ASSESSED_RAW, data_state=DATA_STATE_IMPORT):
        import_record = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org, access_level_instance=org.root
        )
        import_file = ImportFile.objects.create(import_record=import_record, cycle=cycle)
        import_file.source_type = SEED_DATA_SOURCES[source_type][1]
        import_file.data_state = data_state
        import_file.save()

        return import_record, import_file


class FakeRequest:
    """A simple request stub."""

    __name__ = 'FakeRequest'
    META = {'REMOTE_ADDR': '127.0.0.1'}
    path = 'fake_login_path'
    body = None
    GET: Dict[str, Any] = {}
    POST: Dict[str, Any] = {}

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


class FakeClient:
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
    def assertDictContainsSubset(self, subset, dictionary):  # noqa: N802
        """Checks whether dictionary is a superset of subset

        This is a necessary polyfill b/c assertDictContainsSubset was deprecated
        and I believe it's much more readable compared to the implementation below
        """
        # source: https://stackoverflow.com/a/59777678
        # Note that this only works in Python >= 3.9
        self.assertEqual(dictionary, dictionary | subset)
