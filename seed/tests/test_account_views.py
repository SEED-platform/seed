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
from seed.views.main import _get_default_org
from seed.views.organizations import _dict_org
from seed.views.users import _get_js_role, _get_role_from_js


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

        self.org.access_level_names = ["root", "children", "grandchildren"]
        self.ali_a = self.org.add_new_access_level_instance(self.org.root.id, "a")
        self.ali_b = self.org.add_new_access_level_instance(self.org.root.id, "b")
        self.ali_c = self.org.add_new_access_level_instance(self.ali_a.id, "c")

        self.child_a_details = {
            'username': 'a@a.com',
            'password': 'test_pass',
        }
        self.child_a = User.objects.create_user(**self.child_a_details)
        self.org.add_member(self.child_a, self.ali_a.pk, role=ROLE_MEMBER)

        self.child_b_details = {
            'username': 'b@b.com',
            'password': 'test_pass',
        }
        self.child_b = User.objects.create_user(**self.child_b_details)
        self.org.add_member(self.child_b, self.ali_b.pk, role=ROLE_MEMBER)

        self.org.save()

        self.child_c_details = {
            'username': 'c@c.com',
            'password': 'test_pass',
        }
        self.child_c = User.objects.create_user(**self.child_c_details)
        self.org.add_member(self.child_c, self.ali_c.pk, role=ROLE_MEMBER)

        self.org.save()

    def test_dict_org(self):
        """_dict_org turns our org structure into a json payload."""

        expected_single_org_payload = {
            'sub_orgs': [],
            'owners': [{
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'email': 'test_user@demo.com',
                'id': self.user.pk}],
            'number_of_users': 4,
            'name': 'my org',
            'display_decimal_places': 2,
            'display_units_area': 'ft**2',
            'display_units_eui': 'kBtu/ft**2/year',
            'user_role': 'owner',
            'is_parent': True,
            'mapquest_api_key': '',
            'display_meter_units': Organization._default_display_meter_units,
            'thermal_conversion_assumption': Organization.US,
            'parent_id': self.org.pk,
            'org_id': self.org.pk,
            'id': self.org.pk,
            'user_is_owner': True,
            'cycles': [{
                'num_taxlots': 0,
                'num_properties': 0,
                'name': str(self.cal_year_name),
                'cycle_id': self.cycle.pk
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
            'comstock_enabled': False,
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

    def test_dic_org_w_member_in_parent_and_child(self):
        """What happens when a user has a role in parent and child."""

        new_org, _, _ = create_organization(self.user, "sub")
        new_org.parent_org = self.org
        new_org.save()
        new_cycle = Cycle.objects.filter(organization=new_org).first()

        expected_multiple_org_payload = {
            'sub_orgs': [{
                'sub_orgs': [],
                'owners': [{
                    'first_name': 'Johnny',
                    'last_name': 'Energy',
                    'email': 'test_user@demo.com',
                    'id': self.user.pk}],
                'number_of_users': 1,
                'name': 'sub',
                'user_role': 'owner',
                'is_parent': False,
                'mapquest_api_key': '',
                'display_meter_units': Organization._default_display_meter_units,
                'thermal_conversion_assumption': Organization.US,
                'parent_id': self.org.pk,
                'org_id': new_org.pk,
                'id': new_org.pk,
                'user_is_owner': True,
                'display_units_area': 'ft**2',
                'display_units_eui': 'kBtu/ft**2/year',
                'display_decimal_places': 2,
                'cycles': [{
                    'num_taxlots': 0,
                    'num_properties': 0,
                    'name': str(self.cal_year_name),
                    'cycle_id': new_cycle.pk
                }],
                'created': self.org.created.strftime('%Y-%m-%d'),
                'comstock_enabled': False,
            }],
            'owners': [{
                'first_name': 'Johnny',
                'last_name': 'Energy',
                'email': 'test_user@demo.com',
                'id': self.user.pk}],
            'number_of_users': 4,
            'name': 'my org',
            'user_role': 'owner',
            'is_parent': True,
            'mapquest_api_key': '',
            'display_meter_units': Organization._default_display_meter_units,
            'thermal_conversion_assumption': Organization.US,
            'parent_id': self.org.pk,
            'org_id': self.org.pk,
            'id': self.org.pk,
            'user_is_owner': True,
            'display_decimal_places': 2,
            'display_units_area': 'ft**2',
            'display_units_eui': 'kBtu/ft**2/year',
            'cycles': [{
                'num_taxlots': 0,
                'num_properties': 0,
                'name': str(self.cal_year_name),
                'cycle_id': self.cycle.pk
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
            'comstock_enabled': False,
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
        self.assertEqual(org['number_of_users'], 4)
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
        self.assertEqual(org['number_of_users'], 4)
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

    def test_get_user_list_permissions(self):
        johnny = {
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
            'number_of_orgs': 1,
            'user_id': self.user.pk,
            'role': 'owner',
            'access_level_instance_name': 'root',
            'access_level': 'root'
        }
        a = {
            'email': 'a@a.com',
            'first_name': '',
            'last_name': '',
            'number_of_orgs': 1,
            'user_id': self.child_a.pk,
            'role': 'member',
            'access_level_instance_name': 'a',
            'access_level': 'children'
        }
        b = {
            'email': 'b@b.com',
            'first_name': '',
            'last_name': '',
            'number_of_orgs': 1,
            'user_id': self.child_b.pk,
            'role': 'member',
            'access_level_instance_name': 'b',
            'access_level': 'children'
        }
        c = {
            'email': 'c@c.com',
            'first_name': '',
            'last_name': '',
            'number_of_orgs': 1,
            'user_id': self.child_c.pk,
            'role': 'member',
            'access_level_instance_name': 'c',
            'access_level': 'grandchildren'
        }

        resp = self.client.get(
            reverse_lazy('api:v3:organization-users-list', args=[self.org.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'users': [johnny, a, b, c]
            }
        )

        self.client.login(**self.child_a_details)
        resp = self.client.get(
            reverse_lazy('api:v3:organization-users-list', args=[self.org.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'users': [johnny, a, c]
            }
        )

        self.client.login(**self.child_b_details)
        resp = self.client.get(
            reverse_lazy('api:v3:organization-users-list', args=[self.org.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'users': [johnny, b]
            }
        )

        self.client.login(**self.child_c_details)
        resp = self.client.get(
            reverse_lazy('api:v3:organization-users-list', args=[self.org.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'users': [johnny, a, c]
            }
        )

    def test_remove_user_from_org_std(self):
        """test removing a user"""
        # normal case
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, access_level_instance_id=self.org.root.id)

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
        self.child_a.delete()
        self.child_b.delete()
        self.child_c.delete()
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
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_MEMBER, access_level_instance_id=self.org.root.id)
        self.assertEqual(self.org.users.count(), 5)

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
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, access_level_instance_id=self.org.root.id)

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
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, access_level_instance_id=self.org.root.id)

        resp = self.client.delete(
            reverse_lazy('api:v3:organization-users-remove', args=[9999, u.id]),
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            })

    def test__get_js_role(self):
        self.assertEqual(_get_js_role(ROLE_OWNER), 'owner')
        self.assertEqual(_get_js_role(ROLE_MEMBER), 'member')
        self.assertEqual(_get_js_role(ROLE_VIEWER), 'viewer')

    def test__get_role_from_js(self):
        self.assertEqual(_get_role_from_js('owner'), ROLE_OWNER)
        self.assertEqual(_get_role_from_js('member'), ROLE_MEMBER)
        self.assertEqual(_get_role_from_js('viewer'), ROLE_VIEWER)

    def test_update_role(self):
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_VIEWER, access_level_instance_id=self.org.root.id)

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
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_OWNER, access_level_instance_id=self.org.root.id)

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
        u = User.objects.create(username='d@d.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_MEMBER, access_level_instance_id=self.org.root.id)

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

    # def test_get_data_quality_rules_matching(self):
    #     dq = DataQualityCheck.retrieve(self.org)
    #     dq.add_rule({
    #         'table_name': 'PropertyState',
    #         'field': 'address_line_1',
    #         'category': CATEGORY_MISSING_MATCHING_FIELD,
    #         'severity': 0,
    #     })
    #     response = self.client.get(reverse_lazy('api:v2:organizations-data-quality-rules', args=[self.org.pk]))
    #     self.assertEqual('success', json.loads(response.content)['status'])
    #
    # def test_get_data_quality_rules_values(self):
    #     dq = DataQualityCheck.retrieve(self.org)
    #     dq.add_rule({
    #         'table_name': 'PropertyState',
    #         'field': 'address_line_1',
    #         'category': CATEGORY_MISSING_VALUES,
    #         'severity': 0,
    #     })
    #     response = self.client.get(reverse_lazy('api:v2:organizations-data-quality-rules', args=[self.org.pk]))
    #     self.assertEqual('success', json.loads(response.content)['status'])
    #
    # def test_get_data_quality_rules_range(self):
    #     dq = DataQualityCheck.retrieve(self.org)
    #     dq.add_rule({
    #         'table_name': 'PropertyState',
    #         'field': 'address_line_1',
    #         'severity': 0,
    #     })
    #     response = self.client.get(reverse_lazy('api:v2:organizations-data-quality-rules', args=[self.org.pk]))
    #     self.assertEqual('success', json.loads(response.content)['status'])
    #
    # def test_save_data_quality_rules(self):
    #     payload = {
    #         'organization_id': self.org.pk,
    #         'data_quality_rules': {
    #             'missing_matching_field': [
    #                 {
    #                     'table_name': 'PropertyState',
    #                     'field': 'address_line_1',
    #                     'severity': 'error'
    #                 }
    #             ],
    #             'missing_values': [
    #                 {
    #                     'table_name': 'PropertyState',
    #                     'field': 'address_line_1',
    #                     'severity': 'error'
    #                 }
    #             ],
    #             'in_range_checking': [
    #                 {
    #                     'table_name': 'PropertyState',
    #                     'field': 'conditioned_floor_area',
    #                     'enabled': True,
    #                     'type': 'number',
    #                     'min': None,
    #                     'max': 7000000,
    #                     'severity': 'error',
    #                     'units': 'square feet'
    #                 },
    #             ]
    #         }
    #     }
    #
    #     resp = self.client.put(
    #         reverse_lazy('api:v2:organizations-save-data-quality-rules', args=[self.org.pk]),
    #         data=json.dumps(payload),
    #         content_type='application/json',
    #     )
    #     self.assertEqual('success', json.loads(resp.content)['status'])

    def test_add_user_permissions(self):
        data_json = {
            "first_name": "d",
            "last_name": "d",
            "email": "d@d.com",
            "role": "member",
            "access_level_instance_id": self.org.root.pk
        }
        resp = self.client.post(reverse_lazy(
            'api:v3:user-list') + f'?organization_id={self.org.pk}',
            json.dumps(data_json),
            content_type='application/json'
        )
        assert resp.status_code == 200

        a_org_user = OrganizationUser.objects.get(organization=self.org, user=self.child_a)
        a_org_user.role_level = ROLE_OWNER
        a_org_user.save()
        self.client.login(**self.child_a_details)
        resp = self.client.post(
            reverse_lazy('api:v3:user-list') + f'?organization_id={self.org.pk}',
            json.dumps(data_json),
            content_type='application/json'
        )
        assert resp.status_code == 404

        data_json["access_level_instance_id"] = self.ali_c.pk
        resp = self.client.post(
            reverse_lazy('api:v3:user-list') + f'?organization_id={self.org.pk}',
            json.dumps(data_json),
            content_type='application/json'
        )
        assert resp.status_code == 200

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
        org_user = OrganizationUser.objects.get(user=self.user, organization=self.org)

        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'user': {
                    'id': org_user.pk,
                    'access_level_instance': {'id': self.org.root.id, 'name': 'root'},
                }
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
