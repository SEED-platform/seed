"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import locale
import os
import tempfile

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from config.views import debug_media_serve
from seed.data_importer.models import ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER, AccessLevelInstance, OrganizationUser
from seed.models import (
    AUDIT_IMPORT,
    AUDIT_USER_EDIT,
    AnalysisInputFile,
    AnalysisOutputFile,
    BuildingFile,
    ImportFile,
    InventoryDocument,
    Organization,
    PropertyAuditLog,
)
from seed.test_helpers.fake import FakeAnalysisFactory, FakeAnalysisPropertyViewFactory, FakePropertyFactory, FakePropertyStateFactory
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization
from seed.views.v3.media import ModelForFileNotFoundError, check_file_permission
from seed.views.v3.uploads import get_upload_path


class TestMeasures(TestCase):
    def setUp(self):
        self.user_details_a = {"username": "user_a@test.com", "password": "test_pass_a", "email": "user_a@test.com"}
        self.user_a = User.objects.create_user(**self.user_details_a)
        self.user_details_b = {"username": "user_b@test.com", "password": "test_pass_b", "email": "user_b@test.com"}
        self.user_b = User.objects.create_user(**self.user_details_b)
        self.org_a = Organization.objects.create()
        self.root_a = AccessLevelInstance.objects.get(organization_id=self.org_a, depth=1)
        self.org_a_sub = Organization.objects.create()
        self.org_a_sub.parent_org = self.org_a
        self.org_a_sub.save()
        self.org_b = Organization.objects.create()
        self.root_b = AccessLevelInstance.objects.get(organization_id=self.org_b, depth=1)

        OrganizationUser.objects.create(user=self.user_a, organization=self.org_a, access_level_instance_id=self.root_a.id)
        OrganizationUser.objects.create(user=self.user_b, organization=self.org_b, access_level_instance_id=self.root_b.id)

    @classmethod
    def setUpClass(cls):
        # Override MEDIA_ROOT as the temporary dir (kind of a bad way to do this but ya know)
        cls.previous_media_root = settings.MEDIA_ROOT
        cls.temp_media_dir = tempfile.TemporaryDirectory()
        settings.MEDIA_ROOT = cls.temp_media_dir.name

        # create the files we'll use for testing
        # uploads files (those created in uploads API)
        cls.absolute_uploads_file = get_upload_path("test_uploads.txt")
        cls.uploads_file = os.path.relpath(cls.absolute_uploads_file, settings.MEDIA_ROOT)
        os.makedirs(os.path.dirname(cls.absolute_uploads_file), exist_ok=True)
        with open(cls.absolute_uploads_file, "w", encoding=locale.getpreferredencoding(False)) as f:
            f.write("Hello world")

        # BuildingSync file
        upload_to = BuildingFile._meta.get_field("file").upload_to
        cls.absolute_bsync_file = os.path.join(settings.MEDIA_ROOT, upload_to, "test_bsync.xml")
        os.makedirs(os.path.dirname(cls.absolute_bsync_file), exist_ok=True)
        cls.bsync_file = os.path.relpath(cls.absolute_bsync_file, settings.MEDIA_ROOT)
        with open(cls.absolute_bsync_file, "w", encoding=locale.getpreferredencoding(False)) as f:
            f.write("Hello world")

        # analysis output file
        upload_to = AnalysisOutputFile._meta.get_field("file").upload_to
        cls.absolute_analysis_output_file = os.path.join(settings.MEDIA_ROOT, upload_to, "test_analysis_output.xml")
        os.makedirs(os.path.dirname(cls.absolute_analysis_output_file), exist_ok=True)
        cls.analysis_output_file = os.path.relpath(cls.absolute_analysis_output_file, settings.MEDIA_ROOT)
        with open(cls.absolute_analysis_output_file, "w", encoding=locale.getpreferredencoding(False)) as f:
            f.write("Hello world")

        # inventory document file
        upload_to = InventoryDocument._meta.get_field("file").upload_to
        cls.absolute_inv_doc_file = os.path.join(settings.MEDIA_ROOT, upload_to, "test_inv_doc.osm")
        os.makedirs(os.path.dirname(cls.absolute_inv_doc_file), exist_ok=True)
        cls.inv_doc_file = os.path.relpath(cls.absolute_inv_doc_file, settings.MEDIA_ROOT)
        with open(cls.absolute_inv_doc_file, "w", encoding=locale.getpreferredencoding(False)) as f:
            f.write("Hello world")

    @classmethod
    def tearDownClass(cls):
        # set the media directory back
        settings.MEDIA_ROOT = cls.previous_media_root
        cls.temp_media_dir.cleanup()

    def test_successfully_get_uploads_file_when_user_is_org_member(self):
        # Setup
        # create an import file like we do in uploads API
        # b/c this is for org_a, user_a should be able to access it
        import_record = ImportRecord.objects.create(
            owner=self.user_a, last_modified_by=self.user_a, super_organization=self.org_a, access_level_instance=self.org_a.root
        )
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=os.path.basename(self.uploads_file), file=self.absolute_uploads_file
        )

        # Act
        is_permitted = check_file_permission(self.user_a, self.uploads_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_successfully_get_uploads_file_when_user_is_parent_org_member(self):
        # Setup
        # create an import file like we do in uploads API
        # b/c this is for org_a_sub, user_a should be able to access it
        import_record = ImportRecord.objects.create(
            owner=self.user_a,
            last_modified_by=self.user_a,
            # use suborg of org_a
            super_organization=self.org_a_sub,
            access_level_instance=self.org_a_sub.root,
        )
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=os.path.basename(self.uploads_file), file=self.absolute_uploads_file
        )

        # Act
        is_permitted = check_file_permission(self.user_a, self.uploads_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_uploads_file_when_user_is_not_org_member(self):
        # Setup
        # create an import file like we do in uploads API
        # b/c this is for org_a, user_b should NOT be able to access it
        import_record = ImportRecord.objects.create(
            owner=self.user_a, last_modified_by=self.user_a, super_organization=self.org_a, access_level_instance=self.org_a.root
        )
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=os.path.basename(self.uploads_file), file=self.absolute_uploads_file
        )

        # Act
        # check permission user_b, who is not part of the org and thus should not have access
        is_permitted = check_file_permission(self.user_b, self.uploads_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_successfully_get_bsync_file_when_user_is_org_member(self):
        # Setup
        # create BuildingFile for org_a
        BuildingFile.objects.create(
            file=self.absolute_bsync_file,
            filename=os.path.basename(self.bsync_file),
            file_type=BuildingFile.BUILDINGSYNC,
            property_state=(FakePropertyStateFactory(organization=self.org_a).get_property_state()),
        )

        # Act
        is_permitted = check_file_permission(self.user_a, self.bsync_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_bsync_file_when_user_is_not_org_member(self):
        # Setup
        # create BuildingFile for org_a
        BuildingFile.objects.create(
            file=self.absolute_bsync_file,
            filename=os.path.basename(self.bsync_file),
            file_type=BuildingFile.BUILDINGSYNC,
            property_state=(FakePropertyStateFactory(organization=self.org_a).get_property_state()),
        )

        # Act
        # check permission for non org user
        is_permitted = check_file_permission(self.user_b, self.bsync_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_successfully_get_analysis_input_file_when_user_is_org_member(self):
        # Setup
        analysis = FakeAnalysisFactory(organization=self.org_a, user=self.user_a).get_analysis()

        # create AnalysisInputFile for org_a
        # note we have to create the actual file here instead of in the setUp method
        # because the path is dependent on the analysis ID
        analysis_input_file = AnalysisInputFile.objects.create(analysis=analysis, content_type=AnalysisInputFile.BUILDINGSYNC)
        analysis_input_file.file.save("test.xml", ContentFile(b"Hello World"))
        analysis_input_file.save()

        # Act
        is_permitted = check_file_permission(self.user_a, analysis_input_file.file.name)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_analysis_input_file_when_user_is_not_org_member(self):
        # Setup
        analysis = FakeAnalysisFactory(organization=self.org_a, user=self.user_a).get_analysis()

        # create AnalysisInputFile for org_a
        # note we have to create the actual file here instead of in the setUp method
        # because the path is dependent on the analysis ID
        analysis_input_file = AnalysisInputFile.objects.create(analysis=analysis, content_type=AnalysisInputFile.BUILDINGSYNC)
        analysis_input_file.file.save("test.xml", ContentFile(b"Hello World"))
        analysis_input_file.save()

        # Act
        # check permission for user_b, not part of org
        is_permitted = check_file_permission(self.user_b, analysis_input_file.file.name)

        # Assert
        self.assertFalse(is_permitted)

    def test_fails_get_analysis_input_file_when_analysis_does_not_exist(self):
        # Setup
        analysis = FakeAnalysisFactory(organization=self.org_a, user=self.user_a).get_analysis()
        analysis_input_file = AnalysisInputFile.objects.create(analysis=analysis, content_type=AnalysisInputFile.BUILDINGSYNC)
        analysis_input_file.file.save("test.xml", ContentFile(b"Hello World"))
        filepath = analysis_input_file.file.name
        # deleting the analysis leaves its input files on disk
        analysis.delete()

        # Act / Assert
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_b, filepath)

        self.client.login(**self.user_details_b)
        response = self.client.get(f"/api/v3/media/{filepath}")
        self.assertEqual(response.status_code, 404)

    def test_successfully_get_analysis_output_file_when_user_is_org_member(self):
        # Setup
        # create AnalysisOutputFile for org_a
        analysis = FakeAnalysisFactory(organization=self.org_a, user=self.user_a).get_analysis()
        analysis_property_view = FakeAnalysisPropertyViewFactory(
            organization=self.org_a, user=self.user_a, analysis=analysis
        ).get_analysis_property_view()
        analysis_output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC, file=self.absolute_analysis_output_file
        )
        analysis_output_file.analysis_property_views.set([analysis_property_view.id])

        # Act
        is_permitted = check_file_permission(self.user_a, self.analysis_output_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_analysis_output_file_when_user_is_not_org_member(self):
        # Setup
        # create AnalysisOutputFile for org_a
        analysis = FakeAnalysisFactory(organization=self.org_a, user=self.user_a).get_analysis()
        analysis_property_view = FakeAnalysisPropertyViewFactory(
            organization=self.org_a, user=self.user_a, analysis=analysis
        ).get_analysis_property_view()
        analysis_output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC, file=self.absolute_analysis_output_file
        )
        analysis_output_file.analysis_property_views.set([analysis_property_view.id])

        # Act
        # check permission for user_b, not part of org
        is_permitted = check_file_permission(self.user_b, self.analysis_output_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_successfully_get_inv_doc_file_when_user_is_org_member(self):
        # Setup
        # create InventoryDocument for org_a
        InventoryDocument.objects.create(
            file=self.absolute_inv_doc_file,
            filename=os.path.basename(self.inv_doc_file),
            file_type=InventoryDocument.OSM,
            property=(FakePropertyFactory(organization=self.org_a).get_property()),
        )

        # Act
        is_permitted = check_file_permission(self.user_a, self.inv_doc_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_inv_doc_file_when_user_is_not_org_member(self):
        # Setup
        # create InventoryDocument for org_a
        InventoryDocument.objects.create(
            file=self.absolute_inv_doc_file,
            filename=os.path.basename(self.inv_doc_file),
            file_type=InventoryDocument.OSM,
            property=(FakePropertyFactory(organization=self.org_a).get_property()),
        )

        # Act
        # check permission for non org user
        is_permitted = check_file_permission(self.user_b, self.inv_doc_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_fails_when_path_does_not_match(self):
        # test import files
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "uploads/bogus.txt")

        # test buildingsync files
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "buildingsync_files/bogus.txt")

        # test analysis input files
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "analysis_input_files/bogus/bogus.txt")

        # test analysis output files
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "analysis_output_files/bogus.txt")

        # test bad path
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "/inventory_documents/file.txt")

        # test bad path
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "/super-secret/file.txt")

        # test bad path
        with pytest.raises(ModelForFileNotFoundError):
            check_file_permission(self.user_a, "")

    def test_retrieve_file_successfully(self):
        """Test that retrieve endpoint serves files correctly"""
        # Setup - create an import file
        import_record = ImportRecord.objects.create(
            owner=self.user_a, last_modified_by=self.user_a, super_organization=self.org_a, access_level_instance=self.org_a.root
        )
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=os.path.basename(self.uploads_file), file=self.absolute_uploads_file
        )

        self.client.login(**self.user_details_a)
        response = self.client.get(f"/api/v3/media/{self.uploads_file}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Hello world")
        self.assertIn("Content-Disposition", response)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_retrieve_file_with_comma_in_filename(self):
        """Test that files with commas in filename download correctly"""
        # Setup - create a file with commas in the name
        absolute_comma_file = get_upload_path("test,file,with,commas.txt")
        comma_file = os.path.relpath(absolute_comma_file, settings.MEDIA_ROOT)
        os.makedirs(os.path.dirname(absolute_comma_file), exist_ok=True)
        with open(absolute_comma_file, "w", encoding=locale.getpreferredencoding(False)) as f:
            f.write("File with commas")

        import_record = ImportRecord.objects.create(
            owner=self.user_a, last_modified_by=self.user_a, super_organization=self.org_a, access_level_instance=self.org_a.root
        )
        ImportFile.objects.create(import_record=import_record, uploaded_filename=os.path.basename(comma_file), file=absolute_comma_file)

        self.client.login(**self.user_details_a)
        response = self.client.get(f"/api/v3/media/{comma_file}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"File with commas")
        # Verify the download filename is sanitized (commas removed)
        self.assertIn("Content-Disposition", response)
        self.assertIn("testfilewithcommas.txt", response["Content-Disposition"])
        self.assertNotIn(",", response["Content-Disposition"])

    def test_retrieve_file_without_permission_returns_404(self):
        """Test that users without permission get 404"""
        # Setup - create an import file for org_a
        import_record = ImportRecord.objects.create(
            owner=self.user_a, last_modified_by=self.user_a, super_organization=self.org_a, access_level_instance=self.org_a.root
        )
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=os.path.basename(self.uploads_file), file=self.absolute_uploads_file
        )

        # user_b tries to access org_a's file
        self.client.login(**self.user_details_b)
        response = self.client.get(f"/api/v3/media/{self.uploads_file}")

        self.assertEqual(response.status_code, 404)

    def test_retrieve_nonexistent_file_returns_404(self):
        """Test that requesting non-existent file returns 404"""
        self.client.login(**self.user_details_a)
        response = self.client.get("/api/v3/media/uploads/nonexistent.txt")

        self.assertEqual(response.status_code, 404)


class TestMediaAccessLevels(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        self.sibling_member_user_details = {"username": "sibling_member@demo.com", "password": "test_pass"}
        self.sibling_member_user = User.objects.create_user(**self.sibling_member_user_details)
        self.org.add_member(self.sibling_member_user, self.sibling_level_instance.pk, ROLE_MEMBER)

        # keep the files written by these tests out of the real media root
        self.media_root = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=self.media_root))

        self.cycle = self.cycle_factory.get_cycle()
        self.child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        self.sibling_property = self.property_factory.get_property(access_level_instance=self.sibling_level_instance)

    def _write_file(self, filepath, content):
        """Write a file to the media root and return its path relative to the media root"""
        absolute_filepath = os.path.join(self.media_root, os.path.normpath(filepath))
        os.makedirs(os.path.dirname(absolute_filepath), exist_ok=True)
        with open(absolute_filepath, "wb") as f:
            f.write(content)
        return filepath

    def _create_import_file(self, filename, organization, access_level_instance, content):
        filepath = self._write_file(f"uploads/{filename}", content)
        import_record = ImportRecord.objects.create(
            owner=self.root_owner_user,
            last_modified_by=self.root_owner_user,
            super_organization=organization,
            access_level_instance=access_level_instance,
        )
        # like the uploads API, store the absolute path
        ImportFile.objects.create(
            import_record=import_record, uploaded_filename=filename, file=os.path.join(self.media_root, os.path.normpath(filepath))
        )
        return filepath

    def _create_building_file(self, filename, property_state, content):
        filepath = self._write_file(f"buildingsync_files/{filename}", content)
        BuildingFile.objects.create(file=filepath, filename=filename, file_type=BuildingFile.BUILDINGSYNC, property_state=property_state)
        return filepath

    def _get(self, user_details, filepath):
        self.client.logout()
        self.client.login(**user_details)
        return self.client.get(f"/api/v3/media/{filepath}")

    def _assert_allowed(self, filepath, content, *users_details):
        for user_details in users_details:
            with self.subTest(filepath=filepath, user=user_details["username"]):
                response = self._get(user_details, filepath)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, content)

    def _assert_denied(self, filepath, content, *users_details):
        for user_details in users_details:
            with self.subTest(filepath=filepath, user=user_details["username"]):
                response = self._get(user_details, filepath)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(content, response.content)

    def test_root_import_file_is_denied_to_child_and_sibling_members(self):
        filepath = self._create_import_file("root.csv", self.org, self.root_level_instance, b"root import")

        self._assert_allowed(filepath, b"root import", self.superuser_details, self.root_owner_user_details, self.root_member_user_details)
        self._assert_denied(filepath, b"root import", self.child_member_user_details, self.sibling_member_user_details)

    def test_child_import_file_is_available_to_ancestors_only(self):
        filepath = self._create_import_file("child.csv", self.org, self.child_level_instance, b"child import")

        self._assert_allowed(filepath, b"child import", self.root_member_user_details, self.child_member_user_details)
        self._assert_denied(filepath, b"child import", self.sibling_member_user_details)

    def test_other_organizations_import_file_is_available_to_superusers_only(self):
        other_org, _, _ = create_organization(User.objects.create_user(username="other_user@demo.com"), "other org")
        filepath = self._create_import_file("other_org.csv", other_org, other_org.root, b"other org import")

        # the superuser isn't a member of the other organization
        self._assert_allowed(filepath, b"other org import", self.superuser_details)
        self._assert_denied(filepath, b"other org import", self.root_owner_user_details, self.root_member_user_details)

    def test_buildingsync_file_on_current_view_is_available_to_ancestors_only(self):
        view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle)
        filepath = self._create_building_file("current.xml", view.state, b"current bsync")

        self._assert_allowed(filepath, b"current bsync", self.root_member_user_details, self.child_member_user_details)
        self._assert_denied(filepath, b"current bsync", self.sibling_member_user_details)

    def test_buildingsync_file_on_earlier_state_belongs_to_the_property_it_was_merged_into(self):
        view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle)
        earlier_state = self.property_state_factory.get_property_state()
        edited_state = self.property_state_factory.get_property_state()
        # the file's state was edited, and the edited state was then merged into the view's current state
        PropertyAuditLog.objects.create(
            organization=self.org, parent_state1=earlier_state, state=edited_state, name="Manual Edit", record_type=AUDIT_USER_EDIT
        )
        PropertyAuditLog.objects.create(
            organization=self.org,
            parent_state1=self.property_state_factory.get_property_state(),
            parent_state2=edited_state,
            state=view.state,
            name="System Match",
            record_type=AUDIT_IMPORT,
        )
        # a cycle in the audit log must not loop forever
        PropertyAuditLog.objects.create(
            organization=self.org, parent_state1=view.state, state=earlier_state, name="Manual Edit", record_type=AUDIT_USER_EDIT
        )
        filepath = self._create_building_file("earlier.xml", earlier_state, b"earlier bsync")

        self._assert_allowed(filepath, b"earlier bsync", self.root_member_user_details, self.child_member_user_details)
        self._assert_denied(filepath, b"earlier bsync", self.sibling_member_user_details)

    def test_buildingsync_file_ownership_takes_the_same_queries_however_many_states_follow_it(self):
        # e.g., a property's history, whose files are each checked, can follow many edits
        def query_count(generations):
            view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle_factory.get_cycle())
            states = [self.property_state_factory.get_property_state() for _ in range(generations)]
            for parent_state, state in zip(states, [*states[1:], view.state], strict=True):
                PropertyAuditLog.objects.create(
                    organization=self.org, parent_state1=parent_state, state=state, name="Manual Edit", record_type=AUDIT_USER_EDIT
                )
            filepath = self._create_building_file(f"edited_{generations}.xml", states[0], b"edited bsync")
            with CaptureQueriesContext(connection) as queries:
                self.assertTrue(check_file_permission(self.child_member_user, filepath))
            return len(queries)

        self.assertEqual(query_count(1), query_count(8))

    def test_buildingsync_file_on_state_without_view_is_root_only(self):
        filepath = self._create_building_file("no_view.xml", self.property_state_factory.get_property_state(), b"no view bsync")

        self._assert_allowed(filepath, b"no view bsync", self.root_member_user_details)
        self._assert_denied(filepath, b"no view bsync", self.child_member_user_details, self.sibling_member_user_details)

    def test_analysis_files_are_available_to_ancestors_only(self):
        analysis = FakeAnalysisFactory(organization=self.org, user=self.root_owner_user).get_analysis(
            access_level_instance=self.child_level_instance
        )
        input_file = AnalysisInputFile.objects.create(analysis=analysis, content_type=AnalysisInputFile.BUILDINGSYNC)
        input_file.file.save("input.xml", ContentFile(b"analysis input"))
        analysis_property_view = FakeAnalysisPropertyViewFactory(organization=self.org, analysis=analysis).get_analysis_property_view(
            property_obj=self.child_property, cycle=self.cycle
        )
        output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC, file=self._write_file("analysis_output_files/output.xml", b"analysis output")
        )
        output_file.analysis_property_views.add(analysis_property_view)

        for filepath, content in ((input_file.file.name, b"analysis input"), (output_file.file.name, b"analysis output")):
            self._assert_allowed(filepath, content, self.root_member_user_details, self.child_member_user_details)
            self._assert_denied(filepath, content, self.sibling_member_user_details)

    def test_inventory_document_is_available_to_its_property_ancestors_only(self):
        filepath = self._write_file("inventory_documents/sibling.osm", b"sibling document")
        InventoryDocument.objects.create(
            file=filepath, filename="sibling.osm", file_type=InventoryDocument.OSM, property=self.sibling_property
        )

        self._assert_allowed(filepath, b"sibling document", self.root_member_user_details, self.sibling_member_user_details)
        self._assert_denied(filepath, b"sibling document", self.child_member_user_details)

    def test_only_html_analysis_reports_are_shown_in_the_browser(self):
        # members can upload these, so they are downloaded instead of shown, which could run their scripts
        document_filepath = self._write_file("inventory_documents/page.html", b"<script>document</script>")
        InventoryDocument.objects.create(file=document_filepath, filename="page.html", property=self.child_property)
        uploaded_filepaths = [
            self._create_import_file("page.html", self.org, self.child_level_instance, b"<script>import</script>"),
            self._create_import_file("image.svg", self.org, self.child_level_instance, b"<svg><script>import</script></svg>"),
            document_filepath,
        ]
        # HTML analysis reports, which analysis pipelines (e.g., BETTER's) store and members cannot upload, are shown in an iframe
        analysis = FakeAnalysisFactory(organization=self.org, user=self.root_owner_user).get_analysis(
            access_level_instance=self.child_level_instance
        )
        analysis_property_view = FakeAnalysisPropertyViewFactory(organization=self.org, analysis=analysis).get_analysis_property_view(
            property_obj=self.child_property, cycle=self.cycle
        )
        report = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.HTML, file=self._write_file("analysis_output_files/report.html", b"<html>report</html>")
        )
        report.analysis_property_views.add(analysis_property_view)

        for filepath in uploaded_filepaths:
            with self.subTest(filepath=filepath):
                response = self._get(self.child_member_user_details, filepath)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Disposition"], f'attachment; filename="{os.path.basename(filepath)}"')

        response = self._get(self.child_member_user_details, report.file.name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")
        self.assertNotIn("Content-Disposition", response)

    def test_development_media_route_checks_access(self):
        # when DEBUG is on, files are also served at MEDIA_URL (e.g., /media/) for development
        filepath = self._create_import_file("root.csv", self.org, self.root_level_instance, b"root import")

        for user, status_code in [
            # as for the API, since `SEEDAuthentication` always "succeeds" (with no user), DRF denies permission
            (AnonymousUser(), 403),
            (self.child_member_user, 404),
            (self.sibling_member_user, 404),
            (self.root_member_user, 200),
        ]:
            with self.subTest(user=str(user)):
                request = RequestFactory().get(f"/media/{filepath}")
                request.user = user
                response = debug_media_serve(request, filepath)
                # Django renders DRF's responses (e.g., for denied permissions) when the URL resolver calls the view
                if hasattr(response, "render"):
                    response.render()
                self.assertEqual(response.status_code, status_code)
                if status_code == 200:
                    self.assertEqual(response.content, b"root import")
                    self.assertEqual(response["Content-Disposition"], 'attachment; filename="root.csv"')
                else:
                    self.assertNotIn(b"root import", response.content)

    def test_files_without_an_owning_record_are_not_found(self):
        # these records' references to their state, property, organization, or property views are optional
        document_filepath = self._write_file("inventory_documents/orphan.osm", b"orphan document")
        InventoryDocument.objects.create(file=document_filepath, filename="orphan.osm", file_type=InventoryDocument.OSM, property=None)
        output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC, file=self._write_file("analysis_output_files/orphan.xml", b"orphan output")
        )
        files = (
            (self._create_building_file("orphan.xml", None, b"orphan bsync"), b"orphan bsync"),
            (document_filepath, b"orphan document"),
            (self._create_import_file("orphan.csv", None, self.root_level_instance, b"orphan import"), b"orphan import"),
            (output_file.file.name, b"orphan output"),
        )

        for filepath, content in files:
            with self.subTest(filepath=filepath), pytest.raises(ModelForFileNotFoundError):
                check_file_permission(self.root_member_user, filepath)
            self._assert_denied(filepath, content, self.superuser_details, self.root_member_user_details)

    def test_sub_organization_files_are_limited_to_parent_root_members(self):
        sub_org = Organization.objects.create(name="sub-organization", parent_org=self.org)
        filepath = self._create_import_file("sub_org.csv", sub_org, sub_org.root, b"sub-organization import")

        self.assertTrue(check_file_permission(self.root_member_user, filepath))
        self.assertFalse(check_file_permission(self.child_member_user, filepath))
        self.assertFalse(check_file_permission(self.sibling_member_user, filepath))

    def test_property_history_only_links_files_the_user_can_download(self):
        # a root user's import created the child property's state, but its file also holds other access levels' records
        filepath = self._create_import_file("root.csv", self.org, self.root_level_instance, b"root import")
        view = self.property_view_factory.get_property_view(prprty=self.child_property, cycle=self.cycle)
        PropertyAuditLog.objects.filter(state=view.state).update(import_filename=f"{self.media_root}/{filepath}".replace("\\", "/"))
        url = reverse("api:v3:properties-detail", args=[view.pk]) + f"?organization_id={self.org.id}"

        for user_details, file in [
            (self.root_member_user_details, f"{settings.MEDIA_URL}{filepath}"),
            (self.child_member_user_details, None),
        ]:
            with self.subTest(user=user_details["username"]):
                self.client.logout()
                self.client.login(**user_details)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                # the file name is still shown
                self.assertEqual([(h["filename"], h["file"]) for h in response.json()["history"]], [("root.csv", file)])
