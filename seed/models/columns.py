# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import csv
import logging
import os.path
from collections import OrderedDict

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.mappings.mapping_data import MappingData
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.models import (
    Enum,
    Unit,
    SEED_DATA_SOURCES,
)
from seed.utils.constants import VIEW_COLUMNS_PROPERTY

INVENTORY_MAP = {
    'property': 'PropertyState',
    'propertystate': 'PropertyState',
    'taxlot': 'TaxLotState',
    'taxlotstate': 'TaxLotState',
}
# This is the inverse mapping of the property and tax lots that are prepended to the fields
# for the other table.
INVENTORY_MAP_PREPEND = {
    'property': 'tax',
    'propertystate': 'tax',
    'taxlot': 'property',
    'taxlotstate': 'property',
}
_log = logging.getLogger(__name__)


def get_column_mapping(raw_column, organization, attr_name='column_mapped'):
    """Find the ColumnMapping objects that exist in the database from a raw_column

    :param raw_column: str, the column name of the raw data.
    :param organization: Organization inst.
    :param attr_name: str, name of attribute on ColumnMapping to pull out.
        whether we're looking at a mapping from the perspective of
        a raw_column (like we do when creating a mapping), or mapped_column,
        (like when we're applying that mapping).
    :returns: list of mapped items, float representation of confidence.

    """
    from seed.utils.mapping import get_table_and_column_names

    if not isinstance(raw_column, list):
        column_raw = [raw_column]
    else:
        # NL 12/6/2016 - We should never get here, if we see this then find out why and remove the
        # list. Eventually delete this code.
        raise Exception("I am a LIST! Which makes no sense!")

    # Should only return one column
    cols = Column.objects.filter(
        organization=organization, column_name__in=column_raw
    )

    try:
        previous_mapping = ColumnMapping.objects.get(
            super_organization=organization,
            column_raw__in=cols,
        )
    except ColumnMapping.MultipleObjectsReturned:
        _log.debug("ColumnMapping.MultipleObjectsReturned in get_column_mapping")
        # handle the special edge-case where remove dupes does not get
        # called by ``get_or_create``
        ColumnMapping.objects.filter(super_organization=organization, column_raw__in=cols).delete()

        # Need to delete and then just allow for the system to re-attempt the match because
        # the old matches are no longer valid.
        return None
    except ColumnMapping.DoesNotExist:
        _log.debug("ColumnMapping.DoesNotExist")
        return None

    column_names = get_table_and_column_names(previous_mapping, attr_name=attr_name)

    # Check if the mapping is a one-to-one mapping, that is, there is only one mapping available.
    # As far as I know, this should always be the case because of the MultipleObjectsReturned
    # from above.
    if previous_mapping.is_direct():
        column_names = column_names[0]
    else:
        # NL 12/2/2016 - Adding this here for now as a catch. If we get here, then we have problems.
        raise Exception("The mapping returned with not direct!")

    return column_names[0], column_names[1], 100


class Column(models.Model):
    """The name of a column for a given organization."""

    # We have two concepts of the SOURCE. The table_name, which is mostly used, and the
    # SOURCE_* fields. Need to converge on one or the other.
    # SOURCE_PROPERTY = 'P'
    # SOURCE_TAXLOT = 'T'
    # SOURCE_CHOICES = (
    #     (SOURCE_PROPERTY, 'Property'),
    #     (SOURCE_TAXLOT, 'Taxlot'),
    # )
    # SOURCE_CHOICES_MAP = {
    #     SOURCE_PROPERTY: 'property',
    #     SOURCE_TAXLOT: 'taxlot',
    # }

    organization = models.ForeignKey(SuperOrganization, blank=True, null=True)
    column_name = models.CharField(max_length=512, db_index=True)

    # name of the table which the column name applies, if the column name
    # is a db field. Options now are only PropertyState and TaxLotState
    table_name = models.CharField(max_length=512, blank=True, db_index=True, )
    unit = models.ForeignKey(Unit, blank=True, null=True)
    enum = models.ForeignKey(Enum, blank=True, null=True)
    is_extra_data = models.BooleanField(default=False)
    import_file = models.ForeignKey('data_importer.ImportFile', blank=True, null=True)
    units_pint = models.CharField(max_length=64, blank=True, null=True)

    # Do not enable this until running through the database and merging the columns down.
    # BUT first, make sure to add an import file ID into the column class.
    # class Meta:
    #     unique_together = (
    #         'organization', 'column_name', 'is_extra_data', 'table_name', 'import_file')

    def __unicode__(self):
        return u'{} - {}'.format(self.pk, self.column_name)

    @staticmethod
    def create_mappings_from_file(filename, organization, user, import_file_id=None):
        """
        Load the mappings in from a file in a very specific file format. The columns in the file
        must be:

            1. raw field
            2. table name
            3. field name
            4. field display name
            5. field data type
            6. field unit type

        :param filename: string, absolute path and name of file to load
        :param organization: id, organization id
        :param user: id, user id
        :param import_file_id: Integer, If passed, will cache the column mappings data into
                               the import_file_id object.

        :return: ColumnMapping, True
        """

        mappings = []
        if os.path.isfile(filename):
            with open(filename, 'rU') as csvfile:
                for row in csv.reader(csvfile):
                    data = {
                        "from_field": row[0],
                        "to_table_name": row[1],
                        "to_field": row[2],
                        # "to_display_name": row[3],
                        # "to_data_type": row[4],
                        # "to_unit_type": row[5],
                    }
                    mappings.append(data)
        else:
            raise Exception("Mapping file does not exist: {}".format(filename))

        if len(mappings) == 0:
            raise Exception("No mappings in file: {}".format(filename))
        else:
            return Column.create_mappings(mappings, organization, user, import_file_id)

    @staticmethod
    def create_mappings(mappings, organization, user, import_file_id=None):
        """
        Create the mappings for an organization and a user based on a simple
        array of array object.

        :param mappings: dict, dictionary containing mapping information
        :param organization: inst, organization object
        :param user: inst, User object
        :param import_file_id: integer, If passed, will cache the column mappings data into the
                               import_file_id object.

        :return Boolean, True is data are saved in the ColumnMapping table in the database

        .. note:

            Note that as of 09/15/2016 - extra data still needs to be defined in the mappings, it
            will no longer magically appear in the extra_data field if the user did not specify how
            to map it.

        .. example:

                mappings: [
                    {
                        'from_field': 'eui',
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'property',
                    },
                    {
                        'from_field': 'eui',
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'property',
                    }
                ]
        """

        # initialize a cache to store the mappings
        cache_column_mapping = []

        # Take the existing object and return the same object with the db column objects added to
        # the dictionary (to_column_object and from_column_object)
        mappings = Column._column_fields_to_columns(mappings, organization)
        for mapping in mappings:
            if isinstance(mapping, dict):
                try:
                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    )
                except ColumnMapping.MultipleObjectsReturned:
                    _log.debug('ColumnMapping.MultipleObjectsReturned in create_mappings')
                    # handle the special edge-case where remove dupes does not get
                    # called by ``get_or_create``
                    ColumnMapping.objects.filter(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    ).delete()

                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    )

                # Clear out the column_raw and column mapped relationships. -- NL really? history?
                column_mapping.column_raw.clear()
                column_mapping.column_mapped.clear()

                # Add all that we got back from the interface back in the M2M rel.
                [column_mapping.column_raw.add(raw_col) for raw_col in
                 mapping['from_column_object']]
                if mapping['to_column_object'] is not None:
                    [column_mapping.column_mapped.add(dest_col) for dest_col in
                     mapping['to_column_object']]

                column_mapping.user = user
                column_mapping.save()

                cache_column_mapping.append(
                    {
                        'from_field': mapping['from_field'],
                        'from_units': mapping.get('from_units'),
                        'to_field': mapping['to_field'],
                        'to_table_name': mapping['to_table_name'],
                    }
                )
            else:
                raise TypeError("Mapping object needs to be of type dict")

        # save off the cached mappings into the file id that was passed
        if import_file_id:
            from seed.models import ImportFile
            import_file = ImportFile.objects.get(id=import_file_id)
            import_file.save_cached_mapped_columns(cache_column_mapping)
            import_file.save()

        return True

    @staticmethod
    def _column_fields_to_columns(fields, organization):
        """
        List of dictionaries to process into column objects. This method will create the columns
        if they did not previously exist. Note that fields are probably mutable, but the method
        returns a new list of fields.

        .. example:

            test_map = [
                    {
                        'from_field': 'eui',
                        'from_units': 'kBtu/ft**2/year', # optional
                        'to_field': 'site_eui',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'address',
                        'to_field': 'address',
                        'to_table_name': 'TaxLotState'
                    },
                    {
                        'from_field': 'Wookiee',
                        'to_field': 'Dothraki',
                        'to_table_name': 'PropertyState',
                    },
                ]

        Args:
            fields: list of dicts containing to and from fields
            organization: organization model instance

        Returns:
            dict with lists of columns to which is mappable.
        """

        def select_col_obj(column_name, table_name, organization_column):
            if organization_column:
                return [organization_column]
            else:
                # Try for "global" column definitions, e.g. BEDES. - Note the BEDES are not
                # loaded into the database as of 9/8/2016 so not sure if this code is ever
                # exercised
                obj = Column.objects.filter(organization=None, column_name=column_name).first()

                if obj:
                    # create organization mapped column
                    obj.pk = None
                    obj.id = None
                    obj.organization = organization
                    obj.save()

                    return [obj]
                else:
                    if table_name:
                        obj, _ = Column.objects.get_or_create(
                            organization=organization,
                            column_name=column_name,
                            table_name=table_name,
                            is_extra_data=is_extra_data,
                        )
                        return [obj]
                    else:
                        obj, _ = Column.objects.get_or_create(
                            organization=organization,
                            column_name=column_name,
                            is_extra_data=is_extra_data,
                        )
                        return [obj]

        md = MappingData()

        # Container to store the dicts with the Column object
        new_data = []

        for field in fields:
            new_field = field

            # find the mapping data column (i.e. the database fields) that match, if it exists
            # then set the extra data flag to true
            db_field = md.find_column(field['to_table_name'], field['to_field'])
            is_extra_data = False if db_field else True  # yes i am a db column, thus I am not extra_data

            try:
                to_org_col, _ = Column.objects.get_or_create(
                    organization=organization,
                    column_name=field['to_field'],
                    table_name=field['to_table_name'],
                    is_extra_data=is_extra_data
                )
            except Column.MultipleObjectsReturned:
                _log.debug("More than one to_column found for {}.{}".format(field['to_table_name'],
                                                                            field['to_field']))
                # raise Exception("Cannot handle more than one to_column returned for {}.{}".format(
                #     field['to_field'], field['to_table_name']))

                # TODO: write something to remove the duplicate columns
                to_org_col = Column.objects.filter(organization=organization,
                                                   column_name=field['to_field'],
                                                   table_name=field['to_table_name'],
                                                   is_extra_data=is_extra_data).first()
                _log.debug("Grabbing the first to_column")

            try:
                # the from column is the field in the import file, thus the table_name needs to be
                # blank. Eventually need to handle passing in import_file_id
                from_org_col, _ = Column.objects.get_or_create(
                    organization=organization,
                    table_name__in=[None, ''],
                    column_name=field['from_field'],
                    units_pint=field.get('from_units'),  # might be None
                    is_extra_data=False  # data from header rows in the files are NEVER extra data
                )
            except Column.MultipleObjectsReturned:
                _log.debug(
                    "More than one from_column found for {}.{}".format(field['to_table_name'],
                                                                       field['to_field']))

                # TODO: write something to remove the duplicate columns
                from_org_col = Column.objects.filter(organization=organization,
                                                     table_name__in=[None, ''],
                                                     column_name=field['from_field'],
                                                     units_pint=field.get('from_units'),  # might be None
                                                     is_extra_data=is_extra_data).first()
                _log.debug("Grabbing the first from_column")

            new_field['to_column_object'] = select_col_obj(field['to_field'],
                                                           field['to_table_name'], to_org_col)
            new_field['from_column_object'] = select_col_obj(field['from_field'], "", from_org_col)
            new_data.append(new_field)

        return new_data

    @staticmethod
    def save_column_names(model_obj):
        """Save unique column names for extra_data in this organization.

        This is a record of all the extra_data keys we have ever seen
        for a particular organization.

        :param model_obj: model_obj instance (either PropertyState or TaxLotState).
        """

        md = MappingData()

        for key in model_obj.extra_data:
            # Ascertain if our key is ``extra_data`` or not.

            # This is doing way to much work to find if the fields are extra data, especially
            # since that has been asked probably many times before.
            db_field = md.find_column(model_obj.__class__.__name__, key)
            is_extra_data = False if db_field else True  # yes i am a db column, thus I am not extra_data

            # handle the special edge-case where an old organization may have duplicate columns
            # in the database. We should make this a migration in the future and put a validation
            # in the db.
            for i in range(0, 5):
                while True:
                    try:
                        Column.objects.get_or_create(
                            column_name=key[:511],
                            is_extra_data=is_extra_data,
                            organization=model_obj.organization,
                            table_name=model_obj.__class__.__name__
                        )
                    except Column.MultipleObjectsReturned:
                        _log.debug(
                            "Column.MultipleObjectsReturned for {} in save_column_names".format(
                                key[:511]))

                        columns = Column.objects.filter(column_name=key[:511],
                                                        is_extra_data=is_extra_data,
                                                        organization=model_obj.organization,
                                                        table_name=model_obj.__class__.__name__)
                        for c in columns:
                            if not ColumnMapping.objects.filter(
                                    Q(column_raw=c) | Q(column_mapped=c)).exists():
                                _log.debug("Deleting column object {}".format(c.column_name))
                                c.delete()

                        # Check if there are more than one column still
                        if Column.objects.filter(
                                column_name=key[:511],
                                is_extra_data=is_extra_data,
                                organization=model_obj.organization,
                                table_name=model_obj.__class__.__name__).count() > 1:
                            raise Exception(
                                "Could not fix duplicate columns for {}. Contact dev team").format(
                                key)

                        continue

                    break

    def to_dict(self):
        """
        Convert the column object to a dictionary

        :return: dict
        """

        c = {
            'pk': self.id,
            'id': self.id,
            'organization_id': self.organization.id,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'is_extra_data': self.is_extra_data
        }
        if self.unit:
            c['unit_name'] = self.unit.unit_name
            c['unit_type'] = self.unit.unit_type
        else:
            c['unit_name'] = None
            c['unit_type'] = None

        return c

    @staticmethod
    def delete_all(organization):
        """
        Delete all the columns for an organization. Note that this will invalidate all the
        data that is in the extra_data fields of the inventory and is irreversible.

        :param organization: instance, Organization
        :return: [int, int] Number of columns, column_mappings records that were deleted
        """
        cm_delete_count, _ = ColumnMapping.objects.filter(super_organization=organization).delete()
        c_count, _ = Column.objects.filter(organization=organization).delete()
        return [c_count, cm_delete_count]

    @staticmethod
    def _retrieve_db_columns():
        """
        # Retrieve all the columns from the database, independent of the destination of the data,
        # that is, there may be duplicate names, but the table_name.column_name will be unique.

        :return: dict
        """

        # Grab the default columns and their details
        columns = copy.deepcopy(VIEW_COLUMNS_PROPERTY)

        # TODO: check to make sure that all the fields in the DB are in this list!

        return columns

    @staticmethod
    def retrieve_db_types():
        """
        return the data types for the database columns in the format of:

        Example:
        {
          "field_name": "data_type",
          "field_name_2": "data_type_2",
          "address_line_1": "string",
        }

        :return: dict
        """
        columns = Column._retrieve_db_columns()

        MAP_TYPES = {
            'number': 'float',
            'float': 'float',
            'integer': 'integer',
            'string': 'string',
            'datetime': 'datetime',
            'date': 'date',
            'boolean': 'boolean',
        }

        types = OrderedDict()
        for c in columns:
            try:
                types[c['name']] = MAP_TYPES[c['dataType']]
            except KeyError:
                types[c['name']] = ''

        return {"types": types}

    @staticmethod
    def retrieve_db_fields():
        """
        return the fields in the database regardless of properties or taxlots

        [ "address_line_1", "gross_floor_area", ... ]
        :return: list
        """

        columns = Column._retrieve_db_columns()

        fields = set()
        for c in columns:
            if 'dbField' in c.keys() and c['dbField']:
                fields.add(c['name'])

        return list(fields)

    @staticmethod
    def retrieve_all(org_id, inventory_type):
        """
        # Retrieve all the columns for an organization. First, grab the columns from the
        # VIEW_COLUMNS_PROPERTY schema which defines the database columns with added data for
        # various reasons. Then query the database for all extra data columns and add in the
        # data as appropriate ensuring that duplicates that are taken care of (albeit crudely).

        # Note: this method should retrieve the columns from MappingData and then have a method
        # to return for JavaScript (i.e. UI-Grid) or native (standard JSON)

        :param org_id: Organization ID
        :param inventory_type: Inventory Type (property|taxlot)

        :return: dict
        """

        # Grab the default columns and their details
        columns = Column._retrieve_db_columns()

        # Clean up the columns
        for c in columns:
            if c['table'] == INVENTORY_MAP[inventory_type.lower()]:
                c['related'] = False
                if c.get('pinIfNative', False):
                    c['pinnedLeft'] = True
            else:
                c['related'] = True
                # For now, a related field has a prepended value to make the columns unique.
                if c.get('duplicateNameInOtherTable', False):
                    c['name'] = "{}_{}".format(INVENTORY_MAP_PREPEND[inventory_type.lower()],
                                               c['name'])

            # Remove some keys that are not needed for the API
            try:
                c.pop('pinIfNative')
            except KeyError:
                pass

            try:
                c.pop('duplicateNameInOtherTable')
            except KeyError:
                pass

            try:
                c.pop('dbField')
            except KeyError:
                pass

        # Add in all the extra columns
        # don't return columns that have no table_name as these are the columns of the import files
        extra_data_columns = Column.objects.filter(
            organization_id=org_id, is_extra_data=True
        ).exclude(table_name='').exclude(table_name=None)

        for edc in extra_data_columns:
            name = edc.column_name
            table = edc.table_name

            # MAKE NOTE ABOUT HOW IMPORTANT THIS IN
            if name == 'id':
                name += '_extra'

            # check if the column name is already defined in the list. For example, gross_floor_area
            # is a core field, but can be an extra field in taxlot, meaning that the other one
            # needs to be tagged something else.
            # for col in columns:

            # add _extra if the column is already in the list and it is not the one of
            while any(col['name'] == name and col['table'] != table for col in columns):
                name += '_extra'

            # TODO: need to check if the column name is already in the list and if it is then
            # overwrite the data

            display_name = edc.column_name.title().replace('_', ' ')
            columns.append(
                {
                    'name': name,
                    'table': edc.table_name,
                    'displayName': display_name,
                    # 'dataType': 'string',  # TODO: how to check dataTypes on extra_data!
                    'related': edc.table_name != INVENTORY_MAP[inventory_type.lower()],
                    'extraData': True
                }
            )

        # validate that the column names are unique
        uniq = set()
        for c in columns:
            if c['name'] in uniq:
                raise Exception("Duplicate name '{}' found in columns".format(c['name']))
            else:
                uniq.add(c['name'])

        return columns


class ColumnMapping(models.Model):
    """Stores previous user-defined column mapping.

    We'll pull from this when pulling from varied, dynamic
    source data to present the user with previous choices for that
    same field in subsequent data loads.

    """
    user = models.ForeignKey(User, blank=True, null=True)
    source_type = models.IntegerField(choices=SEED_DATA_SOURCES, null=True, blank=True)
    super_organization = models.ForeignKey(SuperOrganization, verbose_name=_('SeedOrg'),
                                           blank=True, null=True, related_name='column_mappings')
    column_raw = models.ManyToManyField('Column', related_name='raw_mappings', blank=True, )
    column_mapped = models.ManyToManyField('Column', related_name='mapped_mappings', blank=True, )

    def is_direct(self):
        """
        Returns True if the ColumnMapping is a direct mapping from imported
        column name to either a BEDES column or a previously imported column.
        Returns False if the ColumnMapping represents a concatenation.
        """
        return (
            (self.column_raw.count() == 1) and
            (self.column_mapped.count() == 1)
        )

    def is_concatenated(self):
        """
        Returns True if the ColumnMapping represents the concatenation of
        imported column names; else returns False.
        """
        return not self.is_direct()

    def remove_duplicates(self, qs, m2m_type='column_raw'):
        """
        Remove any other Column Mappings that use these columns.

        :param qs: queryset of ``Column``. These are the Columns in a M2M with
            this instance.
        :param m2m_type: str, the name of the field we're comparing against.
            Defaults to 'column_raw'.

        """
        ColumnMapping.objects.filter(
            **{
                '{0}__in'.format(m2m_type): qs,
                'super_organization': self.super_organization
            }
        ).exclude(pk=self.pk).delete()

    def to_dict(self):
        """
        Convert the ColumnMapping object to a dictionary

        :return: dict
        """

        c = {
            'pk': self.id,
            'id': self.id
        }
        if self.user:
            c['user_id'] = self.user.id
        else:
            c['user_id'] = None
        c['source_type'] = self.source_type
        c['organization_id'] = self.super_organization.id
        if self.column_raw and self.column_raw.first():
            c['from_column'] = self.column_raw.first().to_dict()
        else:
            c['from_column'] = None

        if self.column_mapped and self.column_mapped.first():
            c['to_column'] = self.column_mapped.first().to_dict()
        else:
            c['to_column'] = None

        return c

    def save(self, *args, **kwargs):
        """
        Overrides default model save to eliminate duplicate mappings.

        .. warning ::
            Other column mappings which have the same raw_columns in them
            will be removed!

        """
        super(ColumnMapping, self).save(*args, **kwargs)
        # Because we need to have saved our ColumnMapping in order to have M2M,
        # We must create it before we prune older references.
        self.remove_duplicates(self.column_raw.all())

    def __unicode__(self):
        return u'{0}: {1} - {2}'.format(
            self.pk, self.column_raw.all(), self.column_mapped.all()
        )

    @staticmethod
    def get_column_mappings(organization):
        """
        Returns dict of all the column mappings for an Organization's given
        source type

        :param organization: instance, Organization.
        :returns: dict, list of dict.

        Use this when actually performing mapping between data sources, but only
        call it after all of the mappings have been saved to the ``ColumnMapping``
        table.
        """
        column_mappings = ColumnMapping.objects.filter(
            super_organization=organization
        )
        mapping = {}
        for cm in column_mappings:
            # What in the world is this doings? -- explanation please
            if not cm.column_mapped.all().exists():
                continue

            key = cm.column_raw.all().values_list('table_name', 'column_name')
            value = cm.column_mapped.all().values_list('table_name', 'column_name')

            if len(key) != 1:
                raise Exception("There is either none or more than one mapping raw column")

            if len(value) != 1:
                raise Exception("There is either none or more than one mapping dest column")

            key = key[0]
            value = value[0]

            # These should be lists of one element each.
            mapping[key[1]] = value

        _log.debug("Mappings from get_column_mappings is: {}".format(mapping))
        return mapping, []

    @staticmethod
    def get_column_mappings_by_table_name(organization):
        """
        Breaks up the get_column_mappings into another layer to provide access by the table
        name as a key.

        :param organization: instance, Organization
        :return: dict
        """

        data, _ = ColumnMapping.get_column_mappings(organization)
        # data will be in format
        # {
        #     u'Wookiee': (u'PropertyState', u'Dothraki'),
        #     u'Ewok': (u'TaxLotState', u'Hattin'),
        #     u'eui': (u'PropertyState', u'site_eui'),
        #     u'address': (u'TaxLotState', u'address')
        # }

        tables = set()
        for k, v in data.iteritems():
            tables.add(v[0])

        # initialize the new container to store the results
        # (there has to be a better way of doing this... not enough time)
        container = {}
        for t in tables:
            container[t] = {}

        for k, v in data.iteritems():
            container[v[0]][k] = v

        # Container will be in the format:
        #
        # container = {
        #     u'PropertyState': {
        #         u'Wookiee': (u'PropertyState', u'Dothraki'),
        #         u'eui': (u'PropertyState', u'site_eui'),
        #     },
        #     u'TaxLotState': {
        #         u'address': (u'TaxLotState', u'address'),
        #         u'Ewok': (u'TaxLotState', u'Hattin'),
        #     }
        # }
        return container

    @staticmethod
    def delete_mappings(organization):
        """
        Delete all the mappings for an organization. Note that this will erase all the mappings
        so if a user views an existing Data Mapping the mappings will not show up as the actual
        mapping, rather, it will show up as new suggested mappings

        :param organization: instance, Organization
        :return: int, Number of records that were deleted
        """
        count, _ = ColumnMapping.objects.filter(super_organization=organization).delete()
        return count
