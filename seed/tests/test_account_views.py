# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import date

from django.test import TestCase
from django.urls import NoReverseMatch, reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.exceptions import InsufficientPermission
from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser
)
from seed.models.columns import Column
from seed.models.cycles import Cycle
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.tests.util import FakeRequest
from seed.utils.organizations import create_organization
from seed.utils.users import get_js_role, get_role_from_js
from seed.views.main import _get_default_org
from seed.views.v3.organizations import _dict_org


class AccountsViewTests(TestCase):
    """
    Tests of the SEED accounts
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user, "my org")
        self.cycle = Cycle.objects.filter(organization=self.org).first()
        self.client.login(**user_details)
        self.fake_request = FakeRequest(user=self.user)
        self.maxDiff = None

        year = date.today().year - 1
        self.cal_year_name = "{} Calendar Year".format(year)

    def test_dict_org(self):
        """_dict_org turns our org structure into a json payload."""

        expected_single_org_payload = {
            'name': 'my org',
            'org_id': self.org.pk,
            'id': self.org.pk,
            'number_of_users': 1,
            'user_is_owner': True,
            'user_role': 'owner',
            'owners': [{
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'email': 'test_user@demo.com',
                'id': self.user.pk
            }],
            'sub_orgs': [],
            'is_parent': True,
            'parent_id': self.org.pk,
            'display_units_eui': 'kBtu/ft**2/year',
            'display_units_area': 'ft**2',
            'display_decimal_places': 2,
            'cycles': [{
                'name': self.cal_year_name,
                'cycle_id': self.cycle.pk,
                'num_properties': 0,
                'num_taxlots': 0
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
            'mapquest_api_key': '',
            'geocoding_enabled': True,
            'better_analysis_api_key': '',
            'better_host_url': 'https://better-lbnl-staging.herokuapp.com',
            'property_display_field': 'address_line_1',
            'taxlot_display_field': 'address_line_1',
            'display_meter_units': Organization._default_display_meter_units,
            'thermal_conversion_assumption': Organization.US,
            'comstock_enabled': False,
            'new_user_email_from': 'info@seed-platform.org',
            'new_user_email_subject': 'New SEED account',
            'new_user_email_content': 'Hello {{first_name}},\nYou are receiving this e-mail because you have been registered for a SEED account.\nSEED is easy, flexible, and cost effective software designed to help organizations clean, manage and share information about large portfolios of buildings. SEED is a free, open source web application that you can use privately.  While SEED was originally designed to help cities and States implement benchmarking programs for public or private buildings, it has the potential to be useful for many other activities by public entities, efficiency programs and private companies.\nPlease go to the following page and setup your account:\n{{sign_up_link}}',
            'new_user_email_signature': 'The SEED Team',
            'at_organization_token': '',
            'audit_template_user': '',
            'audit_template_password': '',
            'at_host_url': 'https://api.labworks.org',
            'salesforce_enabled': False,
            'ubid_threshold': 1
        }

        org_payload = _dict_org(self.fake_request, [self.org])
        self.assertEqual(len(org_payload), 1)
        self.assertDictEqual(org_payload[0], expected_single_org_payload)

        # Now let's make sure that we pick up related buildings correctly.
        for x in range(10):
            ps = PropertyState.objects.create(organization=self.org)
            ps.promote(self.cycle)
            ps.save()

        for x in range(5):
            ts = TaxLotState.objects.create(organization=self.org)
            ts.promote(self.cycle)
            ts.save()

        expected_single_org_payload['cycles'] = [{
            'num_taxlots': 5,
            'num_properties': 10,
            'name': self.cal_year_name,
            'cycle_id': self.cycle.pk
        }]
        self.assertDictEqual(
            _dict_org(self.fake_request, [self.org])[0],
            expected_single_org_payload
        )

    def test_dict_org_w_member_in_parent_and_child(self):
        """What happens when a user has a role in parent and child."""

        new_org, _, _ = create_organization(self.user, "sub")
        new_org.parent_org = self.org
        new_org.save()
        new_cycle = Cycle.objects.filter(organization=new_org).first()

        expected_multiple_org_payload = {
            'name': 'my org',
            'org_id': self.org.pk,
            'id': self.org.pk,
            'number_of_users': 1,
            'user_is_owner': True,
            'user_role': 'owner',
            'owners': [{
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'email': 'test_user@demo.com',
                'id': self.user.pk
            }],
            'sub_orgs': [{
                'name': 'sub',
                'org_id': new_org.pk,
                'id': new_org.pk,
                'number_of_users': 1,
                'user_is_owner': True,
                'user_role': 'owner',
                'owners': [{
                    'first_name': 'Johnny',
                    'last_name': 'Energy',
                    'email': 'test_user@demo.com',
                    'id': self.user.pk
                }],
                'sub_orgs': [],
                'is_parent': False,
                'parent_id': self.org.pk,
                'display_units_eui': 'kBtu/ft**2/year',
                'display_units_area': 'ft**2',
                'display_decimal_places': 2,
                'cycles': [{
                    'name': self.cal_year_name,
                    'cycle_id': new_cycle.pk,
                    'num_properties': 0,
                    'num_taxlots': 0
                }],
                'created': new_org.created.strftime('%Y-%m-%d'),
                'mapquest_api_key': '',
                'geocoding_enabled': True,
                'better_analysis_api_key': '',
                'better_host_url': 'https://better-lbnl-staging.herokuapp.com',
                'property_display_field': 'address_line_1',
                'taxlot_display_field': 'address_line_1',
                'display_meter_units': Organization._default_display_meter_units,
                'thermal_conversion_assumption': Organization.US,
                'comstock_enabled': False,
                'new_user_email_from': 'info@seed-platform.org',
                'new_user_email_subject': 'New SEED account',
                'new_user_email_content': 'Hello {{first_name}},\nYou are receiving this e-mail because you have been registered for a SEED account.\nSEED is easy, flexible, and cost effective software designed to help organizations clean, manage and share information about large portfolios of buildings. SEED is a free, open source web application that you can use privately.  While SEED was originally designed to help cities and States implement benchmarking programs for public or private buildings, it has the potential to be useful for many other activities by public entities, efficiency programs and private companies.\nPlease go to the following page and setup your account:\n{{sign_up_link}}',
                'new_user_email_signature': 'The SEED Team',
                'at_organization_token': '',
                'audit_template_user': '',
                'audit_template_password': '',
                'at_host_url': 'https://api.labworks.org',
                'salesforce_enabled': False,
                'ubid_threshold': 1
            }],
            'is_parent': True,
            'parent_id': self.org.pk,
            'display_units_eui': 'kBtu/ft**2/year',
            'display_units_area': 'ft**2',
            'display_decimal_places': 2,
            'cycles': [{
                'name': self.cal_year_name,
                'cycle_id': self.cycle.pk,
                'num_properties': 0,
                'num_taxlots': 0
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
            'mapquest_api_key': '',
            'geocoding_enabled': True,
            'better_analysis_api_key': '',
            'better_host_url': 'https://better-lbnl-staging.herokuapp.com',
            'property_display_field': 'address_line_1',
            'taxlot_display_field': 'address_line_1',
            'display_meter_units': Organization._default_display_meter_units,
            'thermal_conversion_assumption': Organization.US,
            'comstock_enabled': False,
            'new_user_email_from': 'info@seed-platform.org',
            'new_user_email_subject': 'New SEED account',
            'new_user_email_content': 'Hello {{first_name}},\nYou are receiving this e-mail because you have been registered for a SEED account.\nSEED is easy, flexible, and cost effective software designed to help organizations clean, manage and share information about large portfolios of buildings. SEED is a free, open source web application that you can use privately.  While SEED was originally designed to help cities and States implement benchmarking programs for public or private buildings, it has the potential to be useful for many other activities by public entities, efficiency programs and private companies.\nPlease go to the following page and setup your account:\n{{sign_up_link}}',
            'new_user_email_signature': 'The SEED Team',
            'at_organization_token': '',
            'audit_template_user': '',
            'audit_template_password': '',
            'at_host_url': 'https://api.labworks.org',
            'salesforce_enabled': False,
            'ubid_threshold': 1
        }

        org_payload = _dict_org(self.fake_request, Organization.objects.all())

        self.assertEqual(len(org_payload), 2)
        self.assertDictEqual(org_payload[0], expected_multiple_org_payload)

    def test_get_organizations(self):
        """ tests accounts.get_organizations """
        resp = self.client.get(
            reverse_lazy('api:v3:organizations-list'),
            content_type='application/json',
        )
        orgs = json.loads(resp.content)['organizations']
        org = orgs[0]
        self.assertEqual(org['name'], 'my org')
        self.assertEqual(org['number_of_users'], 1)
        self.assertDictEqual(
            org['owners'][0],
            {
                'email': 'test_user@demo.com',
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'id': self.user.pk  # since this could change
            }
        )
        self.assertTrue(org['user_is_owner'])

    def test_get_organization_no_org(self):
        """test for error when no organization_id sent"""
        with self.assertRaises(NoReverseMatch):
            self.client.get(
                reverse_lazy('api:v3:organizations-detail'),
                content_type='application/json',
            )

    def test_get_organization_std_case(self):
        """test normal case"""
        resp = self.client.get(
            reverse_lazy('api:v3:organizations-detail', args=[self.org.id]),
            content_type='application/json',
        )

        org = json.loads(resp.content)['organization']
        self.assertEqual(org['name'], 'my org')
        self.assertEqual(org['number_of_users'], 1)
        self.assertDictEqual(
            org['owners'][0],
            {
                'email': 'test_user@demo.com',
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'id': self.user.pk  # since this could change
            }
        )
        self.assertTrue(org['user_is_owner'])

    def test_get_organization_user_not_owner(self):
        """test for the case where a user does not have access"""
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org, _, _ = create_organization(other_user, "not my org")

        resp = self.client.get(
            reverse_lazy('api:v3:organizations-detail', args=[other_org.id]),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            })

    def test_get_organization_org_doesnt_exist(self):
        """test for the case where a user does not have access"""
        resp = self.client.get(
            reverse_lazy('api:v3:organizations-detail', args=[self.org.id + 100]),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            })

    def test_remove_user_from_org_std(self):
        """test removing a user"""
        # normal case
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[self.org.id, u.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
            })

    def test_cannot_leave_org_empty(self):
        """test removing a user"""
        self.assertEqual(self.org.users.count(), 1)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[self.org.id, self.user.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'an organization must have at least one member'
            })

    def test_cannot_leave_org_with_no_owner(self):
        """test removing a user"""
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_MEMBER)
        self.assertEqual(self.org.users.count(), 2)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[self.org.id, self.user.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            })

    def test_remove_user_from_org_user_DNE(self):
        """DNE = does not exist"""
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[self.org.id, 9999]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'user does not exist'
            })

    def test_remove_user_from_org_org_DNE(self):
        """DNE = does not exist"""
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[9999, u.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            })

    def test_get_js_role(self):
        self.assertEqual(get_js_role(ROLE_OWNER), 'owner')
        self.assertEqual(get_js_role(ROLE_MEMBER), 'member')
        self.assertEqual(get_js_role(ROLE_VIEWER), 'viewer')

    def test_get_role_from_js(self):
        self.assertEqual(get_role_from_js('owner'), ROLE_OWNER)
        self.assertEqual(get_role_from_js('member'), ROLE_MEMBER)
        self.assertEqual(get_role_from_js('viewer'), ROLE_VIEWER)

    def test_update_role(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_VIEWER)

        ou = OrganizationUser.objects.get(
            user_id=u.id, organization_id=self.org.id)
        self.assertEqual(ou.role_level, ROLE_VIEWER)

        resp = self.client.put(
            reverse_lazy("api:v3:user-role", args=[u.id]) + '?organization_id=' + str(
                self.org.id),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'role': 'member'
                }
            ),
            content_type='application/json',
        )
        ou = OrganizationUser.objects.get(
            user_id=u.id, organization_id=self.org.id)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success'
            })
        self.assertEqual(ou.role_level, ROLE_MEMBER)

    def test_allowed_to_update_role_if_not_last_owner(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_OWNER)

        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertEqual(ou.role_level, ROLE_OWNER)

        resp = self.client.put(
            reverse_lazy("api:v3:user-role",
                         args=[self.user.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps(
                {
                    'role': 'member',
                    'organization_id': str(self.org.id)
                }
            ),
            content_type='application/json',
        )
        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success'
            })
        self.assertEqual(ou.role_level, ROLE_MEMBER)

    def test_cannot_update_role_if_last_owner(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_MEMBER)

        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertEqual(ou.role_level, ROLE_OWNER)

        resp = self.client.put(
            reverse_lazy("api:v3:user-role",
                         args=[self.user.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps(
                {
                    'organization_id': self.org.id,
                    'role': 'owner'
                }
            ),
            content_type='application/json',
        )
        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'an organization must have at least one owner'
            })
        self.assertEqual(ou.role_level, ROLE_OWNER)

    def test_update_role_no_perms(self):
        """ Test trying to change your own role when you are not an owner. """
        ou = OrganizationUser.objects.get(user=self.user,
                                          organization=self.org)
        ou.role_level = ROLE_MEMBER
        ou.save()

        url = reverse_lazy('api:v3:user-role', args=[self.user.id])
        post_data = {'organization_id': self.org.id,
                     'role': 'owner'}
        try:
            self.client.put(
                url,
                data=json.dumps(post_data),
                content_type='application/json'
            )
        except InsufficientPermission:
            # Todo:  currently superperms just raises an exception, rather
            # than returning an HttpResponse.  Update this when that changes.
            pass

        # ensure we did not just become owner
        self.assertFalse(self.org.is_owner(self.user))

    def test_bad_save_request(self):
        """ A malformed request should return error-containing json. """
        url = reverse_lazy('api:v3:organizations-save-settings', args=[self.org.id])

        res = self.client.put(
            url,
            data={},
            content_type='application/json'
        )
        response = json.loads(res.content)
        # don't really care what the message is
        self.assertEqual(response['status'], 'error')

    def test_query_threshold(self):
        url = reverse_lazy('api:v3:organizations-save-settings', args=[self.org.id])
        post_data = {
            'organization': {
                'query_threshold': 27,
                'name': self.org.name
            }
        }

        self.client.put(
            url,
            data=json.dumps(post_data),
            content_type='application/json'
        )
        # reload org
        org = Organization.objects.get(pk=self.org.pk)
        self.assertEqual(org.query_threshold, 27)

    def test_get_shared_fields_none(self):
        url = reverse_lazy('api:v3:organizations-shared-fields', args=[self.org.pk])
        res = self.client.get(url)
        response = json.loads(res.content)
        self.assertEqual(response, {'status': 'success', 'public_fields': []})

    def test_add_shared_fields(self):
        url = reverse_lazy('api:v3:organizations-save-settings', args=[self.org.pk])

        columns = list(Column.objects.filter(organization=self.org).values('id', 'table_name', 'column_name'))
        ubid_id = [c for c in columns if c['table_name'] == 'PropertyState' and c['column_name'] == 'ubid'][0]['id']
        address_line_1_id = [c for c in columns if c['table_name'] == 'PropertyState'
                             and c['column_name'] == 'address_line_1'][0]['id']

        # There are already several columns in the database due to the create_organization method
        payload = {
            'organization_id': self.org.pk,
            'organization': {
                'owners': self.user.pk,
                'query_threshold': 2,
                'name': self.org.name,
                'public_fields': [
                    {
                        "id": ubid_id,
                        "displayName": "UBID",
                        "name": "ubid",
                        "dataType": "string",
                        "related": False,
                        "sharedFieldType": "Public",
                        "table_name": "PropertyState",
                        "column_name": "ubid",
                        "public_checked": True
                    }, {
                        "id": address_line_1_id,
                        "displayName": "Address Line 1 (Property)",
                        "name": "address_line_1",
                        "dataType": "string",
                        "related": False,
                        "column_name": "address_line_1",
                        "sharedFieldType": "None",
                        "table_name": "PropertyState",
                        "public_checked": True
                    }
                ]
            }
        }

        self.client.put(url, json.dumps(payload), content_type='application/json')

        fields = Column.objects.filter(organization=self.org, shared_field_type=Column.SHARED_PUBLIC).values_list(
            'table_name', 'column_name')

        # fields = self.org.exportable_fields.values_list('name', flat=True)
        self.assertTrue(('PropertyState', 'ubid') in fields)
        self.assertTrue(('PropertyState', 'address_line_1') in fields)
        self.assertEqual(len(fields), 2)

    def test_update_user(self):
        """test for update_user"""
        user_data = {
            'first_name': 'bob',
            'last_name': 'd',
            'email': 'some@hgg.com'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-detail', args=[self.user.pk]),
            json.dumps(user_data),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'api_key': '',
                'email': 'some@hgg.com',
                'first_name': 'bob',
                'last_name': 'd'

            })

    def test_get_user_profile(self):
        """test for get_user_profile"""
        resp = self.client.get(
            reverse_lazy('api:v3:user-detail', args=[self.user.pk]),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'api_key': '',
                'email': 'test_user@demo.com',
                'first_name': 'Johnny',
                'last_name': 'Energy'

            })
        resp = self.client.post(
            reverse_lazy('api:v3:user-generate-api-key', args=[self.user.pk]),
            content_type='application/json',
        )
        resp = self.client.get(
            reverse_lazy('api:v3:user-detail', args=[self.user.pk]),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'api_key': User.objects.get(pk=self.user.pk).api_key,
                'email': 'test_user@demo.com',
                'first_name': 'Johnny',
                'last_name': 'Energy'
            })

    def test_generate_api_key(self):
        """test for generate_api_key
            will pick up user.api_key when it's ready
        """
        resp = self.client.post(
            reverse_lazy('api:v3:user-generate-api-key', args=[self.user.pk]),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        api_key = user.api_key

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'api_key': api_key,
            })

    def test_set_password(self):
        """test for set_password"""
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'new passwordD3',
            'password_2': 'new passwordD3'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.check_password('new passwordD3'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
            })

    def test_set_password_only_put(self):
        """test for set_password only allowing put"""
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'new password',
            'password_2': 'new password'
        }
        resp = self.client.post(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(resp.status_code, 405)
        self.assertEqual(
            json.loads(resp.content),
            {
                'detail': 'Method \"POST\" not allowed.',
            })

        resp = self.client.get(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            password_payload,
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(resp.status_code, 405)
        self.assertEqual(
            json.loads(resp.content),
            {
                'detail': 'Method \"GET\" not allowed.'
            })

    def test_set_password_error_messages(self):
        """test for set_password produces proper messages"""
        # check current password is invalid
        password_payload = {
            'current_password': 'test_pass INVALID',
            'password_1': 'new password',
            'password_2': 'new password'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error', 'message': 'current password is not valid',
            })
        # check passwords don't match
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'new password',
            'password_2': 'non matching password'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error', 'message': 'entered password do not match',
            })

    def test_set_password_meets_password_reqs(self):
        """test for set_password meets password reqs"""
        # check new password is less than 8 chars
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'new1234',
            'password_2': 'new1234'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'This password is too short. It must contain at least 8 characters.',
            })
        # check new password is has uppercase letters
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'newnewnew',
            'password_2': 'newnewnew'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': (
                    'This password must contain at least 1 uppercase characters.'
                ),
            })
        # check new password is has lowercase letters
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'NEWNEWNEW',
            'password_2': 'NEWNEWNEW'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': (
                    'This password must contain at least 1 lowercase characters.'
                ),
            })
        # check new password is has alphanumeric letters
        password_payload = {
            'current_password': 'test_pass',
            'password_1': 'nNEWNEWNEW',
            'password_2': 'nNEWNEWNEW'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': (
                    'This password must contain at least 1 numeric characters.'
                ),
            })
        password_payload = {
            'current_password': 'test_pass',
            'password_1': '12345678',
            'password_2': '12345678'
        }
        resp = self.client.put(
            reverse_lazy('api:v3:user-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'This password is too common.',
            })

    def test_create_sub_org(self):
        payload = {
            'sub_org_name': 'test',
            'sub_org_owner_email': self.user.email
        }
        resp = self.client.post(
            reverse_lazy('api:v3:organizations-sub-org', args=[self.org.pk]),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual('success', json.loads(resp.content)['status'])
        self.assertTrue(Organization.objects.filter(name='test').exists())


class AuthViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, _, _ = create_organization(self.user, "my org")
        self.client.login(**user_details)

    def test_is_authorized_base(self):
        resp = self.client.get(reverse_lazy('api:v3:user-current'))
        pk = json.loads(resp.content)['pk']
        resp = self.client.post(
            reverse_lazy("api:v3:user-is-authorized", args=[pk]) + '?organization_id=' + str(
                self.org.id),
            data=json.dumps({
                'actions': ['requires_owner', 'can_invite_member']
            }),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'auth': {
                    'requires_owner': True,
                    'can_invite_member': True,
                }
            })

    def test_is_authorized_parent_org_owner(self):
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org, _, _ = create_organization(other_user, "not my org")
        other_org.parent_org = self.org
        other_org.save()
        resp = self.client.post(
            reverse_lazy('api:v3:user-is-authorized',
                         args=[self.user.id]) + '?organization_id=' + str(other_org.id),
            data=json.dumps({
                'actions': ['requires_owner', 'can_invite_member']
            }),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'auth': {
                    'requires_owner': True,
                    'can_invite_member': True,
                }
            })

    def test_is_authorized_not_in_org(self):
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org, _, _ = create_organization(other_user, "not my org")
        resp = self.client.post(
            reverse_lazy("api:v3:user-is-authorized",
                         args=[self.user.pk]) + '?organization_id=' + str(other_org.id),
            data=json.dumps({
                'actions': ['requires_owner', 'can_invite_member']
            }),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'user does not exist'
            })

    def test_is_authorized_org_DNE(self):
        """DNE == does not exist"""
        resp = self.client.post(
            reverse_lazy("api:v3:user-is-authorized",
                         args=[self.user.pk]) + '?organization_id=' + '9999999',
            data=json.dumps({
                'actions': ['requires_owner', 'can_invite_member']
            }),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'organization does not exist'
            })

    def test_is_authorized_actions_DNE(self):
        """DNE == does not exist"""
        resp = self.client.post(
            reverse_lazy("api:v3:user-is-authorized",
                         args=[self.user.pk]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'organization_id': self.org.id,
            }),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'no actions to check'
            })

    def test_set_default_organization(self):
        """test seed.views.accounts.set_default_organization"""
        resp = self.client.put(
            reverse_lazy('api:v3:user-default-organization',
                         args=[self.user.id]) + f'?organization_id={self.org.pk}',
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
            })
        # refresh the user
        u = User.objects.get(pk=self.user.pk)
        self.assertEqual(u.default_organization, self.org)

    def test__get_default_org(self):
        """test seed.views.main._get_default_org"""
        org_id, org_name, org_role = _get_default_org(self.user)

        # check standard case
        self.assertEqual(org_id, self.org.id)
        self.assertEqual(org_name, self.org.name)
        self.assertEqual(org_role, 'owner')

        # check that the default org was set
        u = User.objects.get(pk=self.user.pk)
        self.assertEqual(u.default_organization, self.org)

        # check that '' is returned for a user without an org
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        org_id, org_name, org_role = _get_default_org(other_user)
        self.assertEqual(org_id, '')
        self.assertEqual(org_name, '')
        self.assertEqual(org_role, '')

        # check that the user is still in the default org, or update
        other_user.default_organization = self.org
        other_user.save()
        other_user = User.objects.get(pk=other_user.pk)
        self.assertEqual(other_user.default_organization, self.org)
        # _get_default_org should remove the user from the org and set the
        # next available org as default or set to ''
        org_id, org_name, org_role = _get_default_org(other_user)
        self.assertEqual(org_id, '')
        self.assertEqual(org_name, '')
        self.assertEqual(org_role, '')
