"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import os
import re

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework import generics

from seed.models import Analysis, AnalysisOutputFile, BuildingFile, ImportFile, InventoryDocument, Organization
from seed.utils.api import OrgMixin, api_endpoint

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ModelForFileNotFoundError(Exception):
    pass


def check_file_permission(user, filepath):
    """Return true if the user has access to a media file, false otherwise.
    Raises ModelForFileNotFound when unable to locate an organization for the file

    :param user: SEEDUser
    :param filepath: string, path to the file relative to MEDIA_ROOT
    """
    absolute_filepath = os.path.join(settings.MEDIA_ROOT, filepath)
    filepath_parts = filepath.split("/")
    base_dir = filepath_parts[0]
    organization = None
    if base_dir == "uploads":
        try:
            import_file = ImportFile.objects.get(file__in=[absolute_filepath, filepath], deleted=False)
        except ImportFile.DoesNotExist:
            raise ModelForFileNotFoundError("ImportFile not found")
        organization = import_file.import_record.super_organization

    elif base_dir == "buildingsync_files":
        try:
            building_file = BuildingFile.objects.get(file__in=[absolute_filepath, filepath])
        except BuildingFile.DoesNotExist:
            raise ModelForFileNotFoundError("BuildingFile not found")
        organization = building_file.property_state.organization

    elif base_dir == "analysis_input_files":
        try:
            _, analysis_id, _ = filepath_parts
            analysis = Analysis.objects.get(id=analysis_id)
        except ValueError:
            raise ModelForFileNotFoundError("File path for analysis_input_file was an unexpected structure")
        except Analysis.DoesNotExist:
            return ModelForFileNotFoundError("Analysis for AnalysisInputFile not found")
        organization = analysis.organization

    elif base_dir == "analysis_output_files":
        try:
            analysis_output_file = AnalysisOutputFile.objects.get(file__in=[absolute_filepath, filepath])
            analysis_property_view = analysis_output_file.analysis_property_views.first()
            if analysis_property_view is None:
                raise ModelForFileNotFoundError(
                    f'AnalysisOutputFile "{analysis_output_file.id}" has no property views to validate the org.'
                )
        except AnalysisOutputFile.DoesNotExist:
            raise ModelForFileNotFoundError("AnalysisOutputFile not found")
        organization = analysis_property_view.cycle.organization

    elif base_dir == "inventory_documents":
        try:
            inventory_document = InventoryDocument.objects.get(file__in=[absolute_filepath, filepath])
        except InventoryDocument.DoesNotExist:
            raise ModelForFileNotFoundError("InventoryDocument not found")
        organization = inventory_document.property.organization
    else:
        raise ModelForFileNotFoundError(f'Base directory for media file is not currently handled: "{base_dir}"')

    if not organization:
        raise ValueError("Organization could not be determined")

    try:
        user.orgs.get(pk=organization.id)
    except Organization.DoesNotExist:
        try:
            user.orgs.get(pk=organization.get_parent().id)
        except Organization.DoesNotExist:
            return False

    return True


class MediaViewSet(generics.RetrieveAPIView, OrgMixin):
    @method_decorator(
        api_endpoint,
    )
    def retrieve(self, request, filepath):
        filepath = os.path.normpath(filepath)
        try:
            user_has_permission = check_file_permission(request.user, filepath)
        except ModelForFileNotFoundError as e:
            logger.debug(f"Failed to locate organization for file: {e!s}")
            return HttpResponse(status=404)

        if user_has_permission:
            # Attempt to remove NamedTemporaryFile suffix
            filename = os.path.basename(filepath)
            name, ext = os.path.splitext(filename)
            pattern = re.compile("(.*?)(_[a-zA-Z0-9]{7})$")
            match = pattern.match(name)
            if match:
                filename = match.groups()[0] + ext

            response = HttpResponse()
            if ext != ".html":
                response["Content-Disposition"] = f"attachment; filename={filename}"
            response["X-Accel-Redirect"] = f"/protected/{filepath}"
            return response
        else:
            # 404 instead of 403 to avoid leaking information
            return HttpResponse(status=404)
