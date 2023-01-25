# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import datetime

import pytz
from django.utils import timezone
from seed_salesforce.salesforce_client import SalesforceClient

from seed.models import PropertyView
from seed.models import StatusLabel as Label
from seed.models.columns import Column
from seed.models.salesforce_configs import SalesforceConfig
from seed.models.salesforce_mappings import SalesforceMapping
from seed.serializers.properties import PropertyViewSerializer


def test_connection(params):
    """ test Salesforce connection with credentials stored in the salesforce_config model
    """
    status = False
    message = None
    try:
        status = 'unknown'
        sf = SalesforceClient(connection_params=params)
        if isinstance(sf, SalesforceClient):
            status = True
        return status, message, sf
    except Exception as e:
        message = " ".join(["Salesforce Authentication Failed:", str(e)])
        return status, message, None


def retrieve_connection_params(org_id):
    """ retrieve salesforce connection params from the salesforce_config model by org_id
    """
    params = {}
    try:
        config = SalesforceConfig.objects.get(organization_id=org_id)
    except Exception as e:
        print('No salesforce configs entered in settings page: ' + e)
        return params

    if config:
        params['instance'] = config.url
        params['username'] = config.username
        params['password'] = config.password
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

    if len(mappings) == 0:
        mappings = SalesforceMapping.objects.filter(organization_id=org_id)

    # TODO: check if property view does not have "add to salesforce label"?
    # or if it is missing the violation OR compliance label?
    # or no benchmark ID defined or populated?

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

    # grab the benchmark ID from the record (can't do anything without it)
    if not config.seed_benchmark_id_column_id:
        message = 'No SEED Benchmark ID Field selected in Settings'
        return status, message

    benchmark_id_colname = Column.objects.get(pk=config.seed_benchmark_id_column_id)
    # TODO: not sure about this...are column names or display names used?
    # print(f"displayname: {benchmark_id_colname.display_name}")
    # print(f"column_name: {benchmark_id_colname.column_name}")

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
        message = 'SEED Unique Benchmark ID Column is undefined '
        return status, message

    # generate the field mappings
    params = {}
    for mapping in mappings:
        params[mapping.salesforce_fieldname] = None
        colname = Column.objects.get(pk=mapping.column_id)

        if colname.display_name and colname.display_name in flat_state:
            field_val = flat_state[colname.display_name]
        elif colname.column_name in flat_state:
            field_val = flat_state[colname.column_name]

        params[mapping.salesforce_fieldname] = field_val

    # add cycle, labels, status (if used)
    if config.cycle_fieldname:
        params[config.cycle_fieldname] = result['cycle']['name']

    if config.status_fieldname:
        # check if violation or compliant label is applied
        params[config.status_fieldname] = ""
        if config.compliance_label_id and config.compliance_label_id in result['labels']:
            params[config.status_fieldname] = config.compliance_label.name
        elif config.violation_label_id and config.violation_label_id in result['labels']:
            params[config.status_fieldname] = config.violation_label.name

    if config.labels_fieldname:
        params[config.labels_fieldname] = ".".join(result['label_names'])

    # print(f"!!!!!! PARAMS:")
    # print(params)

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

    # get salesforce config object
    try:
        config = SalesforceConfig.objects.get(organization_id=org_id)
    except Exception:
        status = False
        messages.append('No Salesforce configs found. Configure Salesforce on the organization settings page')
        return status, messages

    # salesforce_client = SalesforceClient(connection_params=retrieve_connection_params(org_id))
    # get mapping object
    # mappings = SalesforceMapping.objects.filter(organization_id=org_id)

    # get properties list that have the 'Indication Label' label applied (for adding to Salesforce)
    ind_label_id = config.indication_label_id

    # set date
    compare_date = config.last_update_date if config.last_update_date else datetime.datetime(1970, 1, 1, tzinfo=pytz.UTC)

    # GET IDS by label and date
    # TODO: NOTE not limiting CYCLE here! (but should get caught by 'last update date' comparison to 'last salesforce update')
    # could pass this date into the query below?

    property_matches = PropertyView.objects.filter(property__organization_id=org_id).filter(property__updated__gt=compare_date).filter(labels__in=[ind_label_id]).values_list('id', flat=True)

    status, messages = update_salesforce_properties(org_id, list(property_matches))
    # TODO: log this somewhere!?

    if len(messages) == 0:
        status = True
        # save new date
        config.last_update_date = timezone.now()
        config.save(update_fields=['last_update_date'])

    return status, messages
