"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.contrib.auth import SESSION_KEY, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django_otp.plugins.otp_email.models import EmailDevice
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_400_BAD_REQUEST

from seed.decorators import ajax_request
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import PERMS, has_perm
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, AccessLevelInstance, Organization, OrganizationUser
from seed.lib.superperms.orgs.permissions import get_org_or_id
from seed.models.data_quality import Rule
from seed.tasks import invite_to_seed
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.organizations import create_organization
from seed.utils.users import get_role_from_js

_log = logging.getLogger(__name__)


def _get_js_rule_type(data_type):
    """return the JS friendly data type name for the data data_quality rule

    :param data_type: data data_quality rule data type as defined in data_quality.models
    :returns: (string) JS data type name
    """
    return dict(Rule.DATA_TYPES).get(data_type)


def _get_rule_type_from_js(data_type):
    """return the Rules TYPE from the JS friendly data type

    :param data_type: 'string', 'number', 'date', or 'year'
    :returns: int data type as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.DATA_TYPES).items()}
    return d.get(data_type)


def _get_js_rule_severity(severity):
    """return the JS friendly severity name for the data data_quality rule

    :param severity: data data_quality rule severity as defined in data_quality.models
    :returns: (string) JS severity name
    """
    return dict(Rule.SEVERITY).get(severity)


def _get_severity_from_js(severity):
    """return the Rules SEVERITY from the JS friendly severity

    :param severity: 'error', or 'warning'
    :returns: int severity as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.SEVERITY).items()}
    return d.get(severity)


class EmailAndIDSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)
    user_id = serializers.IntegerField()


@extend_schema_serializer(many=False)
class ListUsersResponseSerializer(serializers.Serializer):
    users = EmailAndIDSerializer(many=True)


# the role names accepted by `get_role_from_js`
role_enum = tuple((role, role) for role in ("viewer", "member", "owner"))

# this is used for swagger docs for some views below
user_response_schema = AutoSchemaHelper.schema_factory(
    {
        "first_name": "string",
        "last_name": "string",
        "email": "string",
        "username": "string",
        "api_key": "string",
        "is_superuser": "boolean",
        "id": "integer",
        "pk": "integer",
        "two_factor_method": tuple((method, method) for method in ("disabled", "email", "token")),
        "org_id": "integer",
        "org_name": "string",
        "org_role": "string",
        "ali_name": "string",
        "ali_id": "integer",
        "is_ali_root": "boolean",
        "is_ali_leaf": "boolean",
        "org_user_id": "integer",
        "settings": "object",
    },
    description="The user and their default organization; the organization fields are empty strings if the user has no organization",
)

status_response_schema = AutoSchemaHelper.schema_factory({"status": "string"})


class UserViewSet(viewsets.ViewSet, OrgMixin):
    raise_exception = True
    # only used to type the `id` path parameter in the API schema
    queryset = User.objects.none()

    def validate_request_user(self, pk, request):
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return False, JsonResponse(
                {"status": "error", "message": "Could not find user with pk = " + str(pk)}, status=status.HTTP_404_NOT_FOUND
            )
        if user != request.user:
            return False, JsonResponse(
                {"status": "error", "message": "Cannot access user with pk = " + str(pk)}, status=status.HTTP_403_FORBIDDEN
            )
        return True, user

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(
                required=False, description="Existing organization to add the user to (required unless a superuser provides `org_name`)"
            )
        ],
        request=AutoSchemaHelper.json_body(
            {
                "org_name": "string",
                "first_name": "string",
                "last_name": "string",
                "role": role_enum,
                "email": "string",
                "access_level_instance_id": "integer",
            },
            required=["first_name", "last_name", "email"],
            description="An object containing meta data for a new user:\n"
            "-org_name: New organization name if creating a new organization for this user (superusers only, instead of `organization_id`)\n"
            "-first_name: First name of new user\n"
            "-last_name: Last name of new user\n"
            "-role: one of owner, member, or viewer (default owner)\n"
            "-email: Email address of the new user\n"
            "-access_level_instance_id: Access level instance of the user in the existing organization (required with `organization_id`)",
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "message": "string",
                    "org": "string",
                    "org_created": "boolean",
                    "username": "string",
                    "user_id": "integer",
                },
                description="Properties:\n"
                "-org: name of new org (or existing org)\n"
                "-org_created: true if new org created\n"
                "-username: username of new user\n"
                "-user_id: user id (pk) of new user",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner_or_superuser_without_org", False),
        ]
    )
    def create(self, request):
        """
        Creates a new SEED user.
        Organization owners must specify the `organization_id` query param.
        Superusers can add `org_name` to the body and create a new organization for the new user.
        Sends invitation email to the new user.
        """
        # WARNING: we aren't using the OrgMixin here to validate the organization
        # It is assumed the org authorization logic implemented in this view is
        # consistent with our permissions checking (has_perm decorator)
        body = request.data
        org_name = body.get("org_name")
        # Resolve the org from the query params exactly as `has_perm` does, so that it is the org that was authorized
        org_id = get_org_or_id(request.query_params)
        if (org_name and org_id) or (not org_name and not org_id):
            return JsonResponse(
                {"status": "error", "message": "Choose either an existing org or provide a new one"}, status=status.HTTP_409_CONFLICT
            )
        # `has_perm` also authorizes owners by a body `organization_id`, but only superusers can create organizations here
        if org_name and not request.user.is_superuser:
            return JsonResponse(
                {"status": "error", "message": "Only superusers can create a new organization"}, status=status.HTTP_403_FORBIDDEN
            )

        first_name = body["first_name"]
        last_name = body["last_name"]
        email = body["email"]
        username = body["email"]
        access_level_instance_id = body.get("access_level_instance_id")

        # Validate the request before creating anything, so that rejected requests do not leave users or orgs behind
        try:
            role = get_role_from_js(body.get("role", "owner"))
        except Exception:
            return JsonResponse(
                {"status": "error", "message": "valid arguments for role are [viewer, member, owner]"}, status=status.HTTP_400_BAD_REQUEST
            )

        if org_id:
            org = Organization.objects.get(pk=org_id)
            org_created = False
            if access_level_instance_id is None:
                return JsonResponse(
                    {"status": "error", "message": "if using an existing org, you must provide a `access_level_instance_id`"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not AccessLevelInstance.objects.filter(organization=org, pk=access_level_instance_id).exists():
                return JsonResponse({"status": "error", "message": "No such access_level_instance"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(username=username.lower())

        if not org_id:
            org, _, _ = create_organization(user, org_name)
            access_level_instance_id = AccessLevelInstance.objects.get(organization=org, depth=1).id
            org_created = True

        # Add the user to the org.  If this is the org's first user,
        # the user becomes the owner/admin automatically.
        # see Organization.add_member()

        if not org.is_member(user):
            try:
                org.add_member(user, access_level_instance_id, role)
            except IntegrityError as e:
                if created:
                    user.delete()
                return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if created:
            user.set_unusable_password()
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            if org.require_2fa:
                EmailDevice.objects.create(user=user, name="default")
        user.save()

        try:
            domain = request.get_host()
        except Exception:
            domain = "seed-platform.org"
        invite_to_seed(domain, user.email, default_token_generator.make_token(user), org, user.pk, first_name)

        return JsonResponse(
            {
                "status": "success",
                "message": user.email,
                "org": org.name,
                "org_created": org_created,
                "username": user.username,
                "user_id": user.id,
            }
        )

    @extend_schema(
        responses={
            200: ListUsersResponseSerializer,
        }
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_superuser", False),
        ]
    )
    def list(self, request):
        """
        Retrieves all users' email addresses and IDs.
        Only usable by superusers.
        """
        users = []
        for user in User.objects.only("id", "email"):
            users.append({"email": user.email, "user_id": user.id})
        return JsonResponse({"users": users})

    @extend_schema(responses={200: user_response_schema})
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    @action(detail=False, methods=["GET"])
    def current(self, request):
        """
        Returns the current user, including the id (primary key) to allow it
        to be passed to other user related endpoints
        """

        return JsonResponse(request.user.serialize())

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(
            {
                "role": role_enum,
            },
            required=["role"],
            description="new role for user",
        ),
        responses={200: status_response_schema},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def role(self, request, pk=None):
        """
        Updates a user's role within an organization.
        """
        body = request.data
        role = get_role_from_js(body["role"])

        user_id = int(pk)
        organization_id = self.get_organization(request)

        requester = OrganizationUser.objects.get(user=request.user, organization_id=organization_id)

        try:
            user = OrganizationUser.objects.get(user_id=user_id, organization_id=organization_id)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "no relationship to organization"}, status=status.HTTP_400_BAD_REQUEST)

        # Non-superuser members can only change their own role, and it must have the same or less permissions
        if requester.role_level == ROLE_MEMBER and not requester.user.is_superuser and (requester.user_id != user_id or role > ROLE_MEMBER):
            return JsonResponse(
                {"status": "error", "message": "members can only change their own role to viewer"}, status=status.HTTP_403_FORBIDDEN
            )

        is_last_owner = (
            not OrganizationUser.objects.filter(
                organization_id=organization_id,
                role_level=ROLE_OWNER,
            )
            .exclude(user_id=user_id)
            .exists()
        )

        if is_last_owner:
            return JsonResponse(
                {"status": "error", "message": "an organization must have at least one owner"}, status=status.HTTP_409_CONFLICT
            )

        if role == ROLE_OWNER and user.access_level_instance != user.organization.root:
            return JsonResponse({"status": "error", "message": "Owners must belong to the root ali."}, status=status.HTTP_400_BAD_REQUEST)

        user.role_level = role
        user.save()

        return JsonResponse({"status": "success"})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body({"access_level_instance_id": "integer"}, required=["access_level_instance_id"]),
        responses={200: status_response_schema},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def access_level_instance(self, request, pk=None):
        """
        Updates a user's access level instance within an organization.
        """
        user_id = int(pk)
        organization_id = self.get_organization(request)

        # get user
        try:
            user = OrganizationUser.objects.get(user_id=user_id, organization_id=organization_id)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such user"}, status=status.HTTP_400_BAD_REQUEST)

        # get ali
        access_level_instance_id = request.data.get("access_level_instance_id")
        if access_level_instance_id is None:
            return JsonResponse({"status": "error", "message": "Must be an `access_level_instance_id`"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            access_level_instance = AccessLevelInstance.objects.get(organization_id=organization_id, id=access_level_instance_id)
        except AccessLevelInstance.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such access_level_instance"}, status=status.HTTP_400_BAD_REQUEST)
        if user.role_level == ROLE_OWNER and access_level_instance != user.organization.root:
            return JsonResponse({"status": "error", "message": "Owners must belong to the root ali."}, status=status.HTTP_400_BAD_REQUEST)

        # set user ali
        user.access_level_instance = access_level_instance
        user.save()

        return JsonResponse({"status": "success"})

    @extend_schema(
        responses={
            200: user_response_schema,
        }
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    def retrieve(self, request, pk=None):
        """
        Retrieves user's first_name, last_name, email
        and api key if exists by user ID (pk). Users can only retrieve themselves.
        """

        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content

        return JsonResponse(user.serialize())

    @extend_schema(
        request=None,
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "api_key": "string"})},
    )
    @method_decorator(
        [
            ajax_request,
        ]
    )
    @action(detail=True, methods=["POST"])
    def generate_api_key(self, request, pk=None):
        """
        Generates a new API key for the current user
        """
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content
        user.generate_key()
        return {"status": "success", "api_key": User.objects.get(pk=pk).api_key}

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"first_name": "string", "last_name": "string", "email": "string"},
            required=["first_name", "last_name", "email"],
            description="An object containing meta data for a updated user",
        ),
        responses={
            200: user_response_schema,
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    def update(self, request, pk=None):
        """
        Updates the user's first name, last name, and email
        """
        body = request.data
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content
        json_user = body
        email = json_user.get("email")
        if not email or json_user.get("first_name") is None or json_user.get("last_name") is None:
            return JsonResponse(
                {"status": "error", "message": "first_name, last_name, and email are required"}, status=status.HTTP_400_BAD_REQUEST
            )
        # the email is also the (unique) username
        if User.objects.filter(username=email.lower()).exclude(pk=user.pk).exists():
            return JsonResponse({"status": "error", "message": "A user with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)
        user.first_name = json_user.get("first_name")
        user.last_name = json_user.get("last_name")
        user.email = email
        user.username = email.lower()
        user.save()
        return JsonResponse(user.serialize())

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {
                "current_password": "string",
                "password_1": "string",
                "password_2": "string",
            },
            required=["current_password", "password_1", "password_2"],
            description="Fill in the current and new matching passwords",
        ),
        responses={200: status_response_schema},
    )
    @method_decorator(
        [
            ajax_request,
        ]
    )
    @action(detail=True, methods=["PUT"])
    def set_password(self, request, pk=None):
        """
        sets/updates a user's password, follows the min requirement of
        django password validation settings in config/settings/common.py
        """
        body = request.data
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content
        current_password = body.get("current_password")
        p1 = body.get("password_1")
        p2 = body.get("password_2")
        if not user.check_password(current_password):
            return JsonResponse({"status": "error", "message": "current password is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        if p1 is None or p1 != p2:
            return JsonResponse({"status": "error", "message": "entered password do not match"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(p2)
        except ValidationError as e:
            return JsonResponse({"status": "error", "message": e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(p1)
        user.save()
        # Keep the user logged in to their current session (JWT and API key callers have no session to update)
        if request.session.get(SESSION_KEY) == str(user.pk):
            update_session_auth_hash(request, user)
        return JsonResponse({"status": "success"})

    @method_decorator(
        [
            ajax_request,
        ]
    )
    def get_actions(self, request):
        """returns all actions"""
        return {
            "status": "success",
            "actions": list(PERMS.keys()),
        }

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(
            {
                "actions": ["string"],
            },
            description="A list of actions to check: examples include (requires_parent_org_owner, "
            "requires_owner, requires_member, requires_viewer, "
            "requires_superuser, can_create_sub_org, can_remove_org)",
            required=["actions"],
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "auth": "object"},
                description="`auth` maps each requested action name to whether the user is authorized for it",
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
        ]
    )
    @action(detail=True, methods=["POST"])
    def is_authorized(self, request, pk=None):
        """
        Checks the auth for a given action, if user is the owner of the parent
        org then True is returned for each action
        """
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content

        actions, org, error, message = self._parse_is_authenticated_params(request)
        if error:
            return JsonResponse({"status": "error", "message": message}, status=status.HTTP_400_BAD_REQUEST)

        # If the only action requested is 'requires_superuser' no need to check an org affiliation
        if len(actions) == 1 and actions[0] == "requires_superuser":
            return JsonResponse({"status": "success", "auth": {"requires_superuser": user.is_superuser}})

        auth = self._try_parent_org_auth(user, org, actions)
        if auth:
            return JsonResponse({"status": "success", "auth": auth})

        try:
            ou = OrganizationUser.objects.get(user=user, organization=org)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "user does not exist"})

        # like `has_perm`, unknown actions are not authorized
        auth = {action: PERMS.get(action, lambda _: False)(ou) for action in actions}
        return JsonResponse({"status": "success", "auth": auth})

    def _parse_is_authenticated_params(self, request):
        """checks if the org exists and if the actions are present

        :param request: the request
        :returns: tuple (actions, org, error, message)
        """
        error = False
        message = ""
        body = request.data
        if not body.get("actions"):
            message = "no actions to check"
            error = True

        # WARNING: we aren't using the OrgMixin here to validate the organization
        # It is assumed the org authorization logic implemented here is sufficient
        org_id = request.query_params.get("organization_id", None)
        if org_id == "":
            message = "organization id is undefined"
            error = True
            org = None
        else:
            try:
                org = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist:
                message = "organization does not exist"
                error = True
                org = None

        return body.get("actions"), org, error, message

    def _try_parent_org_auth(self, user, organization, actions):
        """checks the parent org for permissions, if the user is not the owner of
        the parent org, then None is returned.

        :param user: the request user
        :param organization: org to check its parent
        :param actions: list of str actions to check
        :returns: a dict of action permission resolutions or None
        """
        try:
            ou = OrganizationUser.objects.get(user=user, organization=organization.parent_org, role_level=ROLE_OWNER)
        except OrganizationUser.DoesNotExist:
            return None

        return {action: PERMS["requires_owner"](ou) for action in actions}

    @extend_schema(responses={200: AutoSchemaHelper.schema_factory({"status": "string", "show_shared_buildings": "boolean"})})
    @method_decorator(
        [
            ajax_request,
        ]
    )
    @action(detail=True, methods=["GET"])
    def shared_buildings(self, request, pk=None):
        """
        Get the request user's ``show_shared_buildings`` attr
        """
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content

        return JsonResponse(
            {
                "status": "success",
                "show_shared_buildings": user.show_shared_buildings,
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=None,
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "user": {"id": "integer", "access_level_instance": {"id": "integer", "name": "string"}}},
                description="`user.id` is the ID of the user's membership (OrganizationUser) in the new default organization",
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def default_organization(self, request, pk=None):
        """
        Sets the user's default organization
        """
        ok, content = self.validate_request_user(pk, request)
        if ok:
            user = content
        else:
            return content
        user.default_organization_id = self.get_organization(request)
        user.save()

        ou = OrganizationUser.objects.get(user=user, organization_id=user.default_organization_id)
        return {
            "status": "success",
            "user": {
                "id": ou.id,
                "access_level_instance": {
                    "id": ou.access_level_instance.id,
                    "name": ou.access_level_instance.name,
                },
            },
        }

    @extend_schema(
        request=None,
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "data": "string"}, description="`data` is the deactivated user's email"
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_superuser", False),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def deactivate(self, request, pk=None):
        """
        Deactivates a user. This action can only be performed by superusers
        """
        try:
            user_id = pk
            user = User.objects.get(id=user_id)
            user.deactivate_user()
            return JsonResponse({"status": "successfully deactivated", "data": user.email})
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "data": str(e),
                },
                status=HTTP_400_BAD_REQUEST,
            )
