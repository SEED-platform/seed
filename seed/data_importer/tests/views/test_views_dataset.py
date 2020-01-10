# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.urls import reverse

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


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
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.org_2, _, _ = create_organization()

        self.import_record = ImportRecord.objects.create(owner=self.user,
                                                         super_organization=self.org)
        self.import_record_2 = ImportRecord.objects.create(owner=self.user,
                                                           super_organization=self.org_2)
        self.import_file_1 = ImportFile.objects.create(import_record=self.import_record)
        self.import_file_2 = ImportFile.objects.create(import_record=self.import_record_2)

        self.client.login(**user_details)

    def test_delete_file_no_perms(self):
        """ tests the delete_file request invalid request"""
        url = reverse("api:v2:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org.pk),
            content_type='application/json',
        )
        json_string = response.content
        data = json.loads(json_string)

        # assert
        self.assertEqual(data, {
            'status': 'error',
            'message': 'user does not have permission to delete file'
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ImportFile.objects.all().count(), 2)

    def test_delete_file_wrong_org(self):
        """ tests the delete_file request with wrong org"""
        url = reverse("api:v2:import_files-detail", args=[self.import_file_2.pk])
        response = self.client.delete(
            url + '?organization_id=' + str(self.org_2.pk),
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
