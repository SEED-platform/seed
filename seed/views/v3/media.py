"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
import mimetypes
import os

from django.conf import settings
from django.db.models.expressions import RawSQL
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.utils.text import get_valid_filename
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics

from seed.lib.superperms.orgs.decorators import ALLOW_SUPER_USER_PERMS
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models import Analysis, BuildingFile, ImportFile, InventoryDocument, PropertyView
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper, EmptySerializer

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ModelForFileNotFoundError(Exception):
    pass


def get_user_access_level_instance(user, organization):
    """Return the user's access level instance in the organization, or None if they have no access to it.
    As in `has_perm`, superusers get the root. Root members of a parent organization also get the root of its
    sub-organizations.

    :param user: SEEDUser
    :param organization: Organization
    """
    if user.is_superuser and ALLOW_SUPER_USER_PERMS:
        return organization.root

    # Ignore memberships whose access level instance belongs to another organization
    org_user = (
        OrganizationUser.objects.filter(user=user, organization=organization, access_level_instance__organization=organization)
        .select_related("access_level_instance")
        .first()
    )
    if org_user is not None:
        return org_user.access_level_instance

    parent_org_id = organization.parent_org_id
    if (
        parent_org_id is not None
        and OrganizationUser.objects.filter(
            user=user, organization_id=parent_org_id, access_level_instance__organization_id=parent_org_id, access_level_instance__depth=1
        ).exists()
    ):
        return organization.root

    return None


def _get_property_state_owners(property_state):
    """Return (organization, access level instance) pairs for the properties a state's data belongs to.
    Files stay on the state they were added to, so follow edits and merges in the audit log forward to the states
    that properties currently use.

    :param property_state: PropertyState
    """
    organization = property_state.organization
    # The state and its descendants in the audit log, in one query however many edits and merges follow it (e.g., for
    # each file in a property's history). UNION, unlike UNION ALL, skips states already found, so a cycle in the audit
    # log ends the recursion.
    descendant_state_ids = RawSQL(
        """
        WITH RECURSIVE descendants(state_id) AS (
            SELECT %s
            UNION
            SELECT log.state_id
            FROM seed_propertyauditlog log
            JOIN descendants ON log.parent_state1_id = descendants.state_id OR log.parent_state2_id = descendants.state_id
        )
        SELECT state_id FROM descendants
        """,
        [property_state.id],
    )
    views = PropertyView.objects.filter(state_id__in=descendant_state_ids, property__organization=organization).select_related(
        "property__access_level_instance"
    )
    owners = [(organization, view.property.access_level_instance) for view in views]
    if not any(view.state_id == property_state.id for view in views):
        # e.g., imported and merged-away states have no view, and so no access level instance below the root
        owners.append((organization, organization.root))
    return owners


def _get_file_owners(base_dir, filepath_parts, candidate_paths):
    """Return (organization, access level instance) pairs for every record that references a media file.
    Raises ModelForFileNotFoundError when no record references it
    """
    if base_dir == "uploads":
        model_name = "ImportFile"
        # there could be more than one file of the same name if the same file was used to import properties and meters
        import_files = ImportFile.objects.filter(
            file__in=candidate_paths, deleted=False, import_record__super_organization__isnull=False
        ).select_related("import_record__super_organization", "import_record__access_level_instance")
        owners = [(f.import_record.super_organization, f.import_record.access_level_instance) for f in import_files]

    elif base_dir == "buildingsync_files":
        model_name = "BuildingFile"
        building_files = BuildingFile.objects.filter(file__in=candidate_paths, property_state__isnull=False).select_related(
            "property_state__organization"
        )
        owners = [owner for building_file in building_files for owner in _get_property_state_owners(building_file.property_state)]

    elif base_dir == "analysis_input_files":
        model_name = "Analysis for AnalysisInputFile"
        try:
            # the analysis ID is a directory in the path (see `analysis_input_path`)
            _, analysis_id, _ = filepath_parts
            analysis_id = int(analysis_id)
        except ValueError as e:
            raise ModelForFileNotFoundError("File path for analysis_input_file was an unexpected structure") from e
        analyses = Analysis.objects.filter(id=analysis_id).select_related("organization", "access_level_instance")
        owners = [(analysis.organization, analysis.access_level_instance) for analysis in analyses]

    elif base_dir == "analysis_output_files":
        model_name = "Analysis for AnalysisOutputFile"
        analyses = (
            Analysis.objects.filter(analysispropertyview__analysisoutputfile__file__in=candidate_paths)
            .distinct()
            .select_related("organization", "access_level_instance")
        )
        owners = [(analysis.organization, analysis.access_level_instance) for analysis in analyses]

    elif base_dir == "inventory_documents":
        model_name = "InventoryDocument"
        inventory_documents = InventoryDocument.objects.filter(file__in=candidate_paths, property__isnull=False).select_related(
            "property__organization", "property__access_level_instance"
        )
        owners = [(document.property.organization, document.property.access_level_instance) for document in inventory_documents]

    else:
        raise ModelForFileNotFoundError(f'Base directory for media file is not currently handled: "{base_dir}"')

    if not owners:
        raise ModelForFileNotFoundError(f"{model_name} not found")
    return owners


def check_file_permission(user, filepath):
    """Return true if the user has access to a media file, false otherwise.
    A user has access if any record that references the file is within their access level instance's subtree.
    Raises ModelForFileNotFoundError when no record references the file

    :param user: SEEDUser
    :param filepath: string, path to the file relative to MEDIA_ROOT
    """
    normalized_filepath = filepath.replace("\\", "/")
    absolute_filepath = os.path.join(settings.MEDIA_ROOT, os.path.normpath(normalized_filepath.lstrip("/\\")))
    filepath_parts = normalized_filepath.split("/")
    base_dir = filepath_parts[0]
    candidate_paths = {
        absolute_filepath,
        absolute_filepath.replace("\\", "/"),
        normalized_filepath,
        os.path.normpath(normalized_filepath),
        filepath,
        os.path.normpath(filepath),
    }
    owners = _get_file_owners(base_dir, filepath_parts, candidate_paths)

    user_alis = {}
    for organization, access_level_instance in owners:
        if organization.id not in user_alis:
            user_alis[organization.id] = get_user_access_level_instance(user, organization)
        user_ali = user_alis[organization.id]
        # A record whose access level instance belongs to another organization is inconsistent, so access is denied
        if (
            user_ali is not None
            and access_level_instance.organization_id == organization.id
            and (access_level_instance == user_ali or access_level_instance.is_descendant_of(user_ali))
        ):
            return True

    return False


@extend_schema_view(
    get=extend_schema(
        parameters=[AutoSchemaHelper.path_string_field("filepath", "Path of the file relative to the media root (e.g., uploads/file.csv)")],
        responses={
            (200, "application/octet-stream"): OpenApiResponse(
                OpenApiTypes.BINARY,
                description="The file, with the content type guessed from its name. Files other than HTML analysis"
                " reports are sent as attachments",
            ),
            404: OpenApiResponse(description="The file does not exist or the user does not have access to it"),
        },
    )
)
class MediaViewSet(generics.RetrieveAPIView, OrgMixin):
    queryset = ()
    serializer_class = EmptySerializer

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

        # Only HTML analysis reports are shown in the browser (e.g., in an iframe). Analysis pipelines store them (e.g.,
        # BETTER's, as its API returns them), so members cannot upload them. Other files, like imports and inventory
        # documents, can be uploaded by any member, so displaying one (e.g., HTML or SVG) from the SEED origin could run
        # its scripts as whoever opens it
        base_dir = filepath.replace("\\", "/").split("/")[0]
        if not (base_dir == "analysis_output_files" and ext == ".html"):
            safe_download_name = get_valid_filename(filename)
            response["Content-Disposition"] = f'attachment; filename="{safe_download_name}"'

        return response
