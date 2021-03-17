# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse_lazy
from django.utils.text import slugify

from seed.data_importer.models import ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    OrganizationUser
)
from seed.models import (
    Project, ProjectPropertyView,
    PropertyView
)
from seed.test_helpers import fake
from seed.tests.util import FakeRequest, DeleteModelsTestCase
from seed.utils.organizations import create_organization

DEFAULT_NAME = 'proj1'


class ProjectViewTests(DeleteModelsTestCase):
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
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.client.login(**user_details)
        self.fake_request = FakeRequest(user=self.user)

    def _create_project(self, name=DEFAULT_NAME, org_id=None, user=None,
                        via_http=False, **kwargs):
        """helper to create a project, returns the response"""
        if org_id is None:
            org_id = self.org.id
        if user is None:
            user = self.user

        if via_http:
            data = {
                'name': name,
                'status': 'active',
                'description': '',
                'is_compliance': False
            }
            data.update(kwargs)
            data = json.dumps(data)
            url = "{}?organization_id={}".format(
                reverse_lazy("api:v2:projects-list"), str(org_id)
            )
            x = self.client.post(
                url,
                data=data,
                content_type='application/json'
            )
            return x
        else:
            p = Project.objects.create(
                name=name,
                super_organization_id=org_id,
                owner=user,
                description='',
            )
            p.last_modified_by = user
            p.save()
            return p

    def _create_property_view(self, project):
        property_factory = fake.FakePropertyFactory(organization=self.org)
        property = property_factory.get_property()
        property_state_factory = fake.FakePropertyStateFactory(organization=self.org)
        state = property_state_factory.get_property_state()
        cycle_factory = fake.FakeCycleFactory()
        cycle = cycle_factory.get_cycle()
        property_view, _ = PropertyView.objects.get_or_create(
            property=property, cycle=cycle, state=state
        )
        return property_view

    def _set_role_level(self, role_level, user=None, org=None):
        """helper to set an org user's role level"""
        if user is None:
            user = self.user
        if org is None:
            org = self.org
        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.role_level = role_level
        ou.save()

    def _expected_project(self, modified, pk, has_views, name=DEFAULT_NAME,
                          **kwargs):
        expected = {
            'compliance_type': None,
            'deadline_date': None,
            'description': '',
            'end_date': None,
            'id': pk,
            'is_compliance': False,
            'modified': modified,
            'last_modified_by': {'email': 'test_user@demo.com',
                                 'first_name': 'Johnny',
                                 'last_name': 'Energy'},
            'name': name,
            'property_count': 0,
            'slug': slugify(name),
            'taxlot_count': 0,
            'status': 'active',
        }
        if has_views:
            expected.update({
                'property_views': [],
                'taxlot_views': [],
            })
        expected.update(kwargs)
        return expected

    def test_create_project_perms(self):
        """ tests create_project perms"""
        ou = OrganizationUser.objects.get(
            user=self.user, organization=self.org
        )
        # standard case
        ou.role_level = ROLE_MEMBER
        ou.save()
        resp = self._create_project('proj1', via_http=True)
        result = json.loads(resp.content)
        expected = {
            'status': 'success',
            'project': self._expected_project(
                result['project']['modified'],
                result['project']['id'],
                False
            )
        }
        expected['project']['last_modified_by'] = {
            'email': None,
            'first_name': None,
            'last_name': None
        }
        self.assertDictEqual(expected, result)
        # test that owner is good too
        ou.role_level = ROLE_OWNER
        ou.save()
        resp = self._create_project('Proj2', via_http=True)
        result = json.loads(resp.content)
        expected = {
            'status': 'success',
            'project': self._expected_project(
                result['project']['modified'],
                result['project']['id'],
                False, name='Proj2'
            )
        }
        expected['project']['last_modified_by'] = {
            'email': None,
            'first_name': None,
            'last_name': None
        }
        self.assertDictEqual(expected, result)
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
        other_org, _, _ = create_organization()
        # standard case, should only see proj1, not other_proj
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.get(
            reverse_lazy('api:v2:projects-list'),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        projects = json.loads(resp.content)['projects']
        std_output = {
            'projects': [
                self._expected_project(
                    projects[0]['modified'], projects[0]['id'], False
                ),
            ],
            'status': 'success'
        }
        self.assertDictEqual(
            json.loads(resp.content),
            std_output
        )
        # test for member
        self._set_role_level(ROLE_MEMBER)
        resp = self.client.get(
            reverse_lazy("api:v2:projects-list"),
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
            reverse_lazy("api:v2:projects-list"),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            std_output
        )
        # test for an org the user does not belong
        resp = self.client.get(
            reverse_lazy("api:v2:projects-list"),
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
        project = self._create_project('proj1', self.org.pk)
        other_user = User.objects.create(
            username="tester@example.org",
            email="tester@example.org",
        )
        other_org, self.org_user, _ = create_organization(other_user)

        self._create_project('otherproj', other_org.pk, other_user)
        # standard case, should only see proj1, not other_proj
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.get(
            reverse_lazy('api:v2:projects-detail', args=[project.slug]),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        result = json.loads(resp.content)
        expected = {
            'status': 'success',
            'project': self._expected_project(
                result['project']['modified'],
                result['project']['id'],
                True
            )
        }
        self.assertDictEqual(expected, result)
        # test when user sends org id that the user is in, but a project in
        # a different org
        resp = self.client.get(
            reverse_lazy('api:v2:projects-detail', args=['otherproj']),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Could not find project with slug: otherproj'
            }
        )
        # test for the case that a user does not belong to the org
        resp = self.client.get(
            reverse_lazy('api:v2:projects-detail', args=['otherproj']),
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
        project = json.loads(self._create_project(name='proj1', via_http=True).content)['project']
        self._set_role_level(ROLE_MEMBER)
        # standard case
        self.assertEqual(Project.objects.all().count(), 1)
        url = "{}?organization_id={}".format(
            reverse_lazy('api:v2:projects-detail', args=[project['slug']]),
            str(self.org.id)
        )
        resp = self.client.delete(url)
        self.assertDictEqual(
            json.loads(resp.content),
            {'status': 'success'}
        )
        self.assertEqual(Project.objects.all().count(), 0)
        # test viewer cannot delete
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.delete(url)
        self.assertDictEqual(
            json.loads(resp.content),
            {'status': 'error', 'message': 'Permission denied'}
        )
        # only delete the project if you are a member of its org
        other_user = User.objects.create(
            username="tester@example.org",
            email="tester@example.org",
        )
        other_org, _, _ = create_organization(other_user)
        project = self._create_project('proj2', other_org.pk, other_user)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}".format(
            reverse_lazy('api:v2:projects-detail', args=[project.slug]),
            str(self.org.id)
        )
        resp = self.client.delete(url)
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'message': 'Could not find project with slug: proj2',
                'status': 'error'
            }
        )

    def test_update_project(self):
        """tests update_project"""
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        self._set_role_level(ROLE_MEMBER)
        resp = self.client.get(
            reverse_lazy('api:v2:projects-detail', args=[project['slug']]),
            {'organization_id': self.org.id},
            content_type='application/json',
        )
        # using put requires all fields according to proper REST
        # semantics, so use values returned by create
        project['name'] = 'proj22'
        url = "{}?organization_id={}".format(
            reverse_lazy('api:v2:projects-detail', args=[project['slug']]),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(
                project
            ),
            content_type='application/json',
        )
        result = json.loads(resp.content)
        expected = self._expected_project(
            result['project']['modified'],
            result['project']['id'],
            False, name='proj22', slug='proj1'
        )
        self.assertDictEqual(
            result,
            {
                'status': 'success',
                'project': expected
            }
        )
        p = Project.objects.get(slug='proj1')
        self.assertEqual(p.name, 'proj22')

        # test partial update
        project['name'] = 'proj33'
        url = "{}?organization_id={}".format(
            reverse_lazy('api:v2:projects-detail', args=[project['slug']]),
            str(self.org.id)
        )
        resp = self.client.patch(
            url,
            data=json.dumps({
                'name': 'proj33'
            }),
            content_type='application/json',
        )
        result = json.loads(resp.content)
        expected = self._expected_project(
            result['project']['modified'],
            result['project']['id'],
            False, name='proj33', slug='proj1'
        )
        self.assertDictEqual(
            result,
            {
                'status': 'success',
                'project': expected
            }
        )
        p = Project.objects.get(slug='proj1')
        self.assertEqual(p.name, 'proj33')

        # test that a view cannot update
        self._set_role_level(ROLE_VIEWER)
        url = "{}?organization_id={}".format(
            reverse_lazy('api:v2:projects-detail', args=[project['slug']]),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(project),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )
        resp = self.client.patch(
            url,
            data=json.dumps(project),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Permission denied'
            }
        )

    def test_add_inventory_to_project(self):
        """tests adding inventory to project"""
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'added': [pv.id]
            }
        )
        # test case where user is viewer
        self._set_role_level(ROLE_VIEWER)
        resp = self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
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

    def test_remove_inventory_from_project(self):
        """tests remove_inventory_from_project"""
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        project_view = ProjectPropertyView.objects.get(
            project=proj, property_view=pv
        )
        # test standard case
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-remove-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'removed': [project_view.id]
            }
        )
        self.assertFalse(ProjectPropertyView.objects.filter(
            project=proj, property_view=pv
        ).exists())

    def test_remove_inventory_from_project_select_all(self):
        """tests remove inventory from project"""
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        project_view = ProjectPropertyView.objects.get(
            project=proj, property_view=pv
        )
        # test standard case
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-remove-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'removed': [project_view.id]
            }
        )
        self.assertFalse(ProjectPropertyView.objects.filter(
            project=proj, property_view=pv
        ).exists())

    def test_remove_inventory_from_project_viewer(self):
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        # test case where user is viewer
        self._set_role_level(ROLE_VIEWER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-remove-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
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
            reverse_lazy("api:v2:projects-count") + '?organization_id=' + str(self.org.id),
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'success',
                'count': 1
            }
        )
        # test case where user is not in org
        other_org, _, _ = create_organization(None, 'not my org')
        resp = self.client.get(
            reverse_lazy("api:v2:projects-count") + '?organization_id=' + str(other_org.id),
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
        other_user = User.objects.create(
            username="tester@example.org",
            email="tester@example.org",
        )
        other_org, _, _ = create_organization(other_user, 'not my org')
        ImportRecord.objects.create(
            name="test_count",
            super_organization=other_org,
            owner=other_user,
        )
        resp = self.client.get(
            reverse_lazy("api:v3:datasets-count") + '?organization_id=' + str(self.org.id),
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
            reverse_lazy("api:v3:datasets-count") + '?organization_id=' + str(other_org.id),
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
            reverse_lazy("api:v3:datasets-count") + '?organization_id=999',
            content_type='application/json',
        )
        self.assertDictEqual(
            json.loads(resp.content),
            {
                'status': 'error',
                'message': 'Organization does not exist'
            }
        )

    def test_copy_inventory(self):
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        project2 = json.loads(
            self._create_project(name='proj2', via_http=True).content
        )['project']
        proj2 = Project.objects.get(pk=project2['id'])

        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-copy', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps({
                'selected': [pv.id],
                'target': project2['id']
            }),
            content_type='application/json',
        )

        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
            }
        )
        self.assertTrue(
            ProjectPropertyView.objects.filter(
                project=proj, property_view=pv
            ).exists()
        )
        self.assertTrue(
            ProjectPropertyView.objects.filter(
                project=proj2, property_view=pv
            ).exists()
        )

    def test_move_inventory(self):
        project = json.loads(
            self._create_project(name='proj1', via_http=True).content
        )['project']
        proj = Project.objects.get(pk=project['id'])
        pv = self._create_property_view(proj)
        self._set_role_level(ROLE_MEMBER)
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-add-inventory', args=[project['slug']]
            ),
            str(self.org.id)
        )
        self.client.put(
            url,
            data=json.dumps(
                {'selected': [pv.id]}
            ),
            content_type='application/json',
        )
        project2 = json.loads(
            self._create_project(name='proj2', via_http=True).content
        )['project']
        url = "{}?organization_id={}&inventory_type=property".format(
            reverse_lazy(
                'api:v2:projects-move', args=[project['slug']]
            ),
            str(self.org.id)
        )
        resp = self.client.put(
            url,
            data=json.dumps({
                'selected': [pv.id],
                'target': project2['id']
            }),
            content_type='application/json',
        )
        self.assertEqual(
            json.loads(resp.content),
            {
                'status': 'success',
            }
        )
        proj2 = Project.objects.get(pk=project2['id'])
        self.assertTrue(
            ProjectPropertyView.objects.filter(
                project=proj2, property_view=pv
            ).exists()
        )
        self.assertFalse(
            ProjectPropertyView.objects.filter(
                project=proj, property_view=pv
            ).exists()
        )
