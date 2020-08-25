# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA

"""

from seed.serializers.postoffice import PostOfficeSerializer, PostOfficeEmailSerializer
from seed.utils.viewsets import SEEDOrgModelViewSet
from seed.models import PropertyState, TaxLotState
from seed.models import PostOfficeEmail, PostOfficeEmailTemplate
from post_office import mail                      

# Change to template view set
class PostOfficeViewSet(SEEDOrgModelViewSet):
    """API endpoint for viewing and creating cycles (time periods).

        Returns::
            {
                'status': 'success',
                'cycles': [
                    {
                        'id': Cycle`s primary key,
                        'name': Name given to cycle,
                        'start': Start date of cycle,
                        'end': End date of cycle,
                        'created': Created date of cycle,
                        'properties_count': Count of properties in cycle,
                        'taxlots_count': Count of tax lots in cycle,
                        'organization': Id of organization cycle belongs to,
                        'user': Id of user who created cycle
                    }
                ]
            }


    retrieve:
        Return a cycle instance by pk if it is within user`s specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true

    list:
        Return all cycles available to user through user`s specified org.

        :GET: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: name
            :Description: optional name for filtering cycles
            :required: false
            :Parameter: start_lte
            :Description: optional iso date for filtering by cycles
                that start on or before the given date
            :required: false
            :Parameter: end_gte
            :Description: optional iso date for filtering by cycles
                that end on or after the given date
            :required: false

    create:
        Create a new cycle within user`s specified org.

        :POST: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: true
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: true
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: true

    delete:
        Remove an existing cycle.

        :DELETE: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true

    update:
        Update a cycle record.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: true
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: true
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: true

    partial_update:
        Update one or more fields on an existing cycle.

        :PUT: Expects organization_id in query string.
        :Parameters:
            :Parameter: organization_id
            :Description: organization_id for this user`s organization
            :required: true
            :Parameter: cycle pk
            :Description: id for desired cycle
            :required: true
            :Parameter: name
            :Description: cycle name
            :required: false
            :Parameter: start
            :Description: cycle start date. format: ``YYYY-MM-DDThh:mm``
            :required: false
            :Parameter: end
            :Description: cycle end date. format: ``YYYY-MM-DDThh:mm``
            :required: false
    """
    model = PostOfficeEmailTemplate
    serializer_class = PostOfficeSerializer
    pagination_class = None


    def get_queryset(self):
        # temp_id = self.get_templates(self.request)
        # Order cycles by name because if the user hasn't specified then the front end WILL default to the first
        # print(EmailTemplate.objects.order_by('name'))
        return PostOfficeEmailTemplate.objects.order_by('name')

    def perform_create(self, serializer):
        org_id = self.get_organization(self.request)
        user = self.request.user
        serializer.save(organization_id=org_id, user=user)



class PostOfficeEmailViewSet(SEEDOrgModelViewSet):
    model = PostOfficeEmail
    serializer_class = PostOfficeEmailSerializer
    pagination_class = None


    def get_queryset(self):
        # print(id)
        # print(building_id)
        # temp_id = self.get_templates(self.request)
        # Order cycles by name because if the user hasn't specified then the front end WILL default to the first
        # print(EmailTemplate.objects.order_by('name'))
        return PostOfficeEmail.objects.all()
        

    def perform_create(self, serializer):

        # NOTES
        # -- Take building IDs and pull out the email (use building ID to pull owner email)
        # -- Send the email (mail.send)
        # -- Save
        # -- Add organization (maybe user)

        # CLEAN UP THE FOLLOWING CODE
        # DISTINCTION
        # ORGANIZATION ID

        # Adding Organization ID to Template and Email, User to Template and Email
        # After 1st Column add organizations and users


        # org_id = self.get_organization(self.request)
        # user = self.request.user
        # serializer.save(organization_id=org_id, user=user)


        #HANDLE TEMPLATE DOES NOT EXIST

        print("BACKEND")
        name = self.request.data.get('name')
        print(name)
        inventory_id = self.request.data.get('inventory_id', [])
        print(inventory_id)
        print("*****************")
        print(self.request.data.get('inventory_type'))
        print("*****************")
        email_list = []
        if self.request.data.get('inventory_type') == "properties" :
            State = PropertyState
        else :
            State = TaxLotState
        # QuerySet is returned when calling values_list() function, so we convert it into a list 
        email_list = list(State.objects.filter(id__in=inventory_id).values_list('owner_email', flat=True))
        email_sender = 'from@example.com'

        # org_id = self.get_organization(self.request)
        # user = self.request.user
        # serializer.save(organization_id=org_id, user=user)
        ptr = mail.send(
                email_list,
                # self.request.data.get(from_email)
                email_sender,
                template = PostOfficeEmailTemplate.objects.get(name=name),
                backend = 'post_office_backend')
    
        org = self.get_organization(self.request)
        user = self.request.user
        # Assigning all the fields inside of postoffice to seed_postoffice
        email_data = {
            'email_ptr_id': ptr.id, 
            'from_email': ptr.from_email,
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

        serializer.save(**email_data, organization_id=org, user=user)
        




    