"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import mimetypes
import os

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.text import get_valid_filename
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
            # there could be more than one file of the same name if the same file was used to import properties and meters
            import_file = ImportFile.objects.filter(file__in=[absolute_filepath, filepath], deleted=False).first()
            if import_file is None:
                raise ModelForFileNotFoundError("ImportFile not found")
        except ImportFile.DoesNotExist:
            raise ModelForFileNotFoundError("ImportFile not found")
        organization = import_file.import_record.super_organization

    elif base_dir == "buildingsync_files":
        try:
            building_file = BuildingFile.objects.filter(file__in=[absolute_filepath, filepath]).first()
            if building_file is None:
                raise ModelForFileNotFoundError("BuildingFile not found")
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
            analysis_output_file = AnalysisOutputFile.objects.filter(file__in=[absolute_filepath, filepath]).first()
            if analysis_output_file is None:
                raise ModelForFileNotFoundError("AnalysisOutputFile not found")
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
            inventory_document = InventoryDocument.objects.filter(file__in=[absolute_filepath, filepath]).first()
            if inventory_document is None:
                raise ModelForFileNotFoundError("InventoryDocument not found")
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

        if not user_has_permission:
            return HttpResponse(status=404)

        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        absolute_filepath = os.path.join(settings.MEDIA_ROOT, filepath)

        if not os.path.exists(absolute_filepath):
            return HttpResponse(status=404)

        # Serve file through Django
        with open(absolute_filepath, "rb") as f:
            file_data = f.read()

        content_type, _ = mimetypes.guess_type(filename)
        response = HttpResponse(file_data, content_type=content_type or "application/octet-stream")

        if ext != ".html":
            safe_download_name = get_valid_filename(filename)
            response["Content-Disposition"] = f'attachment; filename="{safe_download_name}"'

        return response
