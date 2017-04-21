# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import types
import unicodedata

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django_pgjson.fields import JsonField

from seed.audit_logs.models import AuditLog, LOG
from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.managers.json import JsonManager
from seed.models import SEED_DATA_SOURCES
from seed.utils.generic import split_model_fields, obj_to_dict
from seed.utils.time import convert_datestr

BS_VALUES_LIST = [
    'pk',  # needed for matching not to blow up
    # 'tax_lot_id', # no longer on the propertystate
    'pm_property_id',
    'custom_id_1',
    'address_line_1',
]

SYSTEM_MATCH = 1
USER_MATCH = 2
POSSIBLE_MATCH = 3

SEED_MATCH_TYPES = (
    (SYSTEM_MATCH, 'System Match'),
    (USER_MATCH, 'User Match'),
    (POSSIBLE_MATCH, 'Possible Match'),
)


def find_canonical_building_values(org):
    """Get all canonical building snapshots' id info for an organization.

    :param org: Organization inst.

    :rtype: list of tuples, field values specified in BS_VALUES_LIST
        for all canonical buildings related to an organization.

    NB: This does not return a queryset!

    """
    users = org.users.all()
    return BuildingSnapshot.objects.filter(
        pk__in=CanonicalBuilding.objects.filter(
            canonical_snapshot__import_file__import_record__owner__in=users
        ).values_list('canonical_snapshot_id')
    ).distinct().values_list(*BS_VALUES_LIST)


def get_or_create_canonical(b1, b2=None):
    """Gets most trusted Canonical Building.

    :param b1: BuildingSnapshot model type.
    :param b2: BuildingSnapshot model type.
    :rtype: CanonicalBuilding inst. Will contain PK.

    NB: preference is given to existing snapshots' Canonical link.

    """
    canon = b1.canonical_building
    if not canon and b2:
        canon = b2.canonical_building
    if not canon:
        canon = CanonicalBuilding.objects.create()

    return canon


def initialize_canonical_building(snapshot, user_pk):
    """Called to create a CanonicalBuilding from a single snapshot.

    :param snapshot: BuildingSnapshot inst.
    :param user_pk: The user id of the user initiating the CanonicalBuilding

    """
    canon = get_or_create_canonical(snapshot)
    snapshot.canonical_building = canon
    snapshot.save()
    canon.canonical_snapshot = snapshot
    canon.save()
    # log the new building
    AuditLog.objects.create(
        user_id=user_pk,
        organization=snapshot.super_organization,
        action='create_building',
        action_note='Created building',
        content_object=canon,
        audit_type=LOG,
    )


def clean_canonicals(b1, b2, new_snapshot):
    """Make sure that we don't leave dead limbs in our tree.

    :param b1: BuildingSnapshot, parent 1
    :param b2: BuildingSnapshot, parent 2
    :param new_snapshot: BuildingSnapshot, child.

    """
    latest_canon = new_snapshot.canonical_building
    for p in [b1, b2]:
        canon = p.canonical_building
        if canon and latest_canon and canon.pk != latest_canon.pk:
            canon.active = False
            canon.save()

# def get_building_attrs(data_set_buildings):
#     mapping = seed_mappings.BuildingSnapshot_to_BuildingSnapshot
#     return get_attrs_with_mapping(data_set_buildings, mapping)
#
#
# def save_snapshot_match(b1_pk, b2_pk, confidence=None, user=None,
#                         match_type=None, default_pk=None):
#     """Saves a match between two models as a new snapshot; updates Canonical.
#
#     :param b1_pk: int, id for building snapshot.
#     :param b2_pk: int, id for building snapshot.
#     :param confidence: (optional) float, likelihood that two models are linked.
#     :param user: (optional) User inst, last_modified_by for BuildingSnapshot.
#     :rtype: BuildingSnapshot instance, post save.
#
#     Determines which Canonical link should be used. If ``canonical`` is
#     specified,
#     we're probably changing a building's Canonical link, so use that Canonical
#     Building. Otherwise, use the model we match against. If none exists,
#     create it.
#
#     Update mapped fields in the new snapshot, update canonical links.
#
#     """
#     from seed.mappings import mapper as seed_mapper
#
#     # No point in linking the same building together.
#     if b1_pk == b2_pk:
#         return
#
#     default_pk = default_pk or b1_pk
#
#     b1 = BuildingSnapshot.objects.get(pk=b1_pk)
#     b2 = BuildingSnapshot.objects.get(pk=b2_pk)
#
#     # we don't want to match in the middle of the tree, so get the tip
#     b1 = b1.tip
#     b2 = b2.tip
#
#     default_building = b1 if default_pk == b1_pk else b2
#
#     new_snapshot = BuildingSnapshot.objects.create()
#     new_snapshot, changes = seed_mapper.merge_building(
#         new_snapshot,
#         b1,
#         b2,
#         seed_mapper.get_building_attrs([b1, b2]),
#         conf=confidence,
#         default=default_building,
#         match_type=match_type
#     )
#
#     clean_canonicals(b1, b2, new_snapshot)
#
#     new_snapshot.last_modified_by = user
#
#     new_snapshot.meters.add(*b1.meters.all())
#     new_snapshot.meters.add(*b2.meters.all())
#     new_snapshot.super_organization = b1.super_organization
#     new_snapshot.super_organization = b2.super_organization
#
#     new_snapshot.save()
#
#     return new_snapshot, changes


def unmatch_snapshot_tree(building_pk):
    """May or may not obviate ``unmatch_snapshot``. Experimental.

    :param building_pk: int - Primary Key for a BuildingSnapshot.

    .. warning::

        ``unmatch_snapshot_tree`` potentially modifies *years* of
        merged data. Anything descended from the ``building_pk`` will
        be deleted. The intent is to completely separate ``building_pk``'s
        influence on the resultant canonical_snapshot. The user is saying
        that these are separate entities after all, yes?

    Basically, this function works by getting a merge order list of
    children from the perspective of ``building_pk`` and a list of parents
    from the perspective of leaf node in the child tree. We take the difference
    between these lists and call that the ``remaining_ancestors`` from which
    we reconstruct the merge tree for our CanonicalBuilding.

    ``building_pk`` either gets a reactivated CanonicalBuilding, or a new one.

    """
    root_coparent = BuildingSnapshot.objects.get(pk=building_pk)
    root = root_coparent.co_parent

    node = root
    children_to_murder = []
    coparents_to_keep = []

    if not root.canonical_building:
        new_canon = CanonicalBuilding.objects.create(
            canonical_snapshot=root
        )
        root.canonical_building = new_canon
        root.save()

    # create CanonicalBuilding for coparent that is about to be
    # unmatched
    if (
        not root_coparent.canonical_building or
        root_coparent.canonical_building is root.canonical_building
    ):
        new_canon = CanonicalBuilding.objects.create(
            canonical_snapshot=root_coparent
        )
        root_coparent.canonical_building = new_canon
        root_coparent.save()

        unmatched_canon = root_coparent.canonical_building
        unmatched_canon.active = True
        unmatched_canon.save()
    elif not root_coparent.canonical_building.active:
        unmatched_canon = root_coparent.canonical_building
        unmatched_canon.active = True
        unmatched_canon.canonical_snapshot = root_coparent
        unmatched_canon.save()

    # orphan sub-children from the unmatched snapshot and keep track
    # of which parents to merge back in to create new snapshots
    # without data from the unmatched snapshot; also keep track of the
    # snapshots we are orphaning so we can delete them later.
    while node.children.first():
        child = node.children.first()

        if node.co_parent:
            parent = node.co_parent
            if not (parent.pk == root_coparent.pk):
                coparents_to_keep.append(parent)
            for parent in child.parents.all():
                parent.children.remove(child)

        children_to_murder.append(child)
        node = child

    # delete all sub-children of the unmatched snapshot
    for child in children_to_murder:
        # If the child we're about to delete is set as the canonical snapshop,
        # we should update the canonical_building to point at a different node
        # if possible.
        canons_to_update = CanonicalBuilding.objects.filter(
            canonical_snapshot=child,
        )
        for cb in canons_to_update:
            sibling = cb.buildingsnapshot_set.exclude(
                pk=child.pk,
            ).first()
            if sibling:
                cb.canonical_snapshot = sibling.tip
                cb.save()
        child.delete()

    # re-merge parents whose children have been taken from them
    # bachelor = root
    newborn_child = None
    # for bereaved_parent in coparents_to_keep:
    # newborn_child, _ = save_snapshot_match(
    #     bachelor.pk, bereaved_parent.pk, default_pk=bereaved_parent.pk,
    # )
    # bachelor = newborn_child

    # set canonical_snapshot for root's canonical building
    tip = newborn_child or root
    canon = root.canonical_building
    canon.canonical_snapshot = tip
    canon.active = True
    canon.save()


class CanonicalManager(models.Manager):
    """Manager to add useful model filtering methods"""

    def get_queryset(self):
        """Return only active CanonicalBuilding rows."""
        return super(CanonicalManager, self).get_queryset().filter(
            active=True
        )


class CanonicalBuilding(models.Model):
    """
    One Table to rule them all, One Table to find them, One Table to bring
    them all and in the database bind them.
    """

    canonical_snapshot = models.ForeignKey(
        "BuildingSnapshot", blank=True, null=True, on_delete=models.SET_NULL
    )
    active = models.BooleanField(default=True)
    # Django API: relation to AuditLogs GFK, e.g. canon.audit_logs.all()
    audit_logs = GenericRelation(AuditLog)

    objects = CanonicalManager()
    raw_objects = models.Manager()

    labels = models.ManyToManyField('StatusLabel')
    # ManyToManyField(StatusLabel)

    def __unicode__(self):
        snapshot_pk = "None"
        if self.canonical_snapshot:
            snapshot_pk = self.canonical_snapshot.pk

        return u"pk: {0} - snapshot: {1} - active: {2}".format(
            self.pk,
            snapshot_pk,
            self.active
        )


class BuildingSnapshot(TimeStampedModel):
    """The periodical composite of a building from disparate data sources.

    Represents the best data between all the data sources for a given building,
    potentially merged together with other BuildingSnapshot instances'
    attribute values.

    Two BuildingSnapshots can create a child, forming a match between
    buildings. Thusly, a BuildingSnapshot's co-parent is the other parent of
    its child. The m2m field `children` with related name `parents` allow the
    traversal of the tree. A BuildingSnapshot can have one parent in
    the case where an edit to data was initiated by a user, and the original
    field is preserved (treating BuildingSnapshots as immutable objects) and
    a new BuildingSnapshot is created with the change.

    """

    super_organization = models.ForeignKey(
        SuperOrganization,
        blank=True,
        null=True,
        related_name='building_snapshots'
    )
    import_file = models.ForeignKey(ImportFile, null=True, blank=True)
    canonical_building = models.ForeignKey(
        CanonicalBuilding, blank=True, null=True, on_delete=models.SET_NULL
    )

    # Denormalized Data and sources.
    # e.g. which model does this denormalized data come from?

    tax_lot_id = models.CharField(
        max_length=128, null=True, blank=True, db_index=True
    )
    tax_lot_id_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    pm_property_id = models.CharField(
        max_length=128, null=True, blank=True, db_index=True
    )
    pm_property_id_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    custom_id_1 = models.CharField(
        max_length=128, null=True, blank=True, db_index=True
    )
    custom_id_1_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    lot_number = models.CharField(max_length=128, null=True, blank=True)
    lot_number_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    block_number = models.CharField(max_length=128, null=True, blank=True)
    block_number_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    # Tax IDs are often stuck in here.
    property_notes = models.TextField(null=True, blank=True)
    property_notes_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    year_ending = models.DateField(null=True, blank=True)
    year_ending_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    # e.g. 'Ward', 'Borough', 'Boro', etc.
    district = models.CharField(max_length=128, null=True, blank=True)
    district_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner = models.CharField(max_length=128, null=True, blank=True)
    owner_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner_email = models.CharField(max_length=128, null=True, blank=True)
    owner_email_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner_telephone = models.CharField(max_length=128, null=True, blank=True)
    owner_telephone_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner_address = models.CharField(max_length=128, null=True, blank=True)
    owner_address_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner_city_state = models.CharField(max_length=128, null=True, blank=True)
    owner_city_state_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    owner_postal_code = models.CharField(max_length=128, null=True, blank=True)
    owner_postal_code_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    property_name = models.CharField(max_length=255, null=True, blank=True)
    property_name_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    building_count = models.IntegerField(null=True, blank=True)
    building_count_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    gross_floor_area = models.FloatField(null=True, blank=True)
    gross_floor_area_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    address_line_1 = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    address_line_1_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    address_line_2 = models.CharField(
        max_length=255, null=True, blank=True, db_index=True
    )
    address_line_2_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    city = models.CharField(max_length=255, null=True, blank=True)
    city_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    postal_code = models.CharField(max_length=255, null=True, blank=True)
    postal_code_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    year_built = models.IntegerField(null=True, blank=True)
    year_built_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    recent_sale_date = models.DateTimeField(null=True, blank=True)
    recent_sale_date_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    energy_score = models.IntegerField(null=True, blank=True)
    energy_score_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    site_eui = models.FloatField(null=True, blank=True)
    site_eui_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    generation_date = models.DateTimeField(null=True, blank=True)
    generation_date_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    release_date = models.DateTimeField(null=True, blank=True)
    release_date_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    state_province = models.CharField(max_length=255, null=True, blank=True)
    state_province_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    site_eui_weather_normalized = models.FloatField(null=True, blank=True)
    site_eui_weather_normalized_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    source_eui = models.FloatField(null=True, blank=True)
    source_eui_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    source_eui_weather_normalized = models.FloatField(null=True, blank=True)
    source_eui_weather_normalized_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    energy_alerts = models.TextField(null=True, blank=True)
    energy_alerts_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    space_alerts = models.TextField(null=True, blank=True)
    space_alerts_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    building_certification = models.CharField(
        max_length=255, null=True, blank=True
    )
    building_certification_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    conditioned_floor_area = models.FloatField(null=True, blank=True)
    conditioned_floor_area_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    occupied_floor_area = models.FloatField(null=True, blank=True)
    occupied_floor_area_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    use_description = models.TextField(null=True, blank=True)
    use_description_source = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    # Need a field to indicate that a record is a duplicate of another.  Mainly
    # used for cleaning up.
    duplicate = models.ForeignKey(
        'BuildingSnapshot', related_name='+', null=True, blank=True
    )

    #
    # Meta Data
    #

    children = models.ManyToManyField(
        'BuildingSnapshot',
        blank=True,
        symmetrical=False,
        related_name='parents',
    )

    best_guess_confidence = models.FloatField(null=True, blank=True)
    best_guess_canonical_building = models.ForeignKey(
        'CanonicalBuilding', related_name='best_guess', blank=True, null=True
    )

    # This is set for composite BS instances.
    # 1 if system matched, 2 if manually matched.
    match_type = models.IntegerField(
        choices=SEED_MATCH_TYPES, null=True, blank=True, db_index=True
    )
    # How we determine which subset of `'BuildingSnapshot'` to bubble up.
    confidence = models.FloatField(null=True, blank=True, db_index=True)
    # Setting NULL/BLANK so we can use get_or_create.
    last_modified_by = models.ForeignKey(User, null=True, blank=True)
    # Tells us whether this is pulled from AS-Raw data, PM-Raw data, or BS.
    source_type = models.IntegerField(
        choices=SEED_DATA_SOURCES, null=True, blank=True, db_index=True
    )

    # None if Snapshot is not canonical, otherwise points to Dataset pk.
    canonical_for_ds = models.ForeignKey(
        ImportRecord, null=True, blank=True, related_name='+'
    )

    #
    # JSON data
    #

    # 'key' -> 'value'
    extra_data = JsonField(default={})
    # 'key' -> ['model', 'fk'], what was the model and its FK?
    extra_data_sources = JsonField(default={})

    objects = JsonManager()

    def save(self, *args, **kwargs):
        if self.tax_lot_id and isinstance(self.tax_lot_id, types.StringTypes):
            self.tax_lot_id = self.tax_lot_id[:128]
        if self.pm_property_id and isinstance(
                self.pm_property_id, types.StringTypes):
            self.pm_property_id = self.pm_property_id[:128]
        if self.custom_id_1 and isinstance(
                self.custom_id_1, types.StringTypes):
            self.custom_id_1 = self.custom_id_1[:128]
        if self.lot_number and isinstance(self.lot_number, types.StringTypes):
            self.lot_number = self.lot_number[:128]
        if self.block_number and isinstance(
                self.block_number, types.StringTypes):
            self.block_number = self.block_number[:128]
        if self.district and isinstance(self.district, types.StringTypes):
            self.district = self.district[:128]
        if self.owner and isinstance(self.owner, types.StringTypes):
            self.owner = self.owner[:128]
        if self.owner_email and isinstance(
                self.owner_email, types.StringTypes):
            self.owner_email = self.owner_email[:128]
        if self.owner_telephone and isinstance(
                self.owner_telephone, types.StringTypes):
            self.owner_telephone = self.owner_telephone[:128]
        if self.owner_address and isinstance(
                self.owner_address, types.StringTypes):
            self.owner_address = self.owner_address[:128]
        if self.owner_city_state and isinstance(
                self.owner_city_state, types.StringTypes):
            self.owner_city_state = self.owner_city_state[:128]
        if self.owner_postal_code and isinstance(
                self.owner_postal_code, types.StringTypes):
            self.owner_postal_code = self.owner_postal_code[:128]

        if self.property_name and isinstance(
                self.property_name, types.StringTypes):
            self.property_name = self.property_name[:255]
        if self.address_line_1 and isinstance(
                self.address_line_1, types.StringTypes):
            self.address_line_1 = self.address_line_1[:255]
        if self.address_line_2 and isinstance(
                self.address_line_2, types.StringTypes):
            self.address_line_2 = self.address_line_2[:255]
        if self.city and isinstance(self.city, types.StringTypes):
            self.city = self.city[:255]
        if self.postal_code and isinstance(
                self.postal_code, types.StringTypes):
            self.postal_code = self.postal_code[:255]
        if self.state_province and isinstance(
                self.state_province, types.StringTypes):
            self.state_province = self.state_province[:255]
        if self.building_certification and isinstance(
                self.building_certification, types.StringTypes):  # NOQA
            self.building_certification = self.building_certification[:255]

        super(BuildingSnapshot, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super(BuildingSnapshot, self).clean(*args, **kwargs)

        # if self.owner:
        #     self.owner = self.owner[:128]

        date_field_names = (
            'year_ending',
            'generation_date',
            'release_date',
            'recent_sale_date'
        )
        custom_id_1 = getattr(self, 'custom_id_1')
        if isinstance(custom_id_1, unicode):
            custom_id_1 = unicodedata.normalize('NFKD', custom_id_1).encode(
                'ascii', 'ignore'
            )
        if custom_id_1 and len(str(custom_id_1)) > 128:
            self.custom_id_1 = custom_id_1[:128]
        for field in date_field_names:
            value = getattr(self, field)
            if value and isinstance(value, basestring):
                setattr(self, field, convert_datestr(value))

    def to_dict(self, fields=None, include_related_data=True):
        """
        Returns a dict version of this building, either with all fields
        or masked to just those requested.
        """
        if fields:
            model_fields, ed_fields = split_model_fields(self, fields)
            extra_data = self.extra_data
            ed_fields = filter(lambda f: f in extra_data, ed_fields)

            result = {
                field: getattr(self, field) for field in model_fields
            }
            result['extra_data'] = {
                field: extra_data[field] for field in ed_fields
            }

            # always return id's and canonical_building id's
            result['id'] = result['pk'] = self.pk
            result['canonical_building'] = (
                self.canonical_building and self.canonical_building.pk
            )

            # should probably also return children, parents, and coparent
            result['children'] = map(lambda c: c.id, self.children.all())
            result['parents'] = map(lambda p: p.id, self.parents.all())
            result['co_parent'] = (self.co_parent and self.co_parent.pk)
            result['coparent'] = (self.co_parent and {
                field: self.co_parent.pk for field in ['pk', 'id']
            })

            return result

        d = obj_to_dict(self, include_m2m=include_related_data)

        if include_related_data:
            d['parents'] = list(self.parents.values_list('id', flat=True))
            d['co_parent'] = self.co_parent.pk if self.co_parent else None

        return d

    def __unicode__(self):
        u_repr = u'id: {0}, pm_property_id: {1}, tax_lot_id: {2},' + \
                 ' confidence: {3}'
        return u_repr.format(
            self.pk, self.pm_property_id, self.tax_lot_id, self.confidence
        )

    @property
    def has_children(self):
        return self.children.all().exists()

    @property
    def co_parent(self):
        """returns the first co-parent as a BuildingSnapshot inst"""
        if not self.has_children:
            return
        first_child = self.children.all()[0]
        for parent in first_child.parents.all():
            if parent.pk != self.pk:
                return parent

    @property
    def co_parents(self):
        """returns co-parents for a BuildingSnapshot as a queryset"""
        return BuildingSnapshot.objects.filter(
            children__parents=self
        ).exclude(pk=self.pk)

    def recurse_tree(self, attr):
        """Recurse M2M relationship tree, extending list as we go.

        :param attr: str, name of attribute we wish to traverse.
            .e.g. 'children', or 'parents'

        """
        nodes = []
        node_type = getattr(self, attr)
        # N.B. We're expecting a Django M2M attribute here.
        for node in node_type.all():
            nodes.extend(node.recurse_tree(attr))

        nodes.extend(node_type.all())

        return nodes

    @property
    def child_tree(self):
        """Recurse to give us a merge-order list of children."""
        # Because we traverse down, we need to revese to get merge-order
        children = self.recurse_tree('children')
        children.reverse()
        return children

    @property
    def parent_tree(self):
        """Recurse to give us merge-order list of parents."""
        # No need to reverse, we create merge-order by going backwards
        return self.recurse_tree('parents')

    @property
    def tip(self):
        """returns the tip (leaf) of the BuildingSnapshot tree"""
        children = self.child_tree
        if children:
            # we could also sort by id here to ensure the most recent child
            return children[-1]
        else:
            return self
