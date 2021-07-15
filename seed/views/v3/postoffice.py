# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

"""
from django.conf import settings
from django.forms.models import model_to_dict

from seed.serializers.postoffice import PostOfficeSerializer, PostOfficeEmailSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet
from seed.models import PropertyState, TaxLotState
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate
from post_office import mail


class PostOfficeViewSet(SEEDOrgModelViewSet):
    model = PostOfficeEmailTemplate
    serializer_class = PostOfficeSerializer
    pagination_class = None

    def get_queryset(self):
        return PostOfficeEmailTemplate.objects.filter(
            organization_id=self.get_organization(self.request)
        ).order_by('name')

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)


class PostOfficeEmailViewSet(SEEDOrgModelViewSet):
    model = PostOfficeEmail
    serializer_class = PostOfficeEmailSerializer
    pagination_class = None

    def get_queryset(self):
        return PostOfficeEmail.objects.all()

    def perform_create(self, serializer):
        template_id = self.request.data.get('template_id')
        inventory_id = self.request.data.get('inventory_id', [])
        if self.request.data.get('inventory_type') == "properties":
            state = PropertyState
            org_filter = 'propertyview__property__organization_id'
        else:
            state = TaxLotState
            org_filter = 'taxlotview__taxlot__organization_id'

        org_id = self.get_organization(self.request)
        properties = state.objects.filter(
            id__in=inventory_id,
            **{org_filter: org_id}
        )

        for prop in properties:  # loop to include details in template
            context = {}
            for key, value in model_to_dict(prop).items():
                context[key] = value
            ptr = mail.send(
                prop.owner_email,
                settings.SERVER_EMAIL,
                template=PostOfficeEmailTemplate.objects.get(id=template_id, organization_id=org_id),
                context=context,
                backend='post_office_backend'
            )

            user = self.request.user

            # Assigning all the fields inside of postoffice to seed_postoffice
            email_data = {
                'email_ptr_id': ptr.id,
                'from_email': settings.SERVER_EMAIL,
                'to': ptr.to,
                'cc': ptr.cc,
                'bcc': ptr.bcc,
                'subject': ptr.subject,
                'message': ptr.message,
                'html_message': ptr.message,
                'status': ptr.status,
                'priority': ptr.priority,
                'created': ptr.created,
                'last_updated': ptr.last_updated,
                'scheduled_time': ptr.scheduled_time,
                'headers': ptr.headers,
                'context': ptr.context,
                'template_id': ptr.template_id,
                'backend_alias': ptr.backend_alias,
                'number_of_retries': ptr.number_of_retries,
                'expires_at': ptr.expires_at
            }

            serializer.save(**email_data, organization_id=org_id, user=user)
