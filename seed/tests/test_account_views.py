# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from datetime import date

from django.core.urlresolvers import reverse_lazy, NoReverseMatch
from django.test import TestCase

# from seed.models.data_quality import (
#     DataQualityCheck
# )
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.exceptions import InsufficientPermission
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    OrganizationUser,
    Organization
)
from seed.models.cycles import Cycle
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.public.models import SharedBuildingField
from seed.tests.util import FakeRequest
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
        self.org = Organization.objects.create(name='my org')
        self.cycle = Cycle.objects.filter(organization=self.org).first()
        self.org.add_member(self.user)
        self.client.login(**user_details)
        self.fake_request = FakeRequest(user=self.user)
        self.maxDiff = None

        year = date.today().year - 1
        self.cal_year_name = "{} Calendar Year".format(year)

    def test_dict_org(self):
        """_dict_org turns our org structure into a json payload."""

        expected_single_org_payload = {
            'sub_orgs': [],
            'owners': [{
                'first_name': u'Johnny',
                'last_name': u'Energy',
                'email': u'test_user@demo.com',
                'id': self.user.pk}],
            'number_of_users': 1,
            'name': 'my org',
            'user_role': 'owner',
            'is_parent': True,
            'parent_id': self.org.pk,
            'org_id': self.org.pk,
            'id': self.org.pk,
            'user_is_owner': True,
            'cycles': [{
                'num_taxlots': 0,
                'num_properties': 0,
                'name': self.cal_year_name,
                'cycle_id': self.cycle.pk
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
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

        new_org = Organization.objects.create(name="sub")
        new_org.parent_org = self.org
        new_org.save()
        new_org.add_member(self.user)
        new_cycle = Cycle.objects.filter(organization=new_org).first()

        expected_multiple_org_payload = {
            'sub_orgs': [{
                'sub_orgs': [],
                'owners': [{
                    'first_name': u'Johnny',
                    'last_name': u'Energy',
                    'email': u'test_user@demo.com',
                    'id': self.user.pk}],
                'number_of_users': 1,
                'name': 'sub',
                'user_role': 'owner',
                'is_parent': False,
                'parent_id': self.org.pk,
                'org_id': new_org.pk,
                'id': new_org.pk,
                'user_is_owner': True,
                'cycles': [{
                    'num_taxlots': 0,
                    'num_properties': 0,
                    'name': self.cal_year_name,
                    'cycle_id': new_cycle.pk
                }],
                'created': self.org.created.strftime('%Y-%m-%d'),
            }],
            'owners': [{
                'first_name': u'Johnny',
                'last_name': u'Energy',
                'email': u'test_user@demo.com',
                'id': self.user.pk}],
            'number_of_users': 1,
            'name': 'my org',
            'user_role': 'owner',
            'is_parent': True,
            'parent_id': self.org.pk,
            'org_id': self.org.pk,
            'id': self.org.pk,
            'user_is_owner': True,
            'cycles': [{
                'num_taxlots': 0,
                'num_properties': 0,
                'name': self.cal_year_name,
                'cycle_id': self.cycle.pk
            }],
            'created': self.org.created.strftime('%Y-%m-%d'),
        }

        org_payload = _dict_org(self.fake_request, Organization.objects.all())

        self.assertEqual(len(org_payload), 2)
        self.assertDictEqual(org_payload[0], expected_multiple_org_payload)

    def test_get_organizations(self):
        """ tests accounts.get_organizations """
        resp = self.client.get(
            reverse_lazy('apiv2:organizations-list'),
            content_type='application/json',
        )
        orgs = json.loads(resp.content)['organizations']
        org = orgs[0]
        self.assertEquals(org['name'], 'my org')
        self.assertEquals(org['number_of_users'], 1)
        self.assertDictEqual(
            org['owners'][0],
            {
                'email': u'test_user@demo.com',
                'first_name': u'Johnny',
                'last_name': u'Energy',
                'id': self.user.pk  # since this could change
            }
        )
        self.assertTrue(org['user_is_owner'])

    def test_get_organization_no_org(self):
        """test for error when no organization_id sent"""
        with self.assertRaises(NoReverseMatch):
            self.client.get(
                reverse_lazy('apiv2:organizations-detail'),
                content_type='application/json',
            )

    def test_get_organization_std_case(self):
        """test normal case"""
        resp = self.client.get(
            reverse_lazy('apiv2:organizations-detail', args=[self.org.id]),
            content_type='application/json',
        )

        org = json.loads(resp.content)['organization']
        self.assertEquals(org['name'], 'my org')
        self.assertEquals(org['number_of_users'], 1)
        self.assertDictEqual(
            org['owners'][0],
            {
                'email': u'test_user@demo.com',
                'first_name': u'Johnny',
                'last_name': u'Energy',
                'id': self.user.pk  # since this could change
            }
        )
        self.assertTrue(org['user_is_owner'])

    def test_get_organization_user_not_owner(self):
        """test for the case where a user does not have access"""
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org.add_member(other_user)

        resp = self.client.get(
            reverse_lazy('apiv2:organizations-detail', args=[other_org.id]),
            content_type='application/json',
        )
        self.assertEquals(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            })

    def test_get_organization_org_doesnt_exist(self):
        """test for the case where a user does not have access"""
        resp = self.client.get(
            reverse_lazy('apiv2:organizations-detail', args=[self.org.id + 100]),
            content_type='application/json',
        )
        self.assertEquals(
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
            reverse_lazy('apiv2:organizations-remove-user', args=[self.org.id]),
            data=json.dumps({'user_id': u.id}),
            content_type='application/json',
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
            reverse_lazy('apiv2:organizations-remove-user', args=[self.org.id]),
            data=json.dumps({'user_id': self.user.id}),
            content_type='application/json',
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
            reverse_lazy('apiv2:organizations-remove-user', args=[self.org.id]),
            data=json.dumps({'user_id': self.user.id}),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            })

    def test_remove_user_from_org_missing_org_id(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)
        with self.assertRaises(NoReverseMatch):
            self.client.delete(
                reverse_lazy('apiv2:organizations-remove-user') + '?organization_id=' + str(
                    self.org.id),
                data=json.dumps({'user_id': u.id}),
                content_type='application/json',
            )

    def test_remove_user_from_org_missing_user_id(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)

        resp = self.client.delete(
            reverse_lazy('apiv2:organizations-remove-user', args=[self.org.id]),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'missing the user_id'
            })

    def test_remove_user_from_org_user_DNE(self):
        """DNE = does not exist"""
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u)

        resp = self.client.delete(
            reverse_lazy('apiv2:organizations-remove-user', args=[self.org.id]),
            data=json.dumps({'user_id': 9999}),
            content_type='application/json',
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
            reverse_lazy('apiv2:organizations-remove-user', args=[9999]),
            data=json.dumps({'user_id': u.id}),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            })

    def test__get_js_role(self):
        self.assertEquals(_get_js_role(ROLE_OWNER), 'owner')
        self.assertEquals(_get_js_role(ROLE_MEMBER), 'member')
        self.assertEquals(_get_js_role(ROLE_VIEWER), 'viewer')

    def test__get_role_from_js(self):
        self.assertEquals(_get_role_from_js('owner'), ROLE_OWNER)
        self.assertEquals(_get_role_from_js('member'), ROLE_MEMBER)
        self.assertEquals(_get_role_from_js('viewer'), ROLE_VIEWER)

    def test_update_role(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_VIEWER)

        ou = OrganizationUser.objects.get(
            user_id=u.id, organization_id=self.org.id)
        self.assertEquals(ou.role_level, ROLE_VIEWER)

        resp = self.client.put(
            reverse_lazy("apiv2:users-update-role", args=[u.id]) + '?organization_id=' + str(
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
        self.assertEquals(ou.role_level, ROLE_MEMBER)

    def test_allowed_to_update_role_if_not_last_owner(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_OWNER)

        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertEquals(ou.role_level, ROLE_OWNER)

        resp = self.client.put(
            reverse_lazy("apiv2:users-update-role",
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
        self.assertEquals(ou.role_level, ROLE_MEMBER)

    def test_cannot_update_role_if_last_owner(self):
        u = User.objects.create(username='b@b.com', email='b@be.com')
        self.org.add_member(u, role=ROLE_MEMBER)

        ou = OrganizationUser.objects.get(
            user_id=self.user.id, organization_id=self.org.id)
        self.assertEquals(ou.role_level, ROLE_OWNER)

        resp = self.client.put(
            reverse_lazy("apiv2:users-update-role",
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
                'message': 'an organization must have at least one owner level member'
            })
        self.assertEquals(ou.role_level, ROLE_OWNER)

    def test_update_role_no_perms(self):
        """ Test trying to change your own role when you are not an owner. """
        ou = OrganizationUser.objects.get(user=self.user,
                                          organization=self.org)
        ou.role_level = ROLE_MEMBER
        ou.save()

        url = reverse_lazy('apiv2:users-update-role', args=[self.user.id])
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
        url = reverse_lazy('apiv2:organizations-save-settings', args=[self.org.id])

        res = self.client.put(
            url,
            data={},
            content_type='application/json'
        )
        response = json.loads(res.content)
        # don't really care what the message is
        self.assertEqual(response['status'], 'error')

    def test_query_threshold(self):
        url = reverse_lazy('apiv2:organizations-save-settings', args=[self.org.id])
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
        url = reverse_lazy('apiv2:organizations-shared-fields', args=[self.org.pk])
        res = self.client.get(url)
        response = json.loads(res.content)
        self.assertEqual(response,
                         {'status': 'success',
                          'shared_fields': [],
                          'public_fields': []})

    def test_get_shared_fields(self):
        field1 = self.org.exportable_fields.create(
            name='property_name', field_model='BuildingSnapshot'
        )
        field2 = self.org.exportable_fields.create(
            name='building_count', field_model='BuildingSnapshot'
        )

        SharedBuildingField.objects.create(
            org=self.org, field=field1
        )

        SharedBuildingField.objects.create(
            org=self.org, field=field2
        )

        url = reverse_lazy('apiv2:organizations-shared-fields', args=[self.org.pk])
        res = self.client.get(url)
        response = json.loads(res.content)
        self.assertEqual(response['status'], 'success')

        shared_fields = response['shared_fields']
        self.assertEqual(len(shared_fields), 2)

        self.assertEqual(shared_fields[0]['title'],
                         'Building Count')
        self.assertEqual(shared_fields[0]['sort_column'],
                         'building_count')
        self.assertEqual(shared_fields[1]['title'],
                         'Property Name')
        self.assertEqual(shared_fields[1]['sort_column'],
                         'property_name')

    def test_add_shared_fields(self):
        url = reverse_lazy('apiv2:organizations-save-settings', args=[self.org.pk])
        payload = {
            u'organization_id': self.org.pk,
            u'organization': {
                u'owners': self.user.pk,
                u'query_threshold': 2,
                u'name': self.org.name,
                u'fields': [
                    {
                        u'field_type': u'building_information',
                        u'sortable': True,
                        u'title': u'PM Property ID',
                        u'sort_column': u'pm_property_id',
                        u'class': u'is_aligned_right',
                        u'link': True,
                        u'checked': True,
                        u'static': False,
                        u'type': u'link',
                        u'title_class': u''
                    },
                    {
                        u'field_type': u'building_information',
                        u'sortable': True,
                        u'title': u'Tax Lot ID',
                        u'sort_column': u'tax_lot_id',
                        u'class': u'is_aligned_right',
                        u'link': True,
                        u'checked': True,
                        u'static': False,
                        u'type': u'link',
                        u'title_class': u''
                    }
                ],
            }
        }

        self.client.put(
            url,
            json.dumps(payload),
            content_type='application/json'
        )

        fields = self.org.exportable_fields.values_list('name', flat=True)
        self.assertTrue('tax_lot_id' in fields)
        self.assertTrue('pm_property_id' in fields)
        self.assertEqual(len(fields), 2)

    # def test_get_data_quality_rules_matching(self):
    #     dq = DataQualityCheck.retrieve(self.org)
    #     dq.add_rule({
    #         'table_name': 'PropertyState',
    #         'field': 'address_line_1',
    #         'category': CATEGORY_MISSING_MATCHING_FIELD,
    #         'severity': 0,
    #     })
    #     response = self.client.get(reverse_lazy('apiv2:organizations-data-quality-rules', args=[self.org.pk]))
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
    #     response = self.client.get(reverse_lazy('apiv2:organizations-data-quality-rules', args=[self.org.pk]))
    #     self.assertEqual('success', json.loads(response.content)['status'])
    #
    # def test_get_data_quality_rules_range(self):
    #     dq = DataQualityCheck.retrieve(self.org)
    #     dq.add_rule({
    #         'table_name': 'PropertyState',
    #         'field': 'address_line_1',
    #         'severity': 0,
    #     })
    #     response = self.client.get(reverse_lazy('apiv2:organizations-data-quality-rules', args=[self.org.pk]))
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
    #         reverse_lazy('apiv2:organizations-save-data-quality-rules', args=[self.org.pk]),
    #         data=json.dumps(payload),
    #         content_type='application/json',
    #     )
    #     self.assertEqual('success', json.loads(resp.content)['status'])

    def test_update_user(self):
        """test for update_user"""
        user_data = {
            'first_name': 'bob',
            'last_name': 'd',
            'email': 'some@hgg.com'
        }
        resp = self.client.put(
            reverse_lazy('apiv2:users-detail', args=[self.user.pk]),
            json.dumps(user_data),
            content_type='application/json',
        )
        self.assertEquals(
            json.loads(resp.content),
            {
                'status': 'success',
                u'api_key': u'',
                u'email': u'some@hgg.com',
                u'first_name': u'bob',
                u'last_name': u'd'

            })

    def test_get_user_profile(self):
        """test for get_user_profile"""
        resp = self.client.get(
            reverse_lazy('apiv2:users-detail', args=[self.user.pk]),
            content_type='application/json',
        )
        self.assertEquals(
            json.loads(resp.content),
            {
                'status': 'success',
                'api_key': '',
                'email': 'test_user@demo.com',
                'first_name': 'Johnny',
                'last_name': 'Energy'

            })
        resp = self.client.post(
            reverse_lazy('apiv2:users-generate-api-key', args=[self.user.pk]),
            content_type='application/json',
        )
        resp = self.client.get(
            reverse_lazy('apiv2:users-detail', args=[self.user.pk]),
            content_type='application/json',
        )
        self.assertEquals(
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
        resp = self.client.get(
            reverse_lazy('apiv2:users-generate-api-key', args=[self.user.pk]),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        api_key = user.api_key

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.check_password('new passwordD3'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(resp.status_code, 405)
        self.assertEquals(
            json.loads(resp.content),
            {
                'detail': 'Method \"POST\" not allowed.',
            })

        resp = self.client.get(
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            password_payload,
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(resp.status_code, 405)
        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:users-set-password', args=[self.user.pk]),
            json.dumps(password_payload),
            content_type='application/json',
        )
        user = User.objects.get(pk=self.user.pk)
        self.assertFalse(user.check_password('new password'))

        self.assertEquals(
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
            reverse_lazy('apiv2:organizations-sub-org', args=[self.org.pk]),
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
        self.org = Organization.objects.create(name='my org')
        self.org.add_member(self.user)
        self.client.login(**user_details)

    def test_is_authorized_base(self):
        resp = self.client.get(reverse_lazy('apiv2:users-current-user-id'))
        pk = json.loads(resp.content)['pk']
        resp = self.client.post(
            reverse_lazy("apiv2:users-is-authorized", args=[pk]) + '?organization_id=' + str(
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
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org.add_member(other_user)
        other_org.parent_org = self.org
        other_org.save()
        resp = self.client.post(
            reverse_lazy('apiv2:users-is-authorized',
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
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username='tester@be.com',
            email='tester@be.com',
        )
        other_org.add_member(other_user)
        resp = self.client.post(
            reverse_lazy("apiv2:users-is-authorized",
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
            reverse_lazy("apiv2:users-is-authorized",
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
            reverse_lazy("apiv2:users-is-authorized",
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
            reverse_lazy('apiv2:users-default-organization', args=[self.user.id]),
            data=json.dumps({'organization_id': self.org.id}),
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
