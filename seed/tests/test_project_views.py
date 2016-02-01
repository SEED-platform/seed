# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    OrganizationUser,
    Organization
)
from seed.tests.util import FakeRequest
from seed.models import Project
from seed.data_importer.models import ImportRecord


class ProjectsViewTests(TestCase):
    """
    Tests of the SEED project views: get_project, get_projects, create_project,
    delete_project, update_project, add_buildings_to_project,
    remove_buildings_from_project, get_project_count
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
        self.org.add_member(self.user)
        self.client.login(**user_details)
        self.fake_request = FakeRequest(user=self.user)

    def _create_project(self, name="demo_project", org_id=None, user=None,
                        via_http=False):
        """helper to create a project, returns the responce"""
        if org_id is None:
            org_id = self.org.id
        if user is None:
            user = self.user

        if via_http:
            return self.client.post(
                reverse_lazy('projects:create_project'),
                data=json.dumps({
                    'organization_id': org_id,
                    'project': {
                        'name': name
                    }
                }),
                content_type='application/json',
            )
        else:
            p = Project.objects.create(
                name=name,
                super_organization_id=org_id,
                owner=user
            )
            p.last_modified_by = user
            p.save()

    def _set_role_level(self, role_level, user=None, org=None):
        """helper to set an org user's role level"""
        if user is None:
            user = self.user
        if org is None:
            org = self.org
        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.role_level = role_level
        ou.save()

    def test_create_project_perms(self):
        """ tests create_project perms"""
        ou = OrganizationUser.objects.get(
            user=self.user, organization=self.org
        )
        # standard case
        ou.role_level = ROLE_MEMBER
        ou.save()
        resp = self._create_project('Proj1', via_http=True)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'project_slug': 'proj1'
            }
        )
        # test that owner is good too
        ou.role_level = ROLE_OWNER
        ou.save()
        resp = self._create_project('Proj2', via_http=True)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'project_slug': 'proj2'
            }
        )
        # test that viewer cannot create a project
        ou.role_level = ROLE_VIEWER
        ou.save()
        resp = self._create_project('Proj3', via_http=True)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )

    def test_get_projects(self):
        """tests get_projects"""
        self._create_project('proj1', self.org.pk)
        other_org = Organization.objects.create(name='not my org')
        # standard case, should only see proj1, not other_proj
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.get(
            reverse_lazy("projects:get_projects"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        projects = json.loads(resp.content)['projects']
        std_output = {
            u'projects': [
                {
                    u'is_compliance': False,
                    u'last_modified': projects[0]['last_modified'],
                    u'last_modified_by': {
                        u'email': u'test_user@demo.com',
                        u'first_name': u'Johnny',
                        u'last_name': u'Energy'
                    },
                    u'name': u'proj1',
                    u'number_of_buildings': 0,
                    u'slug': u'proj1',
                    u'status': u'active'
                }
            ],
            u'status': u'success'
        }
        self.assertDictEqual(
            json.loads(resp.content),
            std_output
        )
        # test for member
        self._set_role_level(ROLE_MEMBER)
        resp = self.client.get(
            reverse_lazy("projects:get_projects"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            std_output
        )
        # test for owner
        self._set_role_level(ROLE_OWNER)
        resp = self.client.get(
            reverse_lazy("projects:get_projects"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            std_output
        )
        # test for an org the user does not belong
        resp = self.client.get(
            reverse_lazy("projects:get_projects"),
            {'organization_id': other_org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            }
        )

    def test_get_project(self):
        """tests get_project"""
        self._create_project('proj1', self.org.pk)
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username="tester@be.com",
            email="tester@be.com",
        )
        other_org.add_member(other_user)
        self._create_project('otherproj', other_org.pk, other_user)
        # standard case, should only see proj1, not other_proj
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.get(
            reverse_lazy("projects:get_project"),
            {'organization_id': self.org.id, 'project_slug': 'proj1'},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                u'project': {
                    u'description': None,
                    u'id': json.loads(resp.content)['project']['id'],
                    u'is_compliance': False,
                    u'last_modified_by_id': self.user.pk,
                    u'name': u'proj1',
                    u'owner_id': self.user.pk,
                    u'slug': u'proj1',
                    u'status': 1,
                    u'super_organization_id': self.org.id
                },
                u'status': u'success'}
        )
        # test when user sends org id that the user is in, but a project in
        # a different org
        resp = self.client.get(
            reverse_lazy("projects:get_project"),
            {'organization_id': self.org.id, 'project_slug': 'otherproj'},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )
        # test for the case that a user does not belong to the org
        resp = self.client.get(
            reverse_lazy("projects:get_project"),
            {'organization_id': other_org.pk, 'project_slug': 'otherproj'},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            }
        )

    def test_delete_project(self):
        """tests delete_project"""
        self._create_project(name='proj1', via_http=True)
        self._set_role_level(ROLE_MEMBER)
        # standard case
        self.assertEqual(Project.objects.all().count(), 1)
        resp = self.client.delete(
            reverse_lazy("projects:delete_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project_slug': 'proj1'}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(json.loads(resp.content), {'status': 'success'})
        self.assertEqual(Project.objects.all().count(), 0)
        # test viewer cannot delete
        self._create_project(name='proj1', via_http=True)
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.delete(
            reverse_lazy("projects:delete_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project_slug': 'proj1'}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {'status': 'error', 'message': 'Permission denied'}
        )
        # only delete the project if you are a member of its org
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username="tester@be.com",
            email="tester@be.com",
        )
        self._create_project('proj2', other_org.pk, other_user)
        self._set_role_level(ROLE_MEMBER)
        resp = self.client.delete(
            reverse_lazy("projects:delete_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project_slug': 'proj2'}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {'status': 'error', 'message': 'Permission denied'}
        )

    def test_update_project(self):
        """tests update_project"""
        self._create_project(name='proj1', via_http=True)
        self._set_role_level(ROLE_MEMBER)
        project = {
            'name': 'proj22',
            'slug': 'proj1',
            'is_compliance': None
        }
        resp = self.client.post(
            reverse_lazy("projects:update_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'message': 'project proj22 updated'
            }
        )
        p = Project.objects.get(slug='proj1')
        self.assertEqual(p.name, 'proj22')

        # test that a view cannot update
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.post(
            reverse_lazy("projects:update_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )

    def test_add_buildings_to_project(self):
        """tests add_buildings_to_project"""
        self._create_project(name='proj33', via_http=True)
        self._set_role_level(ROLE_MEMBER)
        project = {
            'name': 'proj33',
            'project_slug': 'proj33',
        }
        # test standard case
        resp = self.client.post(
            reverse_lazy("projects:add_buildings_to_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'project_loading_cache_key': (
                    'SEED_PROJECT_ADDING_BUILDINGS_PERCENTAGE_proj33'
                )
            }
        )
        # test case where user is viewer
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.post(
            reverse_lazy("projects:add_buildings_to_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )

    def test_remove_buildings_from_project(self):
        """tests remove_buildings_from_project"""
        self._create_project(name='proj_remove', via_http=True)
        self._set_role_level(ROLE_MEMBER)
        project = {
            'name': 'proj_remove',
            'project_slug': 'proj_remove',
            'slug': 'proj_remove',
        }
        # test standard case
        resp = self.client.post(
            reverse_lazy("projects:remove_buildings_from_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'project_removing_cache_key': (
                    'SEED_PROJECT_REMOVING_BUILDINGS_PERCENTAGE_proj_remove'
                )
            }
        )
        # test case where user is viewer
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.post(
            reverse_lazy("projects:remove_buildings_from_project"),
            data=json.dumps(
                {'organization_id': self.org.id, 'project': project}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )

    def test_get_projects_count(self):
        """tests get_projects_count"""
        self._create_project(name='proj_count', via_http=True)
        self._set_role_level(ROLE_VIEWER)

        # test standard case
        resp = self.client.get(
            reverse_lazy("projects:get_projects_count"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'projects_count': 1
            }
        )
        # test case where user is not in org
        other_org = Organization.objects.create(name='not my org')
        resp = self.client.get(
            reverse_lazy("projects:get_projects_count"),
            {'organization_id': other_org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            }
        )

    def test_get_datasets_count(self):
        """tests get_datasets_count"""
        self._set_role_level(ROLE_VIEWER)
        ImportRecord.objects.create(
            name="test_count",
            super_organization=self.org,
            owner=self.user,
        )
        other_org = Organization.objects.create(name='not my org')
        other_user = User.objects.create(
            username="tester@be.com",
            email="tester@be.com",
        )
        other_org.add_member(other_user)
        ImportRecord.objects.create(
            name="test_count",
            super_organization=other_org,
            owner=other_user,
        )

        # test standard case
        resp = self.client.get(
            reverse_lazy("seed:get_datasets_count"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'datasets_count': 1
            }
        )
        # test case where user is not in org
        resp = self.client.get(
            reverse_lazy("seed:get_datasets_count"),
            {'organization_id': other_org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'No relationship to organization'
            }
        )
        # test case where org does not exist
        resp = self.client.get(
            reverse_lazy("seed:get_datasets_count"),
            {'organization_id': 999},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            }
        )
