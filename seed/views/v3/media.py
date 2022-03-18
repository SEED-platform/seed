import logging
import os
import re

from django.conf import settings
from django.http import HttpResponse
from rest_framework import generics

from seed.models import ImportFile, Organization, BuildingFile, Analysis, AnalysisOutputFile
from seed.utils.api import OrgMixin


# Get an instance of a logger
logger = logging.getLogger(__name__)


class ModelForFileNotFound(Exception):
    pass


def check_file_permission(user, filepath):
    """Return true if the user has access to a media file, false otherwise.
    Raises ModelForFileNotFound when unable to locate an organization for the file

    :param user: SEEDUser
    :param filepath: string, path to the file relative to MEDIA_ROOT
    """
    absolute_filepath = os.path.join(settings.MEDIA_ROOT, filepath)
    filepath_parts = filepath.split('/')
    base_dir = filepath_parts[0]
    organization = None
    if base_dir == 'uploads':
        try:
            import_file = ImportFile.objects.get(
                file__in=[absolute_filepath, filepath],
                deleted=False
            )
        except ImportFile.DoesNotExist:
            raise ModelForFileNotFound('ImportFile not found')
        organization = import_file.import_record.super_organization

    elif base_dir == 'buildingsync_files':
        try:
            building_file = BuildingFile.objects.get(file__in=[absolute_filepath, filepath])
        except BuildingFile.DoesNotExist:
            raise ModelForFileNotFound('BuildingFile not found')
        organization = building_file.property_state.organization

    elif base_dir == 'analysis_input_files':
        try:
            _, analysis_id, _ = filepath_parts
            analysis = Analysis.objects.get(id=analysis_id)
        except ValueError:
            raise ModelForFileNotFound('File path for analysis_input_file was an unexpected structure')
        except Analysis.DoesNotExist:
            return ModelForFileNotFound('Analysis for AnalysisInputFile not found')
        organization = analysis.organization

    elif base_dir == 'analysis_output_files':
        try:
            analysis_output_file = AnalysisOutputFile.objects.get(file__in=[absolute_filepath, filepath])
            analysis_property_view = analysis_output_file.analysis_property_views.first()
            if analysis_property_view is None:
                raise ModelForFileNotFound(f'AnalysisOutputFile "{analysis_output_file.id}" has no property views to validate the org.')
        except AnalysisOutputFile.DoesNotExist:
            raise ModelForFileNotFound('AnalysisOutputFile not found')
        organization = analysis_property_view.cycle.organization
    else:
        raise ModelForFileNotFound(f'Base directory for media file is not currently handled: "{base_dir}"')

    assert organization is not None

    try:
        user.orgs.get(pk=organization.id)
    except Organization.DoesNotExist:
        try:
            user.orgs.get(pk=organization.get_parent().id)
        except Organization.DoesNotExist:
            return False

    return True


class MediaViewSet(generics.RetrieveAPIView, OrgMixin):
    def retrieve(self, request, filepath):
        filepath = os.path.normpath(filepath)
        try:
            user_has_permission = check_file_permission(request.user, filepath)
        except ModelForFileNotFound as e:
            logger.debug(f'Failed to locate organization for file: {str(e)}')
            return HttpResponse(status=404)

        if user_has_permission:
            # Attempt to remove NamedTemporaryFile suffix
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            pattern = re.compile('(.*?)(_[a-zA-Z0-9]{7})$')
            match = pattern.match(name)
            if match:
                filename = match.groups()[0] + ext

            response = HttpResponse()
            if ext != '.html':
                response['Content-Disposition'] = f'attachment; filename={filename}'
            response['X-Accel-Redirect'] = f'/protected/{filepath}'
            return response
        else:
            # 404 instead of 403 to avoid leaking information
            return HttpResponse(status=404)
