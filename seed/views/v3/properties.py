"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
from collections import namedtuple

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, Subquery
from django.http import HttpResponse, JsonResponse
from django_filters import CharFilter, DateFilter
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from seed.building_sync.building_sync import BuildingSync
from seed.data_importer.utils import usage_point_id
from seed.decorators import ajax_request_class
from seed.hpxml.hpxml import HPXML
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models import (AUDIT_USER_EDIT, DATA_STATE_MATCHING,
                         MERGE_STATE_DELETE, MERGE_STATE_MERGED,
                         MERGE_STATE_NEW, VIEW_LIST, VIEW_LIST_PROPERTY,
                         BuildingFile, Column, ColumnListProfile,
                         ColumnListProfileColumn, ColumnMappingProfile, Cycle,
                         Meter, Note, Property, PropertyAuditLog,
                         PropertyMeasure, PropertyState, PropertyView,
                         Simulation)
from seed.models import StatusLabel as Label
from seed.models import TaxLotProperty, TaxLotView
from seed.serializers.pint import (PintJSONEncoder,
                                   apply_display_unit_preferences)
from seed.serializers.properties import (PropertySerializer,
                                         PropertyStateSerializer,
                                         PropertyViewAsStateSerializer,
                                         PropertyViewSerializer,
                                         UpdatePropertyPayloadSerializer)
from seed.serializers.taxlots import TaxLotViewSerializer
from seed.utils.api import OrgMixin, ProfileIdMixin, api_endpoint_class
from seed.utils.api_schema import (AutoSchemaHelper,
                                   swagger_auto_schema_org_query_param)
from seed.utils.labels import get_labels
from seed.utils.match import match_merge_link
from seed.utils.merge import merge_properties
from seed.utils.meters import PropertyMeterReadingsExporter
from seed.utils.properties import (get_changed_fields,
                                   pair_unpair_property_taxlot,
                                   properties_across_cycles,
                                   update_result_with_master)

# Global toggle that controls whether or not to display the raw extra
# data fields in the columns returned for the view.
DISPLAY_RAW_EXTRADATA = True
DISPLAY_RAW_EXTRADATA_TIME = True

ErrorState = namedtuple('ErrorState', ['status_code', 'message'])


class PropertyViewFilterBackend(filters.DjangoFilterBackend):
    """
    Used to add filters to the `search` view
    I was unable to find a better way to add the filterset_class to a single view

    TODO: Add this to seed/filtersets.py or seed/filters.py
    """
    def get_filterset_class(self, view, queryset=None):
        return PropertyViewFilterSet


class PropertyViewFilterSet(filters.FilterSet, OrgMixin):
    """
    Advanced filtering for PropertyView sets

    TODO: Add this to seed/filtersets.py
    """
    address_line_1 = CharFilter(field_name="state__address_line_1", lookup_expr='contains')
    analysis_state = CharFilter(method='analysis_state_filter')
    identifier = CharFilter(method='identifier_filter')
    cycle_start = DateFilter(field_name='cycle__start', lookup_expr='lte')
    cycle_end = DateFilter(field_name='cycle__end', lookup_expr='gte')

    class Meta:
        model = PropertyView
        fields = ['identifier', 'address_line_1', 'cycle', 'property', 'cycle_start', 'cycle_end', 'analysis_state']

    def identifier_filter(self, queryset, name, value):
        address_line_1 = Q(state__address_line_1__icontains=value)
        jurisdiction_property_id = Q(state__jurisdiction_property_id__icontains=value)
        custom_id_1 = Q(state__custom_id_1__icontains=value)
        pm_property_id = Q(state__pm_property_id__icontains=value)
        ubid = Q(state__ubid__icontains=value)

        query = (
            address_line_1 |
            jurisdiction_property_id |
            custom_id_1 |
            pm_property_id |
            ubid
        )
        return queryset.filter(query).order_by('-state__id')

    def analysis_state_filter(self, queryset, name, value):
        # For some reason a ChoiceFilter doesn't work on this object. I wanted to have it
        # magically look up the map from the analysis_state string to the analysis_state ID, but
        # it isn't working. Forcing it manually.

        # If the user puts in a bogus filter, then it will return All, for now

        state_id = None
        for state in PropertyState.ANALYSIS_STATE_TYPES:
            if state[1].upper() == value.upper():
                state_id = state[0]
                break

        if state_id is not None:
            return queryset.filter(Q(state__analysis_state__exact=state_id)).order_by('-state__id')
        else:
            return queryset.order_by('-state__id')


class PropertyViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    serializer_class = PropertySerializer
    _organization = None

    # For the Swagger page, GenericAPIView asserts a value exists for `queryset`
    queryset = PropertyView.objects.none()

    @action(detail=False, filter_backends=[PropertyViewFilterBackend])
    def search(self, request):
        """
        Filters the property views accessible to the user.
        This is different from the properties/filter API because of the available
        filtering parameters and because this view does not use list views for rendering
        """
        # here be dragons
        org_id = self.get_organization(self.request)
        qs = PropertyView.objects.filter(property__organization_id=org_id).order_by('-state__id')
        # this is the entrypoint to the filtering backend
        # https://www.django-rest-framework.org/api-guide/filtering/#custom-generic-filtering
        qs = self.filter_queryset(qs)
        # converting QuerySet to list b/c serializer will only use column list profile this way
        return JsonResponse(
            PropertyViewAsStateSerializer(list(qs), context={'request': request}, many=True).data,
            safe=False,
        )

    def _get_filtered_results(self, request, profile_id):
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 1)
        org_id = self.get_organization(request)
        cycle_id = request.query_params.get('cycle')
        # check if there is a query paramater for the profile_id. If so, then use that one
        profile_id = request.query_params.get('profile_id', profile_id)

        if not org_id:
            return JsonResponse(
                {'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                status=status.HTTP_400_BAD_REQUEST)

        if cycle_id:
            cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
        else:
            cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
            if cycle:
                cycle = cycle.first()
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not locate cycle',
                    'pagination': {
                        'total': 0
                    },
                    'cycle_id': None,
                    'results': []
                })

        # Return property views limited to the 'property_view_ids' list. Otherwise, if selected is empty, return all
        if 'property_view_ids' in request.data and request.data['property_view_ids']:
            property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(id__in=request.data['property_view_ids'],
                        property__organization_id=org_id, cycle=cycle) \
                .order_by('id')  # TODO: test adding .only(*fields['PropertyState'])
        else:
            property_views_list = PropertyView.objects.select_related('property', 'state', 'cycle') \
                .filter(property__organization_id=org_id, cycle=cycle) \
                .order_by('id')  # TODO: test adding .only(*fields['PropertyState'])

        paginator = Paginator(property_views_list, per_page)

        try:
            property_views = paginator.page(page)
            page = int(page)
        except PageNotAnInteger:
            property_views = paginator.page(1)
            page = 1
        except EmptyPage:
            property_views = paginator.page(paginator.num_pages)
            page = paginator.num_pages

        org = Organization.objects.get(pk=org_id)

        # Retrieve all the columns that are in the db for this organization
        columns_from_database = Column.retrieve_all(org_id, 'property', False)

        # This uses an old method of returning the show_columns. There is a new method that
        # is prefered in v2.1 API with the ProfileIdMixin.
        if profile_id is None:
            show_columns = None
        elif profile_id == -1:
            show_columns = list(Column.objects.filter(
                organization_id=org_id
            ).values_list('id', flat=True))
        else:
            try:
                profile = ColumnListProfile.objects.get(
                    organization=org,
                    id=profile_id,
                    profile_location=VIEW_LIST,
                    inventory_type=VIEW_LIST_PROPERTY
                )
                show_columns = list(ColumnListProfileColumn.objects.filter(
                    column_list_profile_id=profile.id
                ).values_list('column_id', flat=True))
            except ColumnListProfile.DoesNotExist:
                show_columns = None

        related_results = TaxLotProperty.get_related(property_views, show_columns,
                                                     columns_from_database)

        # collapse units here so we're only doing the last page; we're already a
        # realized list by now and not a lazy queryset
        unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

        response = {
            'pagination': {
                'page': page,
                'start': paginator.page(page).start_index(),
                'end': paginator.page(page).end_index(),
                'num_pages': paginator.num_pages,
                'has_next': paginator.page(page).has_next(),
                'has_previous': paginator.page(page).has_previous(),
                'total': paginator.count
            },
            'cycle_id': cycle.id,
            'results': unit_collapsed_results
        }

        return JsonResponse(response)

    def _move_relationships(self, old_state, new_state):
        """
        In general, we move the old relationships to the new state since the old state should not be
        accessible anymore. If we ever unmerge, then we need to decide who gets the data.. both?

        :param old_state: PropertyState
        :param new_state: PropertyState
        :return: PropertyState, updated new_state
        """
        for s in old_state.scenarios.all():
            s.property_state = new_state
            s.save()

        # Move the measures to the new state
        for m in PropertyMeasure.objects.filter(property_state=old_state):
            m.property_state = new_state
            m.save()

        # Move the old building file to the new state to preserve the history
        for b in old_state.building_files.all():
            b.property_state = new_state
            b.save()

        for s in Simulation.objects.filter(property_state=old_state):
            s.property_state = new_state
            s.save()

        return new_state

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(required=True)],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'selected': ['integer'],
            },
            description='IDs for properties to be checked for which labels are applied.'
        )
    )
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def labels(self, request):
        """
        Returns a list of all labels where the is_applied field
        in the response pertains to the labels applied to property_view
        """
        labels = Label.objects.filter(
            super_organization=self.get_parent_org(self.request)
        ).order_by("name").distinct()
        super_organization = self.get_organization(request)
        # TODO: refactor to avoid passing request here
        return get_labels(request, labels, super_organization, 'property_view')

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(required=True)],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'interval': 'string',
                'excluded_meter_ids': ['integer'],
            },
            required=['property_view_id', 'interval', 'excluded_meter_ids'],
            description='Properties:\n'
                        '- interval: one of "Exact", "Month", or "Year"\n'
                        '- excluded_meter_ids: array of meter IDs to exclude'
        )
    )
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def meter_usage(self, request, pk):
        """
        Retrieves meter usage information
        """
        body = dict(request.data)
        interval = body['interval']
        excluded_meter_ids = body['excluded_meter_ids']
        org_id = self.get_organization(request)

        property_view = PropertyView.objects.get(
            pk=pk,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]

        exporter = PropertyMeterReadingsExporter(property_id, org_id, excluded_meter_ids, scenario_ids=scenario_ids)

        return exporter.readings_and_column_defs(interval)

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def meters(self, request, pk):
        """
        Retrieves meters for the property
        """
        org_id = self.get_organization(request)

        property_view = PropertyView.objects.get(
            pk=pk,
            cycle__organization_id=org_id
        )
        property_id = property_view.property.id
        scenario_ids = [s.id for s in property_view.state.scenarios.all()]
        energy_types = dict(Meter.ENERGY_TYPES)

        res = []
        for meter in Meter.objects.filter(Q(property_id=property_id) | Q(scenario_id__in=scenario_ids)):
            if meter.source == meter.GREENBUTTON:
                source = 'GB'
                source_id = usage_point_id(meter.source_id)
            elif meter.source == meter.BUILDINGSYNC:
                source = 'BS'
                source_id = meter.source_id
            else:
                source = 'PM'
                source_id = meter.source_id

            res.append({
                'id': meter.id,
                'type': energy_types[meter.type],
                'source': source,
                'source_id': source_id,
                'scenario_id': meter.scenario.id if meter.scenario is not None else None,
                'scenario_name': meter.scenario.name if meter.scenario is not None else None
            })

        return res

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle',
                required=False,
                description='The ID of the cycle to get properties'
            ),
            AutoSchemaHelper.query_integer_field(
                'per_page',
                required=False,
                description='Number of properties per page'
            ),
            AutoSchemaHelper.query_integer_field(
                'page',
                required=False,
                description='Page to fetch'
            ),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        List all the properties	with all columns
        """
        return self._get_filtered_results(request, profile_id=-1)

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                'organization_id': 'integer',
                'profile_id': 'integer',
                'cycle_ids': ['integer'],
            },
            required=['organization_id', 'cycle_ids'],
            description='Properties:\n'
                        '- organization_id: ID of organization\n'
                        '- profile_id: Either an id of a list settings profile, '
                        'or undefined\n'
                        '- cycle_ids: The IDs of the cycle to get properties'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def filter_by_cycle(self, request):
        """
        List all the properties	with all columns
        """
        # NOTE: we are using a POST http method b/c swagger and django handle
        # arrays differently in query parameters. ie this is just simpler
        org_id = self.get_organization(request)
        profile_id = request.data.get('profile_id', -1)
        cycle_ids = request.data.get('cycle_ids', [])

        if not org_id:
            return JsonResponse(
                {'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
                status=status.HTTP_400_BAD_REQUEST)

        response = properties_across_cycles(org_id, profile_id, cycle_ids)

        return JsonResponse(response)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle',
                required=False,
                description='The ID of the cycle to get properties'),
            AutoSchemaHelper.query_integer_field(
                'per_page',
                required=False,
                description='Number of properties per page'
            ),
            AutoSchemaHelper.query_integer_field(
                'page',
                required=False,
                description='Page to fetch'
            ),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'profile_id': 'integer',
                'property_view_ids': ['integer'],
            },
            description='Properties:\n'
                        '- profile_id: Either an id of a list settings profile, or undefined\n'
                        '- property_view_ids: List of property view ids'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def filter(self, request):
        """
        List all the properties
        """
        if 'profile_id' not in request.data:
            profile_id = None
        else:
            if request.data['profile_id'] == 'None':
                profile_id = None
            else:
                profile_id = request.data['profile_id']

                # ensure that profile_id is an int
                try:
                    profile_id = int(profile_id)
                except TypeError:
                    pass

        return self._get_filtered_results(request, profile_id=profile_id)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(required=True)],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer']
            },
            required=['property_view_ids'],
            description='Properties:\n'
                        '- property_view_ids: array containing Property view IDs.'
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=False, methods=['POST'])
    def meters_exist(self, request):
        """
        Check to see if the given Properties (given by ID) have Meters.
        """
        org_id = self.get_organization(request)
        property_view_ids = request.data.get('property_view_ids', [])
        property_views = PropertyView.objects.filter(
            id__in=property_view_ids,
            cycle__organization_id=org_id
        )

        # Check that property_view_ids given are all contained within given org.
        if (property_views.count() != len(property_view_ids)) or len(property_view_ids) == 0:
            return {
                'status': 'error',
                'message': 'Cannot check meters for given records.'
            }

        return Meter.objects.filter(property_id__in=Subquery(property_views.values('property_id'))).exists()

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer']
            },
            required=['property_view_ids'],
            description='Array containing property view ids to merge'),
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def merge(self, request):
        """
        Merge multiple property records into a single new record, and run this
        new record through a match and merge round within it's current Cycle.
        """
        body = request.data
        organization_id = int(self.get_organization(request))

        property_view_ids = body.get('property_view_ids', [])
        property_states = PropertyView.objects.filter(
            id__in=property_view_ids,
            cycle__organization_id=organization_id
        ).values('id', 'state_id')
        # get the state ids in order according to the given view ids
        property_states_dict = {p['id']: p['state_id'] for p in property_states}
        property_state_ids = [
            property_states_dict[view_id]
            for view_id in property_view_ids if view_id in property_states_dict
        ]

        if len(property_state_ids) != len(property_view_ids):
            return {
                'status': 'error',
                'message': 'All records not found.'
            }

        # Check the number of state_ids to merge
        if len(property_state_ids) < 2:
            return JsonResponse({
                'status': 'error',
                'message': 'At least two ids are necessary to merge'
            }, status=status.HTTP_400_BAD_REQUEST)

        merged_state = merge_properties(property_state_ids, organization_id, 'Manual Match')

        merge_count, link_count, view_id = match_merge_link(merged_state.propertyview_set.first().id, 'PropertyState')

        result = {
            'status': 'success'
        }

        result.update({
            'match_merged_count': merge_count,
            'match_link_count': link_count,
        })

        return result

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=no_body,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['PUT'])
    def unmerge(self, request, pk=None):
        """
        Unmerge a property view into two property views
        """
        try:
            old_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                id=pk,
                property__organization_id=self.get_organization(request)
            )
        except PropertyView.DoesNotExist:
            return {
                'status': 'error',
                'message': 'property view with id {} does not exist'.format(pk)
            }

        # Duplicate pairing
        paired_view_ids = list(TaxLotProperty.objects.filter(property_view_id=old_view.id)
                               .order_by('taxlot_view_id').values_list('taxlot_view_id', flat=True))

        # Capture previous associated labels
        label_ids = list(old_view.labels.all().values_list('id', flat=True))

        notes = old_view.notes.all()
        for note in notes:
            note.property_view = None

        merged_state = old_view.state
        if merged_state.data_state != DATA_STATE_MATCHING or merged_state.merge_state != MERGE_STATE_MERGED:
            return {
                'status': 'error',
                'message': 'property view with id {} is not a merged property view'.format(pk)
            }

        log = PropertyAuditLog.objects.select_related('parent_state1', 'parent_state2').filter(
            state=merged_state
        ).order_by('-id').first()

        if log.parent_state1 is None or log.parent_state2 is None:
            return {
                'status': 'error',
                'message': 'property view with id {} must have two parent states'.format(pk)
            }

        state1 = log.parent_state1
        state2 = log.parent_state2
        cycle_id = old_view.cycle_id

        # Clone the property record twice, then copy over meters
        old_property = old_view.property
        new_property = old_property
        new_property.id = None
        new_property.save()

        new_property_2 = Property.objects.get(pk=new_property.id)
        new_property_2.id = None
        new_property_2.save()

        Property.objects.get(pk=new_property.id).copy_meters(old_view.property_id)
        Property.objects.get(pk=new_property_2.id).copy_meters(old_view.property_id)

        # If canonical Property is NOT associated to a different -View, delete it
        if not PropertyView.objects.filter(property_id=old_view.property_id).exclude(id=old_view.id).exists():
            Property.objects.get(pk=old_view.property_id).delete()

        # Create the views
        new_view1 = PropertyView(
            cycle_id=cycle_id,
            property_id=new_property.id,
            state=state1
        )
        new_view2 = PropertyView(
            cycle_id=cycle_id,
            property_id=new_property_2.id,
            state=state2
        )

        # Mark the merged state as deleted
        merged_state.merge_state = MERGE_STATE_DELETE
        merged_state.save()

        # Change the merge_state of the individual states
        if log.parent1.name in ['Import Creation',
                                'Manual Edit'] and log.parent1.import_filename is not None:
            # State belongs to a new record
            state1.merge_state = MERGE_STATE_NEW
        else:
            state1.merge_state = MERGE_STATE_MERGED
        if log.parent2.name in ['Import Creation',
                                'Manual Edit'] and log.parent2.import_filename is not None:
            # State belongs to a new record
            state2.merge_state = MERGE_STATE_NEW
        else:
            state2.merge_state = MERGE_STATE_MERGED
        # In most cases data_state will already be 3 (DATA_STATE_MATCHING), but if one of the parents was a
        # de-duplicated record then data_state will be 0. This step ensures that the new states will be 3.
        state1.data_state = DATA_STATE_MATCHING
        state2.data_state = DATA_STATE_MATCHING
        state1.save()
        state2.save()

        # Delete the audit log entry for the merge
        log.delete()

        old_view.delete()
        new_view1.save()
        new_view2.save()

        # Asssociate labels
        label_objs = Label.objects.filter(pk__in=label_ids)
        new_view1.labels.set(label_objs)
        new_view2.labels.set(label_objs)

        # Duplicate notes to the new views
        for note in notes:
            created = note.created
            updated = note.updated
            note.id = None
            note.property_view = new_view1
            note.save()
            ids = [note.id]
            note.id = None
            note.property_view = new_view2
            note.save()
            ids.append(note.id)
            # Correct the created and updated times to match the original note
            Note.objects.filter(id__in=ids).update(created=created, updated=updated)

        for paired_view_id in paired_view_ids:
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           property_view_id=new_view1.id,
                           taxlot_view_id=paired_view_id).save()
            TaxLotProperty(primary=True,
                           cycle_id=cycle_id,
                           property_view_id=new_view2.id,
                           taxlot_view_id=paired_view_id).save()

        return {
            'status': 'success',
            'view_id': new_view1.id
        }

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def links(self, request, pk=None):
        """
        Get property details for each linked property across org cycles
        """
        organization_id = self.get_organization(request)
        base_view = PropertyView.objects.select_related('cycle').filter(
            pk=pk,
            cycle__organization_id=organization_id
        )

        if base_view.exists():
            result = {'data': []}

            # Grab extra_data columns to be shown in the results
            all_extra_data_columns = Column.objects.filter(
                organization_id=organization_id,
                is_extra_data=True,
                table_name='PropertyState'
            ).values_list('column_name', flat=True)

            linked_views = PropertyView.objects.select_related('cycle').filter(
                property_id=base_view.get().property_id,
                cycle__organization_id=organization_id
            ).order_by('-cycle__start')
            for linked_view in linked_views:
                state_data = PropertyStateSerializer(
                    linked_view.state,
                    all_extra_data_columns=all_extra_data_columns
                ).data

                state_data['cycle_id'] = linked_view.cycle.id
                state_data['view_id'] = linked_view.id
                result['data'].append(state_data)

            return JsonResponse(result, encoder=PintJSONEncoder, status=status.HTTP_200_OK)
        else:
            result = {
                'status': 'error',
                'message': 'property view with id {} does not exist in given organization'.format(pk)
            }
            return JsonResponse(result)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=no_body
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['POST'])
    def match_merge_link(self, request, pk=None):
        """
        Runs match merge link for an individual property.

        Note that this method can return a view_id of None if the given -View
        was not involved in a merge.
        """
        org_id = self.get_organization(request)

        property_view = PropertyView.objects.get(
            pk=pk,
            cycle__organization_id=org_id
        )
        merge_count, link_count, view_id = match_merge_link(property_view.id, 'PropertyState')

        result = {
            'view_id': view_id,
            'match_merged_count': merge_count,
            'match_link_count': link_count,
        }

        return JsonResponse(result)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'taxlot_id',
                required=True,
                description='The taxlot id to pair up with this property',
            ),
        ],
        request_body=no_body,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['PUT'])
    def pair(self, request, pk=None):
        """
        Pair a taxlot to this property
        """
        organization_id = int(self.get_organization(request))
        property_id = int(pk)
        taxlot_id = int(request.query_params.get('taxlot_id'))
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, True)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'taxlot_id',
                required=True,
                description='The taxlot id to unpair from this property',
            ),
        ],
        request_body=no_body,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['PUT'])
    def unpair(self, request, pk=None):
        """
        Unpair a taxlot from this property
        """
        organization_id = int(self.get_organization(request))
        property_id = int(pk)
        taxlot_id = int(request.query_params.get('taxlot_id'))
        return pair_unpair_property_taxlot(property_id, taxlot_id, organization_id, False)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer']
            },
            required=['property_view_ids'],
            description='A list of property view ids to delete')
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['DELETE'])
    def batch_delete(self, request):
        """
        Batch delete several properties
        """
        org_id = self.get_organization(request)

        property_view_ids = request.data.get('property_view_ids', [])
        property_state_ids = PropertyView.objects.filter(
            id__in=property_view_ids,
            cycle__organization_id=org_id
        ).values_list('state_id', flat=True)
        resp = PropertyState.objects.filter(pk__in=Subquery(property_state_ids)).delete()

        if resp[0] == 0:
            return JsonResponse({'status': 'warning', 'message': 'No action was taken'})

        return JsonResponse({'status': 'success', 'properties': resp[1]['seed.PropertyState']})

    def _get_property_view(self, pk):
        """
        Return the property view

        :param pk: id, The property view ID
        :param cycle_pk: cycle
        :return:
        """
        try:
            property_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                id=pk,
                property__organization_id=self.get_organization(self.request)
            )
            result = {
                'status': 'success',
                'property_view': property_view
            }
        except PropertyView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'property view with id {} does not exist'.format(pk)
            }
        return result

    def _get_taxlots(self, pk):
        lot_view_pks = TaxLotProperty.objects.filter(property_view_id=pk).values_list(
            'taxlot_view_id', flat=True)
        lot_views = TaxLotView.objects.filter(pk__in=lot_view_pks).select_related('cycle', 'state').prefetch_related('labels')
        lots = []
        for lot in lot_views:
            lots.append(TaxLotViewSerializer(lot).data)
        return lots

    def get_history(self, property_view):
        """Return history in reverse order"""

        # access the history from the property state
        history, master = property_view.state.history()

        # convert the history and master states to StateSerializers
        master['state'] = PropertyStateSerializer(master['state_data']).data
        del master['state_data']
        del master['state_id']

        for h in history:
            h['state'] = PropertyStateSerializer(h['state_data']).data
            del h['state_data']
            del h['state_id']

        return history, master

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    def retrieve(self, request, pk=None):
        """
        Get property details
        """
        result = self._get_property_view(pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            result = {'status': 'success'}
            result.update(PropertyViewSerializer(property_view).data)
            # remove PropertyView id from result
            result.pop('id')

            # Grab extra_data columns to be shown in the result
            organization_id = self.get_organization(request)
            all_extra_data_columns = Column.objects.filter(
                organization_id=organization_id,
                is_extra_data=True,
                table_name='PropertyState').values_list('column_name', flat=True)

            result['state'] = PropertyStateSerializer(property_view.state,
                                                      all_extra_data_columns=all_extra_data_columns).data
            result['taxlots'] = self._get_taxlots(property_view.pk)
            result['history'], master = self.get_history(property_view)
            result = update_result_with_master(result, master)
            return JsonResponse(result, encoder=PintJSONEncoder, status=status.HTTP_200_OK)
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=UpdatePropertyPayloadSerializer,
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk=None):
        """
        Update a property and run the updated record through a match and merge
        round within it's current Cycle.
        """
        data = request.data

        result = self._get_property_view(pk)
        if result.get('status', None) != 'error':
            property_view = result.pop('property_view')
            property_state_data = PropertyStateSerializer(property_view.state).data

            # get the property state information from the request
            new_property_state_data = data['state']

            # set empty strings to None
            for key, val in new_property_state_data.items():
                if val == '':
                    new_property_state_data[key] = None

            changed_fields, previous_data = get_changed_fields(property_state_data, new_property_state_data)
            if not changed_fields:
                result.update(
                    {'status': 'success', 'message': 'Records are identical'}
                )
                return JsonResponse(result, status=status.HTTP_204_NO_CONTENT)
            else:
                # Not sure why we are going through the pain of logging this all right now... need to
                # reevaluate this.
                log = PropertyAuditLog.objects.select_related().filter(
                    state=property_view.state
                ).order_by('-id').first()

                # if checks above pass, create an exact copy of the current state for historical purposes
                if log.name == 'Import Creation':
                    # Add new state by removing the existing ID.
                    property_state_data.pop('id')
                    # Remove the import_file_id for the first edit of a new record
                    # If the import file has been deleted and this value remains the serializer won't be valid
                    property_state_data.pop('import_file')
                    new_property_state_serializer = PropertyStateSerializer(
                        data=property_state_data
                    )
                    if new_property_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving relationships
                        new_state = new_property_state_serializer.save()

                        # Since we are creating a new relationship when we are manually editing the Properties, then
                        # we need to move the relationships over to the new manually edited record.
                        new_state = self._move_relationships(property_view.state, new_state)
                        new_state.save()

                        # then assign this state to the property view and save the whole view
                        property_view.state = new_state
                        property_view.save()

                        PropertyAuditLog.objects.create(organization=log.organization,
                                                        parent1=log,
                                                        parent2=None,
                                                        parent_state1=log.state,
                                                        parent_state2=None,
                                                        state=new_state,
                                                        name='Manual Edit',
                                                        description=None,
                                                        import_filename=log.import_filename,
                                                        record_type=AUDIT_USER_EDIT)

                        result.update(
                            {'state': new_property_state_serializer.data}
                        )

                        # save the property view so that the datetime gets updated on the property.
                        property_view.save()
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                new_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                # redo assignment of this variable in case this was an initial edit
                property_state_data = PropertyStateSerializer(property_view.state).data

                if 'extra_data' in new_property_state_data:
                    property_state_data['extra_data'].update(
                        new_property_state_data['extra_data']
                    )

                property_state_data.update(
                    {k: v for k, v in new_property_state_data.items() if k != 'extra_data'}
                )

                log = PropertyAuditLog.objects.select_related().filter(
                    state=property_view.state
                ).order_by('-id').first()

                if log.name in ['Manual Edit', 'Manual Match', 'System Match', 'Merge current state in migration']:
                    # Convert this to using the serializer to save the data. This will override the previous values
                    # in the state object.

                    # Note: We should be able to use partial update here and pass in the changed fields instead of the
                    # entire state_data.
                    updated_property_state_serializer = PropertyStateSerializer(
                        property_view.state,
                        data=property_state_data
                    )
                    if updated_property_state_serializer.is_valid():
                        # create the new property state, and perform an initial save / moving
                        # relationships
                        updated_property_state_serializer.save()

                        result.update(
                            {'state': updated_property_state_serializer.data}
                        )

                        # save the property view so that the datetime gets updated on the property.
                        property_view.save()

                        Note.create_from_edit(request.user.id, property_view, new_property_state_data, previous_data)

                        merge_count, link_count, view_id = match_merge_link(property_view.id, 'PropertyState')

                        result.update({
                            'view_id': view_id,
                            'match_merged_count': merge_count,
                            'match_link_count': link_count,
                        })

                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_200_OK)
                    else:
                        result.update({
                            'status': 'error',
                            'message': 'Invalid update data with errors: {}'.format(
                                updated_property_state_serializer.errors)}
                        )
                        return JsonResponse(result, encoder=PintJSONEncoder,
                                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                else:
                    result = {
                        'status': 'error',
                        'message': 'Unrecognized audit log name: ' + log.name
                    }
                    return JsonResponse(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            return JsonResponse(result, status=status.HTTP_404_NOT_FOUND)

    def _get_property_view_for_property(self, pk, cycle_pk):
        """
        Return a property view based on the property id and cycle
        :param pk: ID of property (not property view)
        :param cycle_pk: ID of the cycle
        :return: dict, propety view and status
        """
        try:
            property_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(
                property_id=pk,
                cycle_id=cycle_pk,
                property__organization_id=self.get_organization(self.request)
            )
            result = {
                'status': 'success',
                'property_view': property_view
            }
        except PropertyView.DoesNotExist:
            result = {
                'status': 'error',
                'message': 'property view with property id {} does not exist'.format(pk)
            }
        except PropertyView.MultipleObjectsReturned:
            result = {
                'status': 'error',
                'message': 'Multiple property views with id {}'.format(pk)
            }
        return result

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'profile_id',
                required=True,
                description='ID of a BuildingSync ColumnMappingProfile'
            ),
        ]
    )
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def building_sync(self, request, pk):
        """
        Return BuildingSync representation of the property
        """
        profile_pk = request.GET.get('profile_id')
        org_id = self.get_organization(self.request)
        try:
            profile_pk = int(profile_pk)
            column_mapping_profile = ColumnMappingProfile.objects.get(
                pk=profile_pk,
                profile_type__in=[ColumnMappingProfile.BUILDINGSYNC_DEFAULT, ColumnMappingProfile.BUILDINGSYNC_CUSTOM])
        except TypeError:
            return JsonResponse({
                'success': False,
                'message': 'Query param `profile_id` is either missing or invalid'
            }, status=status.HTTP_400_BAD_REQUEST)
        except ColumnMappingProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Cannot find a BuildingSync ColumnMappingProfile with pk={profile_pk}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            property_view = (PropertyView.objects.select_related('state')
                             .get(pk=pk, cycle__organization_id=org_id))
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s' % pk
            }, status=status.HTTP_400_BAD_REQUEST)

        bs = BuildingSync()
        # Check if there is an existing BuildingSync XML file to merge
        bs_file = property_view.state.building_files.order_by('created').last()
        if bs_file is not None and os.path.exists(bs_file.file.path):
            bs.import_file(bs_file.file.path)

        try:
            xml = bs.export_using_profile(property_view.state, column_mapping_profile.mappings)
            return HttpResponse(xml, content_type='application/xml')
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()]
    )
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def hpxml(self, request, pk):
        """
        Return HPXML representation of the property
        """
        org_id = self.get_organization(self.request)
        try:
            property_view = (PropertyView.objects.select_related('state')
                             .get(pk=pk, cycle__organization_id=org_id))
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cannot match a PropertyView with pk=%s' % pk
            })

        hpxml = HPXML()
        # Check if there is an existing BuildingSync XML file to merge
        hpxml_file = (property_view.state.building_files
                      .filter(file_type=BuildingFile.HPXML)
                      .order_by('-created')
                      .first())
        if hpxml_file is not None and os.path.exists(hpxml_file.file.path):
            hpxml.import_file(hpxml_file.file.path)
            xml = hpxml.export(property_view.state)
            return HttpResponse(xml, content_type='application/xml')
        else:
            # create a new XML from the record, do not import existing XML
            xml = hpxml.export(property_view.state)
            return HttpResponse(xml, content_type='application/xml')

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.path_id_field(
                description='ID of the property view to update'
            ),
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle_id',
                required=True,
                description='ID of the cycle of the property view'
            ),
            AutoSchemaHelper.upload_file_field(
                'file',
                required=True,
                description='BuildingSync file to use',
            ),
            AutoSchemaHelper.form_string_field(
                'file_type',
                required=True,
                description='Either "Unknown" or "BuildingSync"',
            ),
        ],
        request_body=no_body,
    )
    @action(detail=True, methods=['PUT'], parser_classes=(MultiPartParser,))
    @has_perm_class('can_modify_data')
    def update_with_building_sync(self, request, pk):
        """
        Update an existing PropertyView with a building file. Currently only supports BuildingSync.
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        the_file = request.data['file']
        file_type = BuildingFile.str_to_file_type(request.data.get('file_type', 'Unknown'))
        organization_id = self.get_organization(request)
        cycle_pk = request.query_params.get('cycle_id', None)
        org_id = self.get_organization(self.request)

        try:
            cycle = Cycle.objects.get(pk=cycle_pk, organization_id=org_id)
        except Cycle.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is missing or Cycle does not exist"
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            # note that this is a "safe" query b/c we should have already returned
            # if the cycle was not within the user's organization
            property_view = PropertyView.objects.select_related(
                'property', 'cycle', 'state'
            ).get(pk=pk, cycle_id=cycle_pk)
        except PropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'property view does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        p_status = False
        new_pv_state = None
        building_file = BuildingFile.objects.create(
            file=the_file,
            filename=the_file.name,
            file_type=file_type,
        )

        # passing in the existing propertyview allows it to process the buildingsync file and attach it to the
        # existing propertyview.
        p_status, new_pv_state, new_pv_view, messages = building_file.process(
            organization_id, cycle, property_view=property_view
        )

        if p_status and new_pv_state:
            return JsonResponse({
                'success': True,
                'status': 'success',
                'message': 'successfully imported file',
                'data': {
                    'property_view': PropertyViewAsStateSerializer(new_pv_view).data,
                },
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': "Could not process building file with messages {}".format(messages)
            }, status=status.HTTP_400_BAD_REQUEST)


def diffupdate(old, new):
    """Returns lists of fields changed"""
    changed_fields = []
    changed_extra_data = []
    for k, v in new.items():
        if old.get(k, None) != v or k not in old:
            changed_fields.append(k)
    if 'extra_data' in changed_fields:
        changed_fields.remove('extra_data')
        changed_extra_data, _ = diffupdate(old['extra_data'], new['extra_data'])
    return changed_fields, changed_extra_data
