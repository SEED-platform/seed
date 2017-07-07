# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse_lazy

from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tests.util import DataMappingBaseTestCase
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser


class DeleteFileViewTests(DataMappingBaseTestCase):
    """
    Tests of the SEED Building Detail page
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)
        self.client.login(**user_details)

        import_record = ImportRecord.objects.create(
            super_organization=self.org
        )
        self.org_2 = org_2 = Organization.objects.create()
        import_record_2 = ImportRecord.objects.create(
            super_organization=org_2
        )
        import_file_1 = ImportFile.objects.create(
            import_record=import_record,
        )
        import_file_1.save()
        import_file_2 = ImportFile.objects.create(
            import_record=import_record_2,
        )
        import_file_2.save()

        self.import_record = import_record
        self.import_file_1 = import_file_1
        self.import_file_2 = import_file_2

    def test_delete_file(self):
        """ tests the delete_file request"""
        url = reverse_lazy("seed:delete_file")
        delete_data = {
            'file_id': self.import_file_1.pk,
            'organization_id': self.org.pk,
        }

        # act
        response = self.client.delete(
            url,
            data=json.dumps(delete_data),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {'status': 'success'})
        self.assertEqual(ImportFile.objects.all().count(), 1)

    def test_delete_file_no_perms(self):
        """ tests the delete_file request invalid request"""
        url = reverse_lazy("seed:delete_file")
        delete_data = {
            'file_id': self.import_file_2.pk,
            'organization_id': self.org.pk,
        }

        # act
        response = self.client.delete(
            url,
            data=json.dumps(delete_data),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'user does not have permission to delete file'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)

    def test_delete_file_wrong_org(self):
        """ tests the delete_file request with wrong org"""
        url = reverse_lazy("seed:delete_file")
        delete_data = {
            'file_id': self.import_file_2.pk,
            'organization_id': self.org_2.pk,
        }

        # act
        response = self.client.delete(
            url,
            data=json.dumps(delete_data),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'No relationship to organization'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)

    def test_delete_file_wrong_method(self):
        """ tests the delete_file request with wrong http method"""
        url = reverse_lazy("seed:delete_file")
        delete_data = {
            'file_id': self.import_file_1.pk,
            'organization_id': self.org.pk,
        }

        # act
        response = self.client.get(
            url,
            delete_data,
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'only HTTP DELETE allowed'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)

        # act with put
        response = self.client.put(
            url,
            data=json.dumps(delete_data),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'only HTTP DELETE allowed'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)

        # act with post
        response = self.client.post(
            url,
            data=json.dumps(delete_data),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'only HTTP DELETE allowed'
        })
        self.assertEqual(ImportFile.objects.all().count(), 2)
