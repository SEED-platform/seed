"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from post_office import mail

from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate, PropertyState, TaxLotState
from seed.serializers.postoffice import PostOfficeEmailSerializer, PostOfficeSerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgModelViewSet


@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="create",
)
@extend_schema_org_query_param
class PostOfficeViewSet(SEEDOrgModelViewSet):
    """Email templates of an organization"""

    model = PostOfficeEmailTemplate
    serializer_class = PostOfficeSerializer
    pagination_class = None

    def get_queryset(self):
        return PostOfficeEmailTemplate.objects.filter(organization_id=self.get_organization(self.request)).order_by("name")

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)


@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_owner"),
    ],
    name="create",
)
@extend_schema_org_query_param
@extend_schema_view(
    create=extend_schema(
        description="Send the template's email to the owner of each property or tax lot state, recording each sent email. "
        "Responds with the last recorded email.",
        request=AutoSchemaHelper.json_body(
            {"from_email": "string", "template_id": "integer", "inventory_id": ["integer"], "inventory_type": "string"},
            required=["from_email", "template_id"],
            description="""
                - from_email: required by validation, but replaced by the server's email address
                - template_id: ID of the email template to send
                - inventory_id: IDs of the property or tax lot states whose owners are emailed
                - inventory_type: "properties" for property states; any other value for tax lot states
            """,
        ),
    ),
)
class PostOfficeEmailViewSet(SEEDOrgModelViewSet):
    """Emails sent from an organization's email templates"""

    model = PostOfficeEmail
    serializer_class = PostOfficeEmailSerializer
    pagination_class = None

    def get_queryset(self):
        return PostOfficeEmail.objects.filter(organization_id=self.get_organization(self.request))

    def perform_create(self, serializer):
        template_id = self.request.data.get("template_id")
        inventory_id = self.request.data.get("inventory_id", [])
        if self.request.data.get("inventory_type") == "properties":
            state = PropertyState
            org_filter = "propertyview__property__organization_id"
        else:
            state = TaxLotState
            org_filter = "taxlotview__taxlot__organization_id"

        org_id = self.get_organization(self.request)
        properties = state.objects.filter(id__in=inventory_id, **{org_filter: org_id})

        for prop in properties:  # loop to include details in template
            context = {}
            for key, value in model_to_dict(prop).items():
                context[key] = value
            ptr = mail.send(
                prop.owner_email,
                settings.SERVER_EMAIL,
                template=PostOfficeEmailTemplate.objects.get(id=template_id, organization_id=org_id),
                context=context,
                backend="post_office_backend",
            )

            user = self.request.user

            # Assigning all the fields inside of postoffice to seed_postoffice
            email_data = {
                "email_ptr_id": ptr.id,
                "from_email": settings.SERVER_EMAIL,
                "to": ptr.to,
                "cc": ptr.cc,
                "bcc": ptr.bcc,
                "subject": ptr.subject,
                "message": ptr.message,
                "html_message": ptr.message,
                "status": ptr.status,
                "priority": ptr.priority,
                "created": ptr.created,
                "last_updated": ptr.last_updated,
                "scheduled_time": ptr.scheduled_time,
                "headers": ptr.headers,
                "context": ptr.context,
                "template_id": ptr.template_id,
                "backend_alias": ptr.backend_alias,
                "number_of_retries": ptr.number_of_retries,
                "expires_at": ptr.expires_at,
            }

            # record each email separately, rather than updating (and overwriting the email of) the previously saved record
            serializer.instance = None
            serializer.save(**email_data, organization_id=org_id, user=user)
