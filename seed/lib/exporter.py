# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import os
import tempfile

import unicodecsv as csv
import xlwt
from django.conf import settings
from django.db.models.fields import FieldDoesNotExist
from django.core.files.storage import DefaultStorage
from django.db.models import Manager
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ReverseManyToOneDescriptor,
)


def batch_qs(qs, batch_size=1000):
    """
    From: https://djangosnippets.org/snippets/1170/

    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset.

    Usage:

    .. code-block::python

        # Make sure to order your querset
        article_qs = Article.objects.order_by('id')
        for start, end, total, qs in batch_qs(article_qs):
            print 'Now processing %s - %s of %s' % (start + 1, end, total)
            for article in qs:
                print article.body
    """
    if not qs.ordered:
        qs = qs.order_by('pk')
    total = qs.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])


def get_field_name_from_model(field, model):
    """
    Takes a field name like "building_snapshot__state" and returns the verbose
    field name as set in django, to be used as the header in exported files.

    :param field:
    :param qs:
    :return:
    """
    par = model
    components = field.split("__")
    for component in components[:-1]:  # iterate through the parent models
        par = getattr(par, component)

        # If the component resolves to a Manager or Descriptor,
        # we have to get to the model differently than a standard field
        if isinstance(par, (Manager,
                            ReverseManyToOneDescriptor)):
            par = par.related.model

        # Special case for status_label in project exports, where we want
        # the name from the relation field -- not the field the value comes
        # from.
        elif component == 'status_label':
            components[-1] = component
            par = par.field.model

        # Reverse descriptors also have some special ways to get to the model
        elif isinstance(par, ForwardManyToOneDescriptor):
            par = par.field.target_field.model

    # Use unicode to force this to something the XLS writer can handle properly
    try:
        name = unicode(par._meta.get_field(components[-1]).verbose_name)
    except FieldDoesNotExist:
        name = unicode(components[-1])

    return name


def get_field_value_from_instance(field, obj):
    """
    Does some deep diving to find the right value given a string like
    "building_snapshot__state"
    """
    par = obj
    components = field.split("__")
    for component in components[:-1]:
        par = getattr(par, component)
        if par is None:
            break

    try:
        return getattr(par, components[-1]) if par else None
    except AttributeError:
        # try extra_data JSONField
        return par.extra_data.get(components[-1])


def construct_obj_row(obj, fields):
    """
    Creates an exportable row of data from an object and a list of fields.
    Ignores nones and instances of the Django Manager object, replacing them
    with blank unicode strings.
    """
    row = []
    for field in fields:
        value = get_field_value_from_instance(field, obj)
        if isinstance(value, Manager) or value is None:
            row.append(u'')
        else:
            row.append(unicode(value))
    return row


def qs_to_rows(qs, fields):
    for start, end, total, sub_qs in batch_qs(qs):
        for obj in sub_qs:
            yield construct_obj_row(obj, fields)


class Exporter:
    """
    Class to handle the exporting of buildings
    """
    tempfile = None  # where the temp file is saved after export

    def __init__(self, export_id, export_name, export_type):
        """
        Initialize the exporter object by a few variables

        :param export_id: unique id of the export (used for the directory)
        :param export_name: Name of the file to export (without the extension)
        :param export_type: csv or xls
        :return: Exporter instance
        """

        # initialize a bunch of member variables
        self.export_id = export_id
        self.export_name = export_name
        self.export_type = export_type

    def valid_export_type(self):
        return self.export_type.lower() in {'csv', 'xls'}

    def export(self, buildings, fields, row_cb):
        """
        The main method of export. Uses the export type defined by the initializer

        :param buildings: Array of building ids to export
        :param fields: Array of fields to export
        :param row_cb: ID for row cache
        :return:
        """

        export_method = getattr(self, "export_%s" % self.export_type, None)
        if export_method:
            export_method(buildings, fields, row_cb)
        else:
            return None

        # save the tempfile to the file storage location (s3 or local)
        if self.tempfile is not None:
            with open(self.tempfile) as f:
                if 'S3' in settings.DEFAULT_FILE_STORAGE:
                    s3_key = DefaultStorage().bucket.new_key(self.filename())
                    s3_key.set_contents_from_file(f)
                else:
                    # This is non-ideal. We should just save the file in the right location to start with
                    # or return the file from the "export". This was done to avoid changing the exporter code 'too much'.
                    file_storage = DefaultStorage()
                    file_storage.save(self.filename(), f)

                os.remove(self.tempfile)

        return self.filename

    @staticmethod
    def subdirectory_from_export_id(export_id):
        """
        Return the subdirectory as constructed by the instance method.

        :param export_id: The export ID
        :return: String of the path to the exported file
        """

        dummy_class = Exporter(export_id, None, None)
        return dummy_class.subdirectory()

    @staticmethod
    def fields_from_queryset(qs):
        """
        Creates a list of all accessible fields on a model based off of a queryset.

        This method should not be here. It seems that is should be on the building snapshot model.
        Not moved yet because I am unsure if the qs argument is more than one data type
        (i.e. BuildingSnapshot and/or ?)
        """
        fields = qs.model._meta.get_fields()
        for field in fields:
            try:
                if field.is_relation:
                    continue
            except FieldDoesNotExist:
                continue
            else:
                yield field.name

    def subdirectory(self):
        """
        Create and return the subdirectory

        :return: String of the subdirectory
        """
        path = os.path.join("exports", self.export_id)

        return path

    def filename(self):
        """
        The expected file name based on the export_id, export_name, and export_type

        :return: String of the expected filename
        """
        return os.path.join(self.subdirectory(), "%s.%s" % (self.export_name, self.export_type))

    # Old methods that should be converted into private methods (will require test changes)

    def export_csv(self, qs, fields=[], cb=None):
        self.tempfile = tempfile.mktemp('.csv')

        with open(self.tempfile, 'w') as export_file:
            writer = csv.writer(export_file)

            if not fields:
                fields = list(Exporter.fields_from_queryset(qs))

            header = tuple(
                get_field_name_from_model(field, qs.model)
                for field in fields
            )
            writer.writerow(header)

            for i, row in enumerate(qs_to_rows(qs, fields)):
                writer.writerow(row)
                if cb:
                    cb(i)

        return self.tempfile

    def export_xls(self, qs, fields=[], cb=None):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Exported SEED Data')

        if not fields:
            fields = list(Exporter.fields_from_queryset(qs))

        for i, field in enumerate(fields):
            header = get_field_name_from_model(field, qs.model)
            worksheet.write(0, i, header)

        for i, row in enumerate(qs_to_rows(qs, fields)):
            for j, v in enumerate(row):
                worksheet.write(i + 1, j, v)
            if cb:
                cb(i)

        self.tempfile = tempfile.mktemp('.xls')
        workbook.save(self.tempfile)

        return self.tempfile
