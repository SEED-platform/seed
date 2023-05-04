# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from copy import deepcopy

import django.core.exceptions
from django.db import IntegrityError
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models import StatusLabel as Label
from seed.models.columns import Column
from seed.models.salesforce_configs import SalesforceConfig
from seed.serializers.salesforce_configs import SalesforceConfigSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)
from seed.utils.encrypt import decrypt, encrypt
from seed.utils.salesforce import (
    auto_sync_salesforce_properties,
    schedule_sync,
    test_connection
)


def _validate_data(data, org_id):

    error = False
    msgs = []

    # Indication Label
    i_label_id = data.get('indication_label')
    if i_label_id:
        i_label = Label.objects.get(pk=i_label_id)
        if i_label.super_organization_id != org_id:
            # error, this label does not belong to this org
            error = True
            msgs.append('the selected indication label does not belong to this organization')

    # Violation Label
    v_label_id = data.get('violation_label')
    if v_label_id:
        v_label = Label.objects.get(pk=v_label_id)
        if v_label.super_organization_id != org_id:
            # error, this label does not belong to this org
            error = True
            msgs.append('the selected violation label does not belong to this organization')

    # Compliance Label
    c_label_id = data.get('compliance_label')
    if c_label_id:
        c_label = Label.objects.get(pk=c_label_id)
        if c_label.super_organization_id != org_id:
            # error, this label does not belong to this org
            error = True
            msgs.append('the selected compliance label does not belong to this organization')

    #  Contact Columns
    column_names = ['seed_benchmark_id_column', 'contact_email_column', 'contact_name_column', 'account_name_column']
    for item in column_names:
        c_id = data.get(item)
        if c_id:
            c_col = Column.objects.get(pk=c_id)

            if c_col.organization_id != org_id:
                # error, this column does not belong to this org
                error = True
                msgs.append('The selected column for ' + item + ' does not belong to this organization')

    return error, msgs


class SalesforceConfigViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = SalesforceConfigSerializer
    model = SalesforceConfig

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def list(self, request):
        organization_id = self.get_organization(request)
        salesforce_configs = SalesforceConfig.objects.filter(organization=organization_id)

        s_data = SalesforceConfigSerializer(salesforce_configs, many=True).data
        for item in s_data:
            if 'password' in item and item['password'] is not None:
                item['password'] = decrypt(item['password'])[0]

        return JsonResponse({
            'status': 'success',
            'salesforce_configs': s_data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['POST'])
    def salesforce_connection(self, request):
        """
        Tests connection to Salesforce using passed-in credentials (may not be saved yet)
        """

        self.get_organization(request)

        body = request.data
        # conf = SalesforceConfig.objects.get(pk=pk)
        data = body.get('salesforce_config', None)

        if data is None:
            return JsonResponse({'status': 'error', 'message': 'malformed request'},
                                status=status.HTTP_400_BAD_REQUEST)

        # assume salesforce is enabled if you can get to this view
        # get values from form (they may not be saved yet)
        params = {}
        params['instance_url'] = data.get('url', None)
        params['username'] = data.get('username', None)
        params['password'] = data.get('password', None)
        params['security_token'] = data.get('security_token', None)
        domain = data.get('domain', None)
        if domain:
            params['domain'] = data.get('domain')

        # connect
        status_msg, message, sf = test_connection(params)
        if status_msg is False:
            return JsonResponse({'status': 'error', 'message': message},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse({'status': 'success'})

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=['POST'])
    @has_perm_class('requires_owner')
    def sync(self, request):
        """
        Sync all eligible PropertyViews with Salesforce Benchmark objects.
        Use the saved 'last_update_date' and the configured indication label to determine eligibility
        """
        org_id = self.get_organization(request)
        the_status, messages = auto_sync_salesforce_properties(org_id)

        if the_status:
            return JsonResponse({
                'success': True,
                'status': 'success',
                'message': 'successfully updated Salesforce'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': messages
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def retrieve(self, request, pk=0):
        organization = self.get_organization(request)
        if pk == 0:
            try:
                return JsonResponse({
                    'status': 'success',
                    'salesforce_config': SalesforceConfigSerializer(
                        SalesforceConfig.objects.filter(organization=organization).first()
                    ).data
                }, status=status.HTTP_200_OK)
            except Exception:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No configs exist with this identifier'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                data = SalesforceConfigSerializer(SalesforceConfig.objects.get(id=pk, organization=organization)).data
                if 'password' in data and data['password'] is not None:
                    data['password'] = decrypt(data['password'])[0]
                return JsonResponse({
                    'status': 'success',
                    'salesforce_config': data
                }, status=status.HTTP_200_OK)
            except SalesforceConfig.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'SalesforceConfig with id {pk} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            SalesforceConfig.objects.get(id=pk, organization=organization_id).delete()
        except SalesforceConfig.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'SalesforceConfig with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted SalesforceConfig ID {pk}'
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'indication_label': 'integer',
                'violation_label': 'integer',
                'compliance_label': 'integer',
                'account_rec_type': 'string',
                'contact_rec_type': 'string',
                'last_update_date': 'string',
                'unique_benchmark_id_fieldname': 'string',
                'seed_benchmark_id_fieldname': 'string',
                'url': 'string',
                'username': 'string',
                'password': 'string',
                'security_token': 'string',
                'domain': 'string',
                'cycle_fieldname': 'string',
                'status_fieldname': 'string',
                'labels_fieldname': 'string',
                'contact_email_column': 'integer',
                'contact_name_column': 'integer',
                'account_name_column': 'integer',
                'default_contact_account_name': 'string',
                'logging_email': 'string',
                'benchmark_contact_fieldname': 'string',
                'data_admin_email_column': 'integer',
                'data_admin_name_column': 'integer',
                'data_admin_account_name_column': 'integer',
                'default_data_admin_account_name': 'string',
                'data_admin_contact_fieldname': 'integer',
                'update_at_hour': 'integer',
                'update_at_minute': 'integer',
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):

        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'bad organization_id'},
                                status=status.HTTP_400_BAD_REQUEST)

        data = deepcopy(request.data)
        data.update({'organization_id': org_id})

        # encrypt pwd
        if 'password' in data and data['password']:
            data['password'] = encrypt(data['password'])

        error, msgs = _validate_data(data, org_id)
        if (error is True):
            return JsonResponse({'status': 'error', 'message': ','.join(msgs)},
                                status=status.HTTP_400_BAD_REQUEST)
        serializer = SalesforceConfigSerializer(data=data)

        if not serializer.is_valid():
            error_response = {
                'status': 'error',
                'message': 'Data Validation Error',
                'errors': serializer.errors
            }
            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()

            # setup Salesforce update scheduled tasks
            data['timezone'] = request.GET.get('timezone', None)
            schedule_sync(data, org_id)

            return JsonResponse({
                'status': 'success',
                'salesforce_config': serializer.data
            }, status=status.HTTP_200_OK)
        except IntegrityError:
            return JsonResponse({
                'status': 'error',
                'message': 'Only one Salesforce config can be created per organization'
            }, status=status.HTTP_400_BAD_REQUEST)
        except django.core.exceptions.ValidationError as e:

            message_dict = e.message_dict
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'indication_label': 'integer',
                'violation_label': 'integer',
                'compliance_label': 'integer',
                'account_rec_type': 'string',
                'contact_rec_type': 'string',
                'last_update_date': 'string',
                'unique_benchmark_id_fieldname': 'string',
                'seed_benchmark_id_fieldname': 'string',
                'url': 'string',
                'username': 'string',
                'password': 'string',
                'security_token': 'string',
                'domain': 'string',
                'cycle_fieldname': 'string',
                'status_fieldname': 'string',
                'labels_fieldname': 'string',
                'contact_email_column': 'integer',
                'contact_name_column': 'integer',
                'account_name_column': 'integer',
                'default_contact_account_name': 'string',
                'logging_email': 'string',
                'benchmark_contact_fieldname': 'string',
                'data_admin_email_column': 'integer',
                'data_admin_name_column': 'integer',
                'data_admin_account_name_column': 'integer',
                'default_data_admin_account_name': 'string',
                'data_admin_contact_fieldname': 'integer',
                'update_at_hour': 'integer',
                'update_at_minute': 'integer',
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def update(self, request, pk):
        org_id = self.get_organization(request)

        salesforce_config = None
        try:
            salesforce_config = SalesforceConfig.objects.get(id=pk, organization=org_id)
        except SalesforceConfig.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'SalesforceConfig with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({'organization': org_id})
        if 'password' in data and data['password']:
            data['password'] = encrypt(data['password'])
        error, msgs = _validate_data(data, org_id)
        if (error is True):
            return JsonResponse({'status': 'error', 'message': ','.join(msgs)},
                                status=status.HTTP_400_BAD_REQUEST)

        serializer = SalesforceConfigSerializer(salesforce_config, data=data, partial=True)

        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # setup Salesforce update scheduled tasks (if change detected)
        if data['update_at_hour'] != salesforce_config.update_at_hour or data['update_at_minute'] != salesforce_config.update_at_minute:
            data['timezone'] = request.GET.get('timezone', None)
            schedule_sync(data, org_id)

        try:
            serializer.save()
            # decrypt pwd in response
            return_data = serializer.data
            if 'password' in return_data and return_data['password'] is not None:
                return_data['password'] = decrypt(return_data['password'])[0]

            return JsonResponse({
                'status': 'success',
                'salesforce_config': return_data,
            }, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            # rename key __all__ to general to make it more user friendly
            if '__all__' in message_dict:
                message_dict['general'] = message_dict.pop('__all__')

            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': message_dict,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
