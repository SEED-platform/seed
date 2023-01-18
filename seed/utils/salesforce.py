# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from seed_salesforce.salesforce_client import SalesforceClient


def test_connection(params):
    status = None
    message = None
    try:
        status = 'unknown'
        sf = SalesforceClient(connection_params=params)
        if isinstance(sf, SalesforceClient):
            status = 'success'
        return status, message
    except Exception as e:
        message = " ".join(["Salesforce Authentication Failed:", str(e)])
        status = 'error'
        return status, message


def sync_properties():
    # TODO

    # # get all labels
    # all_labels = self.seed.get_labels()
    # # print(f"ALL labels: {all_labels}")

    # # get properties list that have the 'Indication Label' label applied (for adding to Salesforce)
    # sf_labels = self.seed.get_view_ids_with_label([self.labels['indication_label']])

    # """ labels response looks like this (list):
    # [
    #   {
    #     "id": 30,
    #     "name": "Add to Salesforce",
    #     "color": "orange",
    #     "organization_id": 2,
    #     "is_applied": [212],
    #     "show_in_list": false
    #   }
    # ]
    # """
    # #print(f" SF label(s): {sf_labels}")

    # # retrieve property details for each property with the 'Add to Salesforce' Label (list in is_applied)
    # if sf_labels and sf_labels[0] and 'is_applied' in sf_labels[0].keys():
    #     for item in sf_labels[0]['is_applied']:
    #         # get property
    #         property = self.seed.get_property(item)
    #         print(f" property name: {property['state']['property_name']}, updated date: {property['property']['updated']}")

    #         # first check if Benchmark Salesforce ID exists on this record. we can't do anything otherwise
    #         if not property['state']['extra_data']['Benchmark Salesforce ID']:
    #             # TODO: catch and log
    #             print(f"""SEED record for Property: {property['state']['property_name']} has no Benchmark Salesforce ID populated.
    #                 Create Record in Salesforce first and update SEED record with its Benchmark Salesforce ID.""")

    #         # compare date: property update date should be more recent than last Salesforce upload, otherwise skip.
    #         if self.compare_date_for_upload(property['state']['updated']) is True:
    #             print(f"date comparison == UPDATE! for property {property['state']['property_name']}")

    #             # figure out what other labels are applied to this property
    #             # keep a comma-delimited list for upload to Salesforce later
    #             labelNames = []
    #             for label_id in property['labels']:
    #                 the_label = next((item for item in all_labels if item['id'] == label_id), None)
    #                 if the_label is None:
    #                     # OEP checks if a label applied doesn't exist in SEED and errors out
    #                     # TODO: log appropriately
    #                     print(f"""SEED Label: {label_id} assigned to Property: {property['state']['property_name']} has no details in SEED.
    #                          \n As a result the SEED property (SEED ID: {propertyId} will not be updated in Salesforce until the issue is resolved.
    #                          Confirm that the unavailable SEED label is removed from this property.""")
    #                     continue

    #                 labelNames.append(the_label['name'])

    #             print(f"labelNames: {labelNames}")
    #             labelNameString = ','.join(labelNames)
    #             print(f"labelNameString: {labelNameString}")

    #             # check if property is in violation
    #             isInViolation = True if self.labels['violation_label'] in labelNames else False
    #             isInCompliance = True if self.labels['complied_label'] in labelNames else False

    #             # check violation / compliance status and ensure property should be uploaded
    #             if (isInViolation and not isInCompliance) or (not isInViolation and isInCompliance):
    #                 # xor only one of the labels is applied, can push to Salesforce
    #                 print("Only one label from Violation and Complied is applied, property can be pushed to Salesforce!")

    #                 # QuerySFforContactAndAccount
    #                 # TODO: customizable per instance (looking up contact in Salesforce)?
    #                 contact_email = property['state']['extra_data']['Email'].strip()
    #                 contact_name = property['state']['extra_data']['On Behalf Of']
    #                 account_name = property['state']['extra_data']['Organization'].strip()

    #                 contact_record = self.get_create_contact(contact_name, contact_email, account_name)
    #                 print(f"contact record Id: {contact_record['Id']}, AccountId: {contact_record['AccountId']}")

    #                 # QuerySFforAdminContactAndAccount
    #                 data_admin_email = property['state']['extra_data']['Property Data Administrator - Email'].strip()
    #                 data_admin_name = property['state']['extra_data']['Property Data Administrator'].strip()

    #                 admin_contact_record = self.get_create_contact(data_admin_name, data_admin_email, account_name)
    #                 print(f"admin contact record Id: {admin_contact_record['Id']}, AccountId: {admin_contact_record['AccountId']}")

    #                 # TODO: test contact record now exists, log error and break if not

    #                 # PushPropertytoSalesforce
    #                 result = self.prepare_update_and_push(property, contact_record['Id'], admin_contact_record['Id'], labelNameString, isInViolation, isInCompliance)

    #             elif isInViolation and isInCompliance:
    #                 # Both of these labels should not be applied, ERROR
    #                 # TODO: log this appropriately
    #                 print(f"Property {property['state']['property_name']} has both labels {self.labels['violation_label']} and {self.labels['complied_label']} applied. It should only have one of them. The property was not uploaded to Salesforce.")

    #             else:
    #                 # Neither label is applied
    #                 # TODO: log this appropriately
    #                 print(f"Property {property['state']['property_name']} is missing one of the following labels: {self.labels['violation_label']} or {self.labels['complied_label']}. It was not uploaded to Salesforce.")

    return True
