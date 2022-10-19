# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.
:author Paul Munday <paul@paulmunday.net>
:author Nicholas Long  <nicholas.long@nrel.gov>
"""
import json
from collections import OrderedDict

import pytz
from django.db import models
from past.builtins import basestring
from rest_framework import serializers
from rest_framework.fields import empty

from seed.models import (
    AUDIT_USER_CREATE,
    AUDIT_USER_EDIT,
    GreenAssessmentProperty,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLotProperty,
    TaxLotView
)
from seed.serializers.building_file import BuildingFileSerializer
from seed.serializers.certification import (
    GreenAssessmentPropertyReadOnlySerializer
)
from seed.serializers.inventory_document import InventoryDocumentSerializer
from seed.serializers.measures import PropertyMeasureSerializer
from seed.serializers.pint import PintQuantitySerializerField
from seed.serializers.scenarios import ScenarioSerializer
from seed.serializers.taxlots import TaxLotViewSerializer
from seed.utils.api import OrgMixin, ProfileIdMixin

CYCLE_FIELDS = ['id', 'name', 'start', 'end', 'created']

# Need to reevaluate this list of fields that are being removed.
# I would really like to keep this logic in the serializers and not here.
PROPERTY_STATE_FIELDS = [
    field.name for field in PropertyState._meta.get_fields()
]
REMOVE_FIELDS = [field for field in PROPERTY_STATE_FIELDS
                 if field.startswith('propertyauditlog__')]
# eventually we can remove the measures, building_file, and property_state as soon as we remove
# the use of PVFIELDS... someday
REMOVE_FIELDS.extend(['organization', 'import_file', 'measures', 'building_files', 'scenarios'])
for field in REMOVE_FIELDS:
    PROPERTY_STATE_FIELDS.remove(field)
PROPERTY_STATE_FIELDS.extend(['organization_id', 'import_file_id'])

PVFIELDS = ['state__{}'.format(f) for f in PROPERTY_STATE_FIELDS]
PVFIELDS.extend(['cycle__{}'.format(f) for f in CYCLE_FIELDS])
PVFIELDS.extend(['id', 'property_id'])


class PropertyLabelsField(serializers.RelatedField):
    def to_representation(self, value):
        return value.id


class PropertyAuditLogReadOnlySerializer(serializers.BaseSerializer):
    """Read only serializer for representing PropertyState History"""

    def to_representation(self, obj):
        """Show history"""
        if obj.record_type == AUDIT_USER_EDIT:
            try:
                changed_fields = json.loads(obj.description)
                description = 'User edit'
            except ValueError:
                changed_fields = None
                description = obj.description
        else:
            changed_fields = None
            description = obj.description
        return {
            'state': PropertyStateSerializer(obj.state).data,
            'date_edited': obj.created.ctime(),
            'source': obj.get_record_type_display(),
            'filename': obj.import_filename,
            'changed_fields': changed_fields,
            'description': str(description)
        }


class PropertyListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        """Overwritten to optimize fetching of Labels"""
        if isinstance(data, models.Manager):
            iterable = data.all().prefetch_related('parent_property')
        else:
            iterable = data
        result = []
        for item in iterable:
            representation = self.child.to_representation(item)
            result.append(representation)
        return result


class PropertySerializer(serializers.ModelSerializer):
    # The created and updated fields are in UTC time and need to be casted accordingly in this format
    created = serializers.DateTimeField("%Y-%m-%dT%H:%M:%S.%fZ", default_timezone=pytz.utc, read_only=True)
    updated = serializers.DateTimeField("%Y-%m-%dT%H:%M:%S.%fZ", default_timezone=pytz.utc, read_only=True)

    inventory_documents = InventoryDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = '__all__'
        extra_kwargs = {
            'organization': {'read_only': True}
        }

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = PropertyMinimalSerializer()
        return PropertyListSerializer(*args, **kwargs)


class PropertyMinimalSerializer(serializers.ModelSerializer):
    """Define fields to avoid label lookup"""

    class Meta:
        model = Property
        fields = ['id', 'campus', 'parent_property']
        extra_kwargs = {
            'organization': {'read_only': True}
        }


class PropertyStateSerializer(serializers.ModelSerializer):
    extra_data = serializers.JSONField(required=False)
    measures = PropertyMeasureSerializer(source='propertymeasure_set', many=True, read_only=True)
    scenarios = ScenarioSerializer(many=True, read_only=True)
    files = BuildingFileSerializer(source='building_files', many=True, read_only=True)

    # support the pint objects
    conditioned_floor_area = PintQuantitySerializerField(allow_null=True)
    gross_floor_area = PintQuantitySerializerField(allow_null=True)
    occupied_floor_area = PintQuantitySerializerField(allow_null=True)
    site_eui = PintQuantitySerializerField(allow_null=True)
    site_eui_modeled = PintQuantitySerializerField(allow_null=True)
    source_eui_weather_normalized = PintQuantitySerializerField(allow_null=True)
    source_eui = PintQuantitySerializerField(allow_null=True)
    source_eui_modeled = PintQuantitySerializerField(allow_null=True)
    site_eui_weather_normalized = PintQuantitySerializerField(allow_null=True)
    total_ghg_emissions = PintQuantitySerializerField(allow_null=True)
    total_marginal_ghg_emissions = PintQuantitySerializerField(allow_null=True)
    total_ghg_emissions_intensity = PintQuantitySerializerField(allow_null=True)
    total_marginal_ghg_emissions_intensity = PintQuantitySerializerField(allow_null=True)

    # support naive datetime objects
    generation_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True)
    recent_sale_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True)
    release_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True)

    # to support the old state serializer method with the PROPERTY_STATE_FIELDS variables
    import_file_id = serializers.IntegerField(allow_null=True, read_only=True)
    organization_id = serializers.IntegerField()

    class Meta:
        model = PropertyState
        fields = '__all__'
        extra_kwargs = {
            'organization': {'read_only': True}
        }

    def __init__(self, instance=None, data=empty, all_extra_data_columns=None, show_columns=None, **kwargs):
        """
        If show_columns is passed, then all_extra_data_columns is not needed since the extra_data columns are embedded
        in the show_columns.

        TODO: remove the use of all_extra_data_columns.

        :param instance: instance to serialize
        :param data: initial data
        :param all_extra_data_columns:
        :param show_columns: dict of list, Which columns to show in the form of c['fields']=[] and c['extra_data'].
        """
        if show_columns is not None:
            self.all_extra_data_columns = show_columns['extra_data']
        else:
            self.all_extra_data_columns = all_extra_data_columns

        super().__init__(instance=instance, data=data, **kwargs)

        # remove the fields to display based on the show_columns list.
        if show_columns is not None:
            for field_name in set(self.fields) - set(show_columns['fields']):
                self.fields.pop(field_name)

    def to_representation(self, data):
        """Overwritten to handle time conversion and extra_data null fields"""
        result = super().to_representation(data)

        # Prepopulate the extra_data columns with a default of None so that they will appear in the result
        # This will also handle the passing of the show_columns extra data list. If the show_columns isn't
        # requiring a column, then it won't show up here.
        if self.all_extra_data_columns and data.extra_data:
            prepopulated_extra_data = {
                col_name: data.extra_data.get(col_name, None) for col_name in self.all_extra_data_columns
            }

            result['extra_data'] = prepopulated_extra_data

        return result


class PropertyStateWritableSerializer(serializers.ModelSerializer):
    """
    Used by PropertyViewAsState as a nested serializer

    This serializer is for use with the PropertyViewAsStateSerializer such that
    PropertyState can be created and updated through a single call to the
    associated PropertyViewViewSet.
    """
    extra_data = serializers.JSONField(required=False)
    measures = PropertyMeasureSerializer(source='propertymeasure_set', many=True, read_only=True)
    scenarios = ScenarioSerializer(many=True, read_only=True)
    files = BuildingFileSerializer(source='building_files', many=True, read_only=True)

    # to support the old state serializer method with the PROPERTY_STATE_FIELDS variables
    import_file_id = serializers.IntegerField(allow_null=True, read_only=True)
    organization_id = serializers.IntegerField(read_only=True)

    # support naive datetime objects
    # support naive datetime objects
    generation_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True, required=False)
    recent_sale_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True, required=False)
    release_date = serializers.DateTimeField('%Y-%m-%dT%H:%M:%S', allow_null=True, required=False)

    # support the pint objects
    conditioned_floor_area = PintQuantitySerializerField(allow_null=True, required=False)
    gross_floor_area = PintQuantitySerializerField(allow_null=True, required=False)
    occupied_floor_area = PintQuantitySerializerField(allow_null=True, required=False)
    site_eui = PintQuantitySerializerField(allow_null=True, required=False)
    site_eui_modeled = PintQuantitySerializerField(allow_null=True, required=False)
    source_eui_weather_normalized = PintQuantitySerializerField(allow_null=True, required=False)
    source_eui = PintQuantitySerializerField(allow_null=True, required=False)
    source_eui_modeled = PintQuantitySerializerField(allow_null=True, required=False)
    site_eui_weather_normalized = PintQuantitySerializerField(allow_null=True, required=False)
    total_ghg_emissions = PintQuantitySerializerField(allow_null=True, required=False)
    total_marginal_ghg_emissions = PintQuantitySerializerField(allow_null=True, required=False)
    total_ghg_emissions_intensity = PintQuantitySerializerField(allow_null=True, required=False)
    total_marginal_ghg_emissions_intensity = PintQuantitySerializerField(allow_null=True, required=False)

    class Meta:
        fields = '__all__'
        model = PropertyState


class PropertyViewSerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = PropertyLabelsField(read_only=True, many=True)

    state = PropertyStateSerializer()
    property = PropertySerializer()

    class Meta:
        model = PropertyView
        depth = 1
        fields = ('id', 'cycle', 'state', 'property', 'labels')


class PropertyViewListSerializer(serializers.ListSerializer, OrgMixin, ProfileIdMixin):
    """When serializing Property View as a list, omit history."""

    def to_representation(self, data):
        """Overridden to optimize db calls."""

        # Not sure when the data is a models.Manager or a QuerySet. It seems
        # like this method, in general, is going to cause a bunch of issues as we
        # extend the data model.
        # NL: Extending this method to add in profile_id lookup
        if isinstance(data, (models.Manager, models.QuerySet)):
            iterable = data.all().values(*PVFIELDS)
            view_ids = []
            results = []
            for row in iterable:
                view_ids.append(row['id'])
                results.append(unflatten_values(row, ['state', 'cycle']))
        else:
            iterable = data
            view_ids = [view.id for view in iterable]
            results = []

            # grab the organization and profile_id. In testing the context is none in some cases.
            if self.context.get('request') is not None:
                org_id = self.get_organization(self.context['request'])
                profile_id = self.context['request'].query_params.get('profile_id', None)
                show_columns = self.get_show_columns(org_id, profile_id)
            else:
                show_columns = None

            for item in iterable:
                cycle = [
                    (field, getattr(item.cycle, field, None)) for field in CYCLE_FIELDS
                ]
                cycle = OrderedDict(cycle)
                state = PropertyStateSerializer(
                    item.state,
                    show_columns=show_columns
                ).data
                representation = OrderedDict((
                    ('id', item.id),
                    ('property', item.property_id),
                    ('created', item.property.created),
                    ('updated', item.property.updated),
                    ('state', state),
                    ('cycle', cycle),
                ))
                results.append(representation)
        certifications = GreenAssessmentProperty.objects.filter(
            view__in=view_ids
        ).prefetch_related('assessment', 'urls', 'view')
        certset = {}
        for certification in certifications:
            record = certset.setdefault(certification.view_id, [])
            record.append(
                GreenAssessmentPropertyReadOnlySerializer(certification).data
            )
        for row in results:
            row['certifications'] = certset.get(row['id'], None)
        return results


class PropertyViewAsStateSerializer(serializers.ModelSerializer):
    """Serialize PropertyView as Underlying PropertyState"""

    state = PropertyStateWritableSerializer()
    certifications = serializers.SerializerMethodField(read_only=True)
    org_id = serializers.IntegerField(write_only=True)

    changed_fields = serializers.SerializerMethodField(read_only=True)
    date_edited = serializers.SerializerMethodField(read_only=True)
    filename = serializers.SerializerMethodField(read_only=True)
    history = serializers.SerializerMethodField(read_only=True)
    source = serializers.SerializerMethodField(read_only=True)
    taxlots = serializers.SerializerMethodField(read_only=True)

    created = serializers.SerializerMethodField(read_only=True)
    updated = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PropertyView
        validators = []  # type: ignore[var-annotated]
        fields = ('id', 'state', 'property', 'cycle',
                  'changed_fields', 'date_edited',
                  'certifications', 'filename', 'history',
                  'org_id', 'source', 'taxlots', 'created', 'updated')

    def __init__(self, instance=None, data=empty, **kwargs):
        """Override __init__ to get audit logs if instance is passed"""
        if instance and isinstance(instance, PropertyView):
            self._audit_logs = PropertyAuditLog.objects.select_related('state').filter(
                view=instance).order_by('-created', '-state_id')
            current = self._audit_logs.filter(state=instance.state).first()
            self.current = PropertyAuditLogReadOnlySerializer(current).data if current else {}
        else:
            self.current = {}
        super().__init__(instance=instance, data=data, **kwargs)

    def to_internal_value(self, data):
        """Serialize state"""
        self._validate(data)
        data = data.copy()
        state = data.pop('state', None)
        org_id = conv_value(data.pop('org_id', None))
        if state:
            if isinstance(state, (list, tuple)):
                state = state[0]
            try:
                state = int(state)
                state_obj = PropertyState.objects.get(id=state)
                state = PropertyStateWritableSerializer(
                    instance=state_obj
                ).data
            except TypeError:
                pass  # already a PropertyStateWritableSerializer object
            required = True if self.context['request'].method in ['PUT', 'POST'] else False
            org = state.get('organization')
            org_id = org if org else org_id
            if not org_id and required:
                raise serializers.ValidationError(
                    {'org_id': 'state supplied without organization or org_id'}
                )
            if org_id:
                try:
                    org_id = int(org_id)
                except TypeError:
                    raise serializers.ValidationError(
                        {'org_id': 'invalid type'}
                    )
            state['organization'] = org_id
            data['state'] = state
        return data

    def _validate(self, data):
        required_fields = ('state', 'property', 'cycle', 'org_id')
        unique_together = PropertyView._meta.unique_together
        missing = []
        wrong_type = []
        unique = []
        required = True if self.context['request'].method in [
            'PUT', 'POST'
        ] else False
        if required:
            for field in required_fields:
                if field not in required_fields:
                    missing.append(field)
        # type validation
        for field in required_fields:
            if field != 'state':  # state is a writeable serializer field
                if data.get(field) and not isinstance(data[field], (basestring, int)):
                    wrong_type.append((field, type(field)))
        for fields in unique_together:
            field_vals = {}
            for field in fields:
                field_vals[field] = conv_value(data.get(field))
                # only applies when updating via PATCH
                if not field_vals[field] and self.instance:
                    field_vals[field] = getattr(self.instance, field)
            if self.instance:
                query = PropertyView.objects.filter(
                    **field_vals
                ).exclude(pk=self.instance.pk)
            else:
                query = PropertyView.objects.filter(**field_vals)
            if query.exists():
                unique.append("({})".format(", ".join(fields)))
        errors = {}
        if missing:
            msg = "Required fields are missing: {}".format(
                ", ".join(missing)
            )
            errors['missing'] = msg
        if wrong_type:
            wrong_type = [
                "{}({})".format(
                    field, "json dict/int" if field == "state" else 'int'
                ) for field in wrong_type
            ]
            msg = "Fields are wrong type: {}".format(
                ", ".join(wrong_type)
            )
            errors['wrong_type'] = msg
        if unique:
            msg = "Unique together constraint violated for: {}".format(unique)
            errors['unique'] = msg
        if errors:
            raise serializers.ValidationError(detail=errors)

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = PropertyViewSerializer()
        return PropertyViewListSerializer(*args, **kwargs)

    def create(self, validated_data):
        """Override create to add state"""
        state = validated_data.pop('state')
        property_id = conv_value(validated_data.pop('property'))
        validated_data['property_id'] = property_id
        cycle_id = conv_value(validated_data.pop('cycle'))
        validated_data['cycle_id'] = cycle_id
        new_property_state_serializer = PropertyStateWritableSerializer(data=state)
        if new_property_state_serializer.is_valid(raise_exception=True):
            new_state = new_property_state_serializer.save()
        instance = PropertyView.objects.create(
            state=new_state, **validated_data
        )
        PropertyAuditLog.objects.create(
            organization_id=instance.property.organization_id,
            state=instance.state, view=instance,
            record_type=AUDIT_USER_CREATE, description='Initial audit log'
        )
        return instance

    def update(self, instance, validated_data):
        """Override update to add state"""
        state = validated_data.pop('state', None)
        if state:
            audit_log = {
                'state': instance.state,
                'view': instance,
                'organization_id': instance.property.organization_id
            }
            # update existing state if PATCH
            if self.context['request'].method == 'PATCH':
                property_state_serializer = PropertyStateWritableSerializer(
                    instance.state, data=state
                )
                description = 'Updated via API PATCH call'
                record_type = AUDIT_USER_EDIT
            # otherwise create a new state
            else:
                property_state_serializer = PropertyStateWritableSerializer(data=state)
                description = '["state"]'
                record_type = AUDIT_USER_CREATE
            if property_state_serializer.is_valid():
                new_state = property_state_serializer.save()
                instance.state = new_state
                audit_log.update(
                    {'description': description, 'record_type': record_type}
                )
                self.update_state_audit_log(new_state, **audit_log)
        cycle_id = conv_value(validated_data.pop('cycle', None))
        if cycle_id:
            instance.cycle_id = cycle_id
        property_id = conv_value(validated_data.pop('property', None))
        if property_id:
            instance.property_id = property_id
        instance.save()
        return instance

    # pylint:disable=unused-argument
    def get_certifications(self, obj):
        """Get certifications(GreenAssessments)"""
        certifications = GreenAssessmentProperty.objects.filter(
            view=obj
        ).prefetch_related('assessment', 'urls')
        return [
            GreenAssessmentPropertyReadOnlySerializer(cert).data
            for cert in certifications
        ]

    def get_changed_fields(self, obj):
        """Get fields changed on state, if any."""
        return self.current.get('changed_fields', None)

    def get_date_edited(self, obj):
        """Get date last edited, if any."""
        return self.current.get('date_edited', None)

    def get_filename(self, obj):
        """Get import filename, if any."""
        return self.current.get('filename', None)

    def get_history(self, obj):
        """Historic audit logs."""
        history = self._audit_logs.exclude(
            state=obj.state
        ) if hasattr(self, '_audit_logs') else None
        return [
            PropertyAuditLogReadOnlySerializer(log).data for log in history
        ] if history else None

    def get_source(self, obj):
        """Get (import) source."""
        return self.current.get('source', None)

    def get_taxlots(self, obj):
        """Get associated taxlots"""
        lot_view_pks = TaxLotProperty.objects.filter(
            property_view_id=obj.id
        ).values_list('taxlot_view_id', flat=True)

        lot_views = TaxLotView.objects.filter(
            pk__in=lot_view_pks
        ).select_related('cycle', 'state')
        return [
            TaxLotViewSerializer(lot).data for lot in lot_views
        ] if lot_views else None

    def get_created(self, obj):
        """Return the Property creation as string"""
        return obj.property.created

    def get_updated(self, obj):
        """Return the Property creation as string"""
        return obj.property.updated

    def update_state_audit_log(self, new_state, **kwargs):
        state = kwargs.pop('state')
        view_audit_log = PropertyAuditLog.objects.filter(
            state=state
        ).first()
        if not view_audit_log:
            kwargs.update(
                {'description': "Initial audit log added on update."}
            )

        audit_log = PropertyAuditLog.objects.create(
            parent1=view_audit_log,
            parent_state1=state,
            state=new_state,
            **kwargs
        )
        return audit_log


class UpdatePropertyPayloadSerializer(serializers.Serializer):
    state = PropertyStateSerializer()


def conv_value(val):
    """Convert value to correct format"""
    # swagger makes everything lists
    if isinstance(val, (list, tuple)):
        val = val[0]
    # convert to int, may throw value error
    if val:
        val = int(val)
    return val


def unflatten_values(vdict, fkeys):
    """
    Takes a dicts produced by values() that traverses foreign relationships
    (e.g., contains foreign_key__field) and converts them into a nested dict.
    so vdict[foreign_key__field] becomes vdict[foreign_key][field]

    It assumes values has been provided with foreignkey__field  e.g., state__city

    {'id':1,  'state__city': 'London'} -> {'id': 1, 'state':{'city': 'London'}}

    :param vdict: dict from list returned by e.g., Model.objects.all().values()
    :type vdict: dict
    :param fkeys: field names for foreign key (e.g., state for state__city)
    :type fkeys: list
    """
    assert set(list(vdict.keys())).isdisjoint(set(fkeys)), "unflatten_values: {} has fields named in {}".format(vdict,
                                                                                                                fkeys)
    idents = tuple(["{}__".format(fkey) for fkey in fkeys])
    newdict = vdict.copy()
    for key, val in vdict.items():
        if key.startswith(idents):
            fkey, new_key = key.split('__', 1)
            subdict = newdict.setdefault(fkey, {})
            subdict[new_key] = val
            newdict.pop(key)
    return newdict
