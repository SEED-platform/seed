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
        else:
            state = TaxLotState
        properties = state.objects.filter(id__in=inventory_id)
        org_id = self.get_organization(self.request)

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
            ptr.organization_id = org_id
            ptr.user = user
            ptr.template_id = template_id
            ptr.save()
