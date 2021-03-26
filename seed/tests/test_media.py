import os
import tempfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase

from seed.test_helpers.fake import FakePropertyStateFactory, FakeAnalysisFactory, FakeAnalysisPropertyViewFactory
from seed.views.v3.media import check_file_permission, ModelForFileNotFound
from seed.views.v3.uploads import get_upload_path
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.data_importer.models import ImportRecord
from seed.models import (
    Organization,
    BuildingFile,
    ImportFile,
    AnalysisInputFile,
    AnalysisOutputFile
)


class TestMeasures(TestCase):
    def setUp(self):
        self.user_a = User.objects.create(username='user_a')
        self.user_b = User.objects.create(username='user_b')
        self.org_a = Organization.objects.create()
        self.org_a_sub = Organization.objects.create()
        self.org_a_sub.parent_org = self.org_a
        self.org_a_sub.save()
        self.org_b = Organization.objects.create()

        OrganizationUser.objects.create(
            user=self.user_a, organization=self.org_a
        )
        OrganizationUser.objects.create(
            user=self.user_b, organization=self.org_b
        )

    @classmethod
    def setUpClass(cls):
        # Override MEDIA_ROOT as the temporary dir (kind of a bad way to do this but ya know)
        cls.temp_media_dir = tempfile.TemporaryDirectory()
        settings.MEDIA_ROOT = cls.temp_media_dir.name

        # create the files we'll use for testing
        # uploads files (those created in uploads API)
        cls.absolute_uploads_file = get_upload_path('test_uploads.txt')
        cls.uploads_file = os.path.relpath(cls.absolute_uploads_file, settings.MEDIA_ROOT)
        os.makedirs(os.path.dirname(cls.absolute_uploads_file), exist_ok=True)
        with open(cls.absolute_uploads_file, 'w') as f:
            f.write('Hello world')

        # buildingsync file
        upload_to = BuildingFile._meta.get_field('file').upload_to
        cls.absolute_bsync_file = os.path.join(settings.MEDIA_ROOT, upload_to, 'test_bsync.xml')
        os.makedirs(os.path.dirname(cls.absolute_bsync_file), exist_ok=True)
        cls.bsync_file = os.path.relpath(cls.absolute_bsync_file, settings.MEDIA_ROOT)
        with open(cls.absolute_bsync_file, 'w') as f:
            f.write('Hello world')

        # analysis output file
        upload_to = AnalysisOutputFile._meta.get_field('file').upload_to
        cls.absolute_analysis_output_file = os.path.join(settings.MEDIA_ROOT, upload_to, 'test_analysis_output.xml')
        os.makedirs(os.path.dirname(cls.absolute_analysis_output_file), exist_ok=True)
        cls.analysis_output_file = os.path.relpath(cls.absolute_analysis_output_file, settings.MEDIA_ROOT)
        with open(cls.absolute_analysis_output_file, 'w') as f:
            f.write('Hello world')

    @classmethod
    def tearDownClass(cls):
        cls.temp_media_dir.cleanup()

    def test_successfully_get_uploads_file_when_user_is_org_member(self):
        # Setup
        # create an import file like we do in uploads API
        # b/c this is for org_a, user_a should be able to access it
        import_record = ImportRecord.objects.create(
            owner=self.user_a,
            last_modified_by=self.user_a,
            super_organization=self.org_a
        )
        ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=os.path.basename(self.uploads_file),
            file=self.absolute_uploads_file
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
            super_organization=self.org_a_sub
        )
        ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=os.path.basename(self.uploads_file),
            file=self.absolute_uploads_file
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
            owner=self.user_a,
            last_modified_by=self.user_a,
            super_organization=self.org_a
        )
        ImportFile.objects.create(
            import_record=import_record,
            uploaded_filename=os.path.basename(self.uploads_file),
            file=self.absolute_uploads_file
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
            property_state=(FakePropertyStateFactory(organization=self.org_a)
                            .get_property_state())
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
            property_state=(FakePropertyStateFactory(organization=self.org_a)
                            .get_property_state())
        )

        # Act
        # check permission for non org user
        is_permitted = check_file_permission(self.user_b, self.bsync_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_successfully_get_analysis_input_file_when_user_is_org_member(self):
        # Setup
        analysis = (FakeAnalysisFactory(organization=self.org_a, user=self.user_a)
                    .get_analysis())

        # create AnalysisInputFile for org_a
        # note we have to create the actual file here instead of in the setUp method
        # because the path is dependent on the analysis ID
        analysis_input_file = AnalysisInputFile.objects.create(
            analysis=analysis,
            content_type=AnalysisInputFile.BUILDINGSYNC
        )
        analysis_input_file.file.save('test.xml', ContentFile(b'Hello World'))
        analysis_input_file.save()

        # Act
        is_permitted = check_file_permission(self.user_a, analysis_input_file.file.name)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_analysis_input_file_when_user_is_not_org_member(self):
        # Setup
        analysis = (FakeAnalysisFactory(organization=self.org_a, user=self.user_a)
                    .get_analysis())

        # create AnalysisInputFile for org_a
        # note we have to create the actual file here instead of in the setUp method
        # because the path is dependent on the analysis ID
        analysis_input_file = AnalysisInputFile.objects.create(
            analysis=analysis,
            content_type=AnalysisInputFile.BUILDINGSYNC
        )
        analysis_input_file.file.save('test.xml', ContentFile(b'Hello World'))
        analysis_input_file.save()

        # Act
        # check permission for user_b, not part of org
        is_permitted = check_file_permission(self.user_b, analysis_input_file.file.name)

        # Assert
        self.assertFalse(is_permitted)

    def test_successfully_get_analysis_output_file_when_user_is_org_member(self):
        # Setup
        # create AnalysisOutputFile for org_a
        analysis = (FakeAnalysisFactory(organization=self.org_a, user=self.user_a)
                    .get_analysis())
        analysis_property_view = FakeAnalysisPropertyViewFactory(
            organization=self.org_a,
            user=self.user_a,
            analysis=analysis
        ).get_analysis_property_view()
        analysis_output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC,
            file=self.absolute_analysis_output_file
        )
        analysis_output_file.analysis_property_views.set([analysis_property_view.id])

        # Act
        is_permitted = check_file_permission(self.user_a, self.analysis_output_file)

        # Assert
        self.assertTrue(is_permitted)

    def test_fails_get_analysis_output_file_when_user_is_not_org_member(self):
        # Setup
        # create AnalysisOutputFile for org_a
        analysis = (FakeAnalysisFactory(organization=self.org_a, user=self.user_a)
                    .get_analysis())
        analysis_property_view = FakeAnalysisPropertyViewFactory(
            organization=self.org_a,
            user=self.user_a,
            analysis=analysis
        ).get_analysis_property_view()
        analysis_output_file = AnalysisOutputFile.objects.create(
            content_type=AnalysisOutputFile.BUILDINGSYNC,
            file=self.absolute_analysis_output_file
        )
        analysis_output_file.analysis_property_views.set([analysis_property_view.id])

        # Act
        # check permission for user_b, not part of org
        is_permitted = check_file_permission(self.user_b, self.analysis_output_file)

        # Assert
        self.assertFalse(is_permitted)

    def test_fails_when_path_doesnt_match(self):
        # test import files
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(
                self.user_a,
                'uploads/bogus.txt'
            )

        # test buildingsync files
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(
                self.user_a,
                'buildingsync_files/bogus.txt'
            )

        # test analysis input files
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(
                self.user_a,
                'analysis_input_files/bogus/bogus.txt'
            )

        # test analysis output files
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(
                self.user_a,
                'analysis_output_files/bogus.txt'
            )

        # test bad path
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(
                self.user_a,
                '/super-secret/file.txt'
            )

        # test bad path
        with self.assertRaises(ModelForFileNotFound):
            check_file_permission(self.user_a, '')
