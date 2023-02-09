# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import datetime

from django.utils import timezone
from django.utils.timezone import get_current_timezone
from seed_salesforce.salesforce_client import SalesforceClient

from seed.models import Organization, PropertyView
from seed.models import StatusLabel as Label
from seed.models.columns import Column
from seed.models.salesforce_configs import SalesforceConfig
from seed.models.salesforce_mappings import SalesforceMapping
from seed.serializers.properties import PropertyViewSerializer
from seed.utils.encrypt import decrypt


def test_connection(params):
    """ test Salesforce connection with credentials stored in the salesforce_config model
    """
    status = False
    message = None
    try:
        sf = SalesforceClient(connection_params=params)
        if isinstance(sf, SalesforceClient):
            status = True
        return status, message, sf
    except Exception as e:
        message = " ".join(["Salesforce Authentication Failed:", str(e)])
        return status, message, None


def check_salesforce_enabled(org_id):
    """ check that salesforce process is enabled before synching
    """
    enabled = False
    org = Organization.objects.get(pk=org_id)
    if org.salesforce_enabled:
        enabled = True
    return enabled


def retrieve_connection_params(org_id):
    """ retrieve salesforce connection params from the salesforce_config model by org_id
    """
    params = {}
    try:
        config = SalesforceConfig.objects.filter(organization_id=org_id)
    except Exception as e:
        print('No salesforce configs entered in settings page: ' + e)
        return params

    if len(config) >= 1:
        config = config.first()
        params['instance'] = config.url
        params['username'] = config.username
        params['password'] = decrypt(config.password)[0]
        params['security_token'] = config.security_token
        if config.domain == 'test':
            params['domain'] = config.domain

    return params


def _get_label_names(labels_arr):
    """
    Return a list of the label names associated with a property_view
    """

    labels = []
    if labels_arr:
        labels = list(Label.objects.filter(pk__in=labels_arr).values_list("name", flat=True))

    return labels


def _get_property_view(property_id, org_id):
    """
    Return the property view

    :param property_id: id, The property view ID
    :param org_id: id, the organization ID
    :return:
    """
    try:
        property_view = PropertyView.objects.select_related(
            'property', 'cycle', 'state'
        ).get(
            id=property_id,
            property__organization_id=org_id
        )

        result = {
            'status': 'success',
            'property_view': property_view
        }
    except PropertyView.DoesNotExist:
        result = {
            'status': 'error',
            'message': 'property view with id {} does not exist'.format(property_id)
        }
    return result


def update_salesforce_property(org_id, property_id, salesforce_client=None, config=None, mappings={}):
    """ Sync a specific SEED property record with Salesforce
    """
    status = False
    message = None
    params = {}

    """ INITIALIZATION """
    # if client is initialized, use it, otherwise initialize it
    if salesforce_client is None:
        connection_status, message, salesforce_client = test_connection(retrieve_connection_params(org_id))
        if not connection_status:
            # connection failed
            return connection_status, message

    if config is None:
        # get salesforce config object
        try:
            config = SalesforceConfig.objects.get(organization_id=org_id)
        except Exception:
            message = 'No Salesforce configs found. Configure Salesforce on the organization settings page'
            return status, message

    # retrieve mappings if not initialized
    if len(mappings) == 0:
        mappings = SalesforceMapping.objects.filter(organization_id=org_id)

    # get property view
    result = _get_property_view(property_id, org_id)
    if result.get('status', None) == 'error':
        message = 'Cannot retrieve property view details for: ' + property_id
        return status, message

    property_view = result.pop('property_view')
    result.update(PropertyViewSerializer(property_view).data)
    label_names = _get_label_names(result['labels'])
    result['label_names'] = label_names

    # flatten state / extra_data
    flat_state = {}
    for key, val in result['state'].items():
        if key == 'extra_data':
            for key1, val1 in val.items():
                flat_state[key1] = val1
        else:
            flat_state[key] = val

    """ VALIDATE FIELDS """
    # check a few required fields
    if not config.seed_benchmark_id_column_id:
        message = 'No SEED Benchmark ID Field configured. Configure Salesforce functionality on the organization settings page.'
        return status, message

    if not config.compliance_label_id:
        message = 'No Compliance Label configured. Configure Salesforce functionality on the organization settings page.'
        return status, message

    """ RETRIEVE BENCHMARK ID """
    # grab the benchmark ID from the record
    benchmark_id_colname = Column.objects.get(pk=config.seed_benchmark_id_column_id)

    # we don't know if this will be in extra_data or canonical fields
    benchmark_id = None
    if benchmark_id_colname.display_name is not None and benchmark_id_colname.display_name != "":
        if benchmark_id_colname.display_name in flat_state:
            benchmark_id = flat_state[benchmark_id_colname.display_name]
    else:
        if benchmark_id_colname.column_name in flat_state:
            benchmark_id = flat_state[benchmark_id_colname.column_name]

    # print(f"benchmark ID is: {benchmark_id}")
    if not benchmark_id:
        message = 'SEED Unique Benchmark ID Column data is undefined. Update your property record with this information.'
        return status, message

    """ CONTACT/ACCOUNT CREATION """
    # try to create / update contact and account (if configured)
    # if we want to try to make a contact, we at least need contact email and account name on the Salesforce side
    # NOTE: skipping this if not configured (not erroring out)
    if config.contact_email_column_id and config.account_name_column_id and config.benchmark_contact_fieldname:
        fields = {'email': config.contact_email_column_id,
                  'contact_name': config.contact_name_column_id,
                  'account_name': config.account_name_column_id}
        contact_info = {}
        for key, val in fields.items():
            colname = Column.objects.get(pk=val)
            contact_info[key] = ""
            if colname.display_name and colname.display_name in flat_state:
                contact_info[key] = flat_state[colname.display_name]
            elif colname.column_name in flat_state:
                contact_info[key] = flat_state[colname.column_name]
        try:
            contact_record = salesforce_client.find_contact_by_email(contact_info['email'])
        except Exception as e:
            message = str(e)
            return status, message

        if not contact_record:
            # Create Account first, then Contact (Salesforce Requirement)
            account_record = salesforce_client.find_account_by_name(contact_info['account_name'])
            if not account_record:
                # create account
                a_details = {}
                if config.account_rec_type:
                    a_details['RecordTypeId'] = config.account_rec_type
                try:
                    account_record = salesforce_client.create_account(contact_info['account_name'], **a_details)
                    print(f"created account record: {account_record}")
                except Exception as e:
                    message = str(e)
                    return status, message

            account_id = account_record['Id']
            # Note: Salesforce doesn't seem to allow direct access to the Contact "Name" field
            # but instead concatenates FirstName + LastName to make Name
            # push the Contact Name field into LastName only
            c_details = {'AccountId': account_id, 'LastName': contact_info['contact_name']}
            if config.contact_rec_type:
                c_details['RecordTypeId'] = config.contact_rec_type

            # Create contact: mapping name and email (PK) to Name and Email native Salesforce Contact Fields (no customization).
            try:
                contact_record = salesforce_client.create_contact(contact_info['email'], **c_details)
            except Exception as e:
                message = str(e)
                return status, message
        # add contact ID to params
        params[config.benchmark_contact_fieldname] = contact_record['Id']

    """ SPECIAL FIELD MAPPINGS FOR LABELS AND CYCLE NAME """
    # create benchmark params
    if config.status_fieldname:
        # check if violation or compliant label is applied
        params[config.status_fieldname] = ""
        if config.compliance_label_id and config.compliance_label_id in result['labels']:
            params[config.status_fieldname] = config.compliance_label.name
        elif config.violation_label_id and config.violation_label_id in result['labels']:
            params[config.status_fieldname] = config.violation_label.name

    if config.labels_fieldname:
        params[config.labels_fieldname] = ".".join(result['label_names'])

    # add cycle, labels, status (if used)
    if config.cycle_fieldname:
        params[config.cycle_fieldname] = result['cycle']['name']

    """ CUSTOM SALESFORCE MAPPINGS FROM PROPERTY """
    # if compliance label is applied, also generate the other field mappings
    # violation label applied means we do not transfer these data fields over
    if config.compliance_label_id and config.compliance_label_id in result['labels']:
        for mapping in mappings:
            params[mapping.salesforce_fieldname] = None
            colname = Column.objects.get(pk=mapping.column_id)

            if colname.display_name and colname.display_name in flat_state:
                field_val = flat_state[colname.display_name]
            elif colname.column_name in flat_state:
                field_val = flat_state[colname.column_name]

            params[mapping.salesforce_fieldname] = field_val

    """ PERFORM UPDATE """
    try:
        salesforce_client.update_benchmark(benchmark_id, **params)
        status = True
    except Exception as ex:
        template = "Property View {2} / Salesforce Benchmark ID {3} : An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args, property_id, benchmark_id)

    return status, message


def update_salesforce_properties(org_id, property_ids):
    """ Update a selection of salesforce properties (not scheduled)
    """

    status = False
    messages = []

    # connect
    connection_status, message, salesforce_client = test_connection(retrieve_connection_params(org_id))
    if not connection_status:
        # connection failed
        return connection_status, [message]

    # get configs
    try:
        config = SalesforceConfig.objects.get(organization_id=org_id)
    except Exception:
        messages.append('No Salesforce configs found. Configure Salesforce on the organization settings page')
        return status, messages

    mappings = SalesforceMapping.objects.filter(organization_id=org_id)

    # update each property
    for p in property_ids:
        st, msg = update_salesforce_property(org_id, p, salesforce_client, config, mappings)

        if not st:
            # catch this failure but keep going
            messages.append(msg)

    if len(messages) == 0:
        # success across all properties
        status = True

    return status, messages


def auto_sync_salesforce_properties(org_id):
    """ scheduled Salesforce properties updates
    """

    status = False
    messages = []

    if not check_salesforce_enabled(org_id):
        messages.append("Salesforce Workflow is not enabled. Enable Salesforce on the organization settings page")
        return status, messages

    # get salesforce config object
    try:
        config = SalesforceConfig.objects.get(organization_id=org_id)
    except Exception:
        messages.append('No Salesforce configs found. Configure Salesforce on the organization settings page')
        return status, messages

    # get properties list that have the 'Indication Label' label applied (for adding to Salesforce)
    ind_label_id = config.indication_label_id

    # set date
    compare_date = config.last_update_date if config.last_update_date else datetime.datetime(1970, 1, 1, tzinfo=get_current_timezone())

    # get IDs by label and date
    property_matches = PropertyView.objects.filter(property__organization_id=org_id).filter(property__updated__gt=compare_date).filter(labels__in=[ind_label_id]).values_list('id', flat=True)

    status, messages = update_salesforce_properties(org_id, list(property_matches))
    # can't email from here due to circular imports...emailing is done in tasks.py

    if len(messages) == 0:
        status = True
        # save new date only if ALL succeeded
        config.last_update_date = timezone.now()
        config.save(update_fields=['last_update_date'])

    return status, messages
