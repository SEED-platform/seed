from rest_framework import viewsets
from rest_framework import generics

from seed.decorators import (
    DecoratorMixin,
)
from seed.filters import (
    BuildingFilterBackend,
)
from seed.utils.api import (
    drf_api_endpoint,
)
from seed.models import (
    StatusLabel as Label,
    BuildingSnapshot,
)
from seed.serializers.labels import (
    LabelSerializer,
)


class LabelViewSet(DecoratorMixin(drf_api_endpoint),
                   viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    queryset = Label.objects.none()

    def get_queryset(self):
        return Label.objects.filter(
            super_organization__in=self.request.user.orgs.all()
        ).distinct()

    def get_serializer(self, *args, **kwargs):
        kwargs['super_organization'] = self.request.user.orgs.first()
        return super(LabelViewSet, self).get_serializer(*args, **kwargs)


class UpdateBuildingLabelsAPIView(generics.GenericAPIView):
    filter_backends = (BuildingFilterBackend,)
    queryset = BuildingSnapshot.objects.none()

    def put(self, *args, **kwargs):
        """
        Updates label assignments to buildings.

        Payload::

            {
                "add_label_ids": {array}            Array of label ids to apply to selected buildings
                "remove_label_ids": {array}         Array of label ids to remove from selected buildings
                "buildings": {array}                Array of building ids to apply/remove labels. (this will be empty or null if select_all_checkbox is true),
                "select_all_checkbox": {boolean},   Whether select all checkbox was selected on building list
                "filter_params": {object}           A 'filter params' object containing key/value pairs for selected filters
                "org_id": {integer}                 The user's org ID
            }

        Returns::

            {
                'status': {string}                  'success' or 'error'
                'message': {string}                 Error message if status = 'error'
                'num_buildings_updated': {integer}  Number of buildings in queryset
            }

        """
        # TODO: this should actually do something
        '''
        @api_endpoint
        @ajax_request
        @login_required
        def update_building_labels(request):
            #TEMP:
            num_buildings_updated = 23

            #TODO:  Apply add_label_ids to selected buildings in org
            #       Remove remove_label_ids from selected buildings in org
            #       Return 'success' or 'error' and an error 'message'

            return {'status': 'success', 'num_buildings_updated': num_buildings_updated}
        '''
        queryset = self.filter_queryset(self.get_queryset())
        import ipdb; ipdb.set_trace()
        assert False


## ~~~~~~~ #
## LABELS  #
## ~~~~~~~ #
#
##DMcQ:  Temporary location for label methods. (Probably should be added as separate view
##       if we want to start refactoring main.py.)
##       This code is only for UI work...will be properly implemented by BE person.
#
#
#from ..utils import labels as label_utils
#from django.core.exceptions import ObjectDoesNotExist
#
#@api_endpoint
#@ajax_request
#@login_required
#def get_labels(request):
#    """
#    Gets all labels for the current user's organization.
#
#    If request object has 'search' object assigned, use that object to
#    select subset of buildings, and then determine if each label appears
#    at least once in that set. If so, assign an 'is_applied' property to
#    True, otherwise assign False.
#
#    If no 'search' object is provided, do not need to assign an 'is_applied' property.
#
#    (Note:  The search object is defined on the front end by the angular search_service.js
#            and is used in other Django methods. It has a host of properties, only some
#            of which are relative here.)
#
#    Payload::
#
#        {
#            'search': (optional)
#            {
#                "select_all_checkbox":  boolean, indicates if "select all" on building
#                                        list was selected
#                "selected_buildings":   array of building ids. May be empty if
#                                        select_all_checkbox is true.
#                "filter_params" :       object with key/values for each filter used.
#            }
#        }
#
#    Returns::
#
#        {
#         'status': 'success',
#         'labels':
#          [
#            {
#             'name': name of label,
#             'color': color of label,
#             'id': label's ID
#             'is_applied': boolean. True if label is in one or more buildings in query.
#            }, ...
#         ]
#        }
#    """
#    labels = label_utils.get_labels(request.user)
#
#    #DMcQ: TEMP FOR UI DEV: Randomly assign 'is_applied' property
#    #TODO: REPLACE WITH VALID ROUTINE TO ASSIGN is_applied
#    for label in labels:
#        label['is_applied'] = random.choice([True, False])
#
#    return {'status': 'success', 'labels': labels}
#
#
#
#
#@api_endpoint
#@ajax_request
#@login_required
#def create_label(request):
#    """
#    Creates a new label.
#
#    Payload::
#
#        {
#         'label':
#          {
#           "color": "red",
#           "name": "non compliant"
#          }
#        }
#
#    Returns::
#
#        {
#         'status':  {string} 'success' or 'error',
#         'message': {string} error message, if any
#         'label':   {object} The new label object
#        }
#
#    """
#
#    #Check for correct request and params
#    if request.method != 'POST':
#        return HttpResponseBadRequest("This view replies only to POST methods")
#
#    body = json.loads(request.body)
#    label = body.get('label')
#
#    if not label:
#        msg = "Missing 'label' parameter"
#        _log.error(msg)
#        _log.exception(str(e))
#        return HttpResponseBadRequest(msg)
#
#    #TODO:  We need to implement proper error responses for the REST API.
#    #       In this case, we should be returning a 409 error if the label
#    #       already exists.
#
#    if StatusLabel.objects.filter(name=label['name']).exists():
#        return  {'status': 'error', 'message' : 'label already exists' }
#
#    new_label, created = StatusLabel.objects.get_or_create(
#        super_organization=request.user.orgs.all()[0],
#        name=label['name'],
#        color=label['color'],
#    )
#
#    #Must be an easier way to do this
#    return_label = {    'id' : new_label.id,
#                        'name': new_label.name,
#                        'color' : new_label.color
#                    }
#
#    return {'status': 'success',
#            'label': return_label}
#
#
#@api_endpoint
#@ajax_request
#@login_required
#def update_label(request):
#    """
#    Updates a label.
#
#    Payload::
#
#        {
#         "label": {
#            "id":       ID of label to change,
#            "color":    Label's new color,
#            "name":     Label's new name,
#         }
#        }
#
#    Returns::
#
#        {
#            'status': {string}  'success' or 'error'
#            'label' : {object}  label object for updated label
#        }
#
#    """
#
#    # NOTE: SHOULDN'T THIS BE USING THE 'PUT' REQUEST TYPE?
#
#     #Check for correct request and params
#    if request.method != 'POST':
#        return HttpResponseBadRequest("This view replies only to POST methods")
#
#    body = json.loads(request.body)
#    label = body.get('label')
#
#    if not label:
#        msg = "Missing 'label' parameter"
#        _log.error(msg)
#        _log.exception(str(e))
#        return HttpResponseBadRequest(msg)
#
#    try:
#        update_label = StatusLabel.objects.get(pk=label['id'])
#    except ObjectDoesNotExist:
#        return  {'status': 'error', 'message' : 'label does not exist' }
#
#    try:
#        update_label.color = label['color']
#        update_label.name = label['name']
#        update_label.save()
#    except:
#        msg = 'Could not update label'
#        _log.error(msg)
#        _log.exception(str(e))
#        return  {'status': 'error', 'message' : msg }
#
#    return_label = {    'id'    : update_label.id,
#                        'name'  : update_label.name,
#                        'color' : update_label.color
#                    }
#
#    return {'status': 'success', 'label': return_label}
#
#
#@api_endpoint
#@ajax_request
#@login_required
#def delete_label(request):
#    """
#    Deletes a label.
#
#    Payload::
#
#        {'label':
#         {'id': ID of label to delete}
#        }
#
#    Returns::
#
#        {'status': 'success'}
#
#    """
#
#    # NOTE: SHOULDN'T THIS BE USING THE 'DELETE' REQUEST TYPE?
#
#    body = json.loads(request.body)
#    label = body.get('label')
#
#    if not label:
#        msg = "Missing 'label' parameter"
#        _log.error(msg)
#        _log.exception(str(e))
#        return HttpResponseBadRequest(msg)
#
#    try:
#        status_label = StatusLabel.objects.get(pk=label['id'])
#        ProjectBuilding.objects.filter(
#            status_label=status_label
#        ).update(status_label=None)
#        status_label.delete()
#    except:
#        msg = 'Could not delete label'
#        _log.error(msg)
#        _log.exception(str(e))
#        return  {'status': 'error', 'message' : msg }
#
#    return {'status': 'success'}
